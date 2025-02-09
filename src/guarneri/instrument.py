"""Loader for creating instances of the devices from a config file."""

import asyncio
import inspect
import logging
import time
import warnings
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any, Callable, TypeAlias, TypeVar, cast

import tomlkit
from ophyd import Device as ThreadedDevice
from ophyd.sim import make_fake_device
from ophyd_async.core import DEFAULT_TIMEOUT
from ophyd_async.core import Device as AsyncDevice
from ophyd_async.core import NotConnected
from ophydregistry import Registry

from .exceptions import InvalidConfiguration

log = logging.getLogger(__name__)


instrument = None


K = TypeVar("K")
Device: TypeAlias = AsyncDevice | ThreadedDevice


class Instrument:
    """A beamline instrument built from config files of Ophyd devices.

    *device_classes* should be dictionary that maps configuration
     section names to device classes (or similar items).

    Example:

    .. code-block:: python

        instrument = Instrument({
          "ion_chamber": IonChamber
          "motors": load_motors,
        })

    The values in *device_classes* should be one of the following:

    *ignored_classes* can be used to avoid sections in the
    configuration file that are needed for other things. If provided,
    sections whose ``"device_class"`` is included in *ignored_classes*
    will be skipped.

    1. A device class
    2. A callable that returns an instantiated device object
    3. A callable that returns a sequence of device objects

    Parameters
    ==========
    device_classes
      Maps config section names to device classes.
    registry
      An ophyd registry to use, if omitted a new registry will be
      created. This registry will be available as
      `Instrument.devices`.
    ignored_classes
      Class names to ignore if they are present in the config file.

    """

    devices: Registry

    def __init__(
        self,
        device_classes: Mapping[str, type[Device]],
        registry: Registry | None = None,
        ignored_classes: Sequence[str] | None = None,
    ):
        self.unconnected_devices: list[Device] = []
        if registry is None:
            registry = Registry(auto_register=False, use_typhos=False)
        self.devices = registry
        self.device_classes = device_classes
        if ignored_classes is None:
            ignored_classes = []
        self.ignored_classes = ignored_classes

    def parse_config(self, config_file: IO, config_format: str) -> list[dict]:
        """Parse an instrument configuration file.

        This method can be overridden to implement custom
        configuration file schema. It should return a sequence of
        device definitions, similar to:

        .. code-block:: python

            [
                {
                   "device_class": "ophyd.motor.EpicsMotor",
                   "kwargs": {
                       "name": "my_device",
                       "prefix": "255idcVME:m1",
                    },
                }
            ]

        *device_class* can be an entry in the
        ``Instrument.device_classes``, or else an import path that
        will be loaded dynamically.

        Parameters
        ==========
        config_file
          A file path to read.
        config_format
          The language in which the config file is written.

        Returns
        =======
        device_defns
          A list of dictionaries, describing the devices to create.

        """
        if config_format == "toml":
            return self.parse_toml_file(config_file)
        if config_format == "yaml":
            return self.parse_yaml_file(config_file)
        else:
            raise ValueError(f"Unknown file extension: {config_file}")

    def parse_yaml_file(self, config_file: IO[str]) -> list[dict]:
        """Produce device definitions from a YAML file.

        See ``parse_config()`` for details.

        """
        raise NotImplementedError

    def parse_toml_file(self, config_file: IO[str]) -> list[dict]:
        """Produce device definitions from a TOML file.

        See ``parse_config()`` for details.

        """
        # Load the file from disk
        cfg = tomlkit.load(config_file)
        # Convert file contents to device definitions
        device_defns = []
        sections = {
            key: val for key, val in cfg.items() if isinstance(val, tomlkit.items.AoT)
        }
        tables = [(cls, table) for cls, aot in sections.items() for table in aot]
        device_defns = [
            {
                "device_class": class_name,
                "args": (),
                "kwargs": table,
            }
            for class_name, table in tables
        ]
        return device_defns

    def make_devices(self, defns: Sequence[Mapping], fake: bool) -> list[Device]:
        """Create Device instances based on device definitions.

        Parameters
        ==========
        defns
          The device defitions need to create devices. Each one should
          at least have the keys "device_class", and "kwargs".

        Returns
        =======
        devices
          The Ophyd and ophyd-async devices created from *defintions*.

        """
        # Validate all the defitions
        for defn in defns:
            try:
                Klass = self.device_classes[defn["device_class"]]
            except KeyError:
                continue
            self.validate_params(defn["kwargs"], Klass)
        # Create devices
        devices: list[Device] = []
        for defn in defns:
            if defn["device_class"] in self.ignored_classes:
                continue
            # Check if we know how to make the device
            try:
                Klass = self.device_classes[defn["device_class"]]
            except KeyError as exc:
                warnings.warn(f"Unknown device class: {exc}")
                continue
            # Create the device
            device = self.make_device(
                Klass,
                args=defn.get("args", ()),
                kwargs=defn.get("kwargs", {}),
                fake=fake,
            )
            try:
                # Maybe its a list of devices?
                devices.extend(device)
            except TypeError:
                # No, assume it's just a single device then
                devices.append(device)
        return devices

    def validate_params(self, params: dict[str, Any], Klass: type[Device]):
        """Check that parameters match a Device class's initializer."""
        sig = inspect.signature(Klass)
        any([param.kind == param.VAR_KEYWORD for param in sig.parameters.values()])
        # Make sure we're not missing any required parameters
        for key, sig_param in sig.parameters.items():
            # Check for missing parameters
            param_missing = key not in params
            VAR_ARGS = [sig_param.VAR_KEYWORD, sig_param.VAR_POSITIONAL]
            param_required = (
                sig_param.default is sig_param.empty and sig_param.kind not in VAR_ARGS
            )
            if param_missing and param_required:
                raise InvalidConfiguration(
                    f"Missing required key '{key}' for {Klass}: {params}"
                )
            # Check types
            if not param_missing:
                try:
                    correct_type = isinstance(params[key], sig_param.annotation)
                    has_type = not issubclass(sig_param.annotation, inspect._empty)
                except TypeError:
                    correct_type = False
                    has_type = False
                if has_type and not correct_type:
                    raise InvalidConfiguration(
                        f"Incorrect type for {Klass} key '{key}': "
                        f"expected `{sig_param.annotation}` but got "
                        f"`{type(params[key])}`."
                    )

    def make_device(
        self,
        Klass: Callable | type,
        args: Sequence[Any],
        kwargs: Mapping[str, Any],
        fake: bool,
    ) -> Any:
        """Create a device from its parameters.

        Parameters
        ==========
        Klass
          The thing to call to create the device.
        args
          Positional arguments for creating the device.
        kwargs
          Keyword arguments for creating the device.
        fake
          If true, a fake device will be created instead of the real
          one. See :py:func:`ophyd.sim.make_fake_device`.

        """
        # Mock threaded ophyd devices if necessary
        if fake:
            try:
                Klass = make_fake_device(Klass)
            except TypeError:
                pass
        # Turn the parameters into pure python objects
        Item = tomlkit.items.Item
        args = [arg.unwrap() if isinstance(arg, Item) else arg for arg in args]
        kwargs = {
            key: arg.unwrap() if isinstance(arg, Item) else arg
            for key, arg in kwargs.items()
        }
        # Check if we need to inject additional arguments
        sig = inspect.signature(Klass)
        if "registry" in sig.parameters.keys():
            kwargs.setdefault("registry", self.devices)
        if "fake" in sig.parameters.keys():
            kwargs.setdefault("fake", fake)
        # Create the device
        result = Klass(**kwargs)
        return result

    async def connect(
        self,
        mock: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
        force_reconnect: bool = False,
        return_exceptions: bool = False,
    ):
        """Connect all Devices.

        Contains a timeout that gets propagated to device.connect methods.

        Parameters
        ----------
        mock:
          If True then use ``MockSignalBackend`` for all Signals
        timeout:
          Time to wait before failing with a TimeoutError.
        force_reconnect
          Force the signals to establish a new connection.
        return_exceptions
          If true, exceptions will be returned for further processing,
          otherwise, exceptions will be raised (default).

        """
        t0 = time.monotonic()
        # Sort out which devices are which
        threaded_devices: list[ThreadedDevice] = []
        async_devices: list[AsyncDevice] = []
        for device in self.unconnected_devices:
            if hasattr(device, "connect"):
                async_devices.append(device)
            else:
                threaded_devices.append(device)
        # Connect to async devices
        aws = (
            dev.connect(mock=mock, timeout=timeout, force_reconnect=force_reconnect)
            for dev in async_devices
        )
        results = await asyncio.gather(*aws, return_exceptions=True)
        # Filter out the disconnected devices
        new_devices = []
        exceptions: dict[str, Exception] = {}
        for device, result in zip(async_devices, results):
            if result is None:
                log.debug(f"Successfully connected device {device.name}")
                new_devices.append(device)
                self.unconnected_devices.remove(device)
            else:
                # Unexpected exception, raise it so it can be handled
                log.debug(f"Failed connection for device {device.name}")
                exceptions[device.name] = cast(Exception, result)
        # Connect to threaded devices
        timeout_reached = False
        while not timeout_reached and len(threaded_devices) > 0:
            # Remove any connected devices for the running list
            connected_devices = [
                dev for dev in threaded_devices if getattr(dev, "connected", True)
            ]
            for device in connected_devices:
                self.unconnected_devices.remove(device)
            new_devices.extend(connected_devices)
            threaded_devices = [
                dev for dev in threaded_devices if dev not in connected_devices
            ]
            # Tick the clock for the next round through the while loop
            await asyncio.sleep(min((0.05, timeout / 10.0)))
            timeout_reached = (time.monotonic() - t0) > timeout
        # Add disconnected devices to the exception list
        for device in threaded_devices:
            try:
                device.wait_for_connection(timeout=0)
            except TimeoutError as exc:
                exceptions[device.name] = NotConnected(str(exc))
        # Re-register devices in case their names or labels changed
        for device in new_devices:
            self.devices.register(device)
        # Raise exceptions if any were present
        if return_exceptions:
            return new_devices, exceptions
        if len(exceptions) > 0:
            raise NotConnected(exceptions)
        return new_devices

    @contextmanager
    def open_config_file(
        self, config_file: Path | str | IO, config_format: str | None
    ) -> Iterator[tuple[IO, str]]:
        bad_fmt_msg = (
            f"Could not determine format of config file {config_file}. "
            "Please provide format as *config_format*."
        )
        try:
            fp = Path(cast(Path | str, config_file))
        except TypeError:
            # Probably an open file so just use as is
            if config_format is None:
                raise RuntimeError(bad_fmt_msg)
            yield (cast(IO, config_file), config_format)
        # Decide what format this file is in
        suffix = fp.suffix
        formats = {
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
        }
        if config_format is None:
            try:
                config_format = formats[suffix]
            except KeyError:
                raise RuntimeError(bad_fmt_msg)
        with open(fp, mode="rt") as fd:
            yield (fd, config_format)

    def load(
        self,
        config_file: Path | str | IO,
        *,
        config_format: str | None = None,
        fake: bool = False,
        device_classes: Mapping | None = None,
        ignored_classes: Sequence[str] | None = None,
        return_exceptions: bool = False,
    ):
        """Load instrument specified in config file.

        Parameters
        ==========
        config_file
          A file path that will be loaded. Can be either a path to a
          file, or the open file object itself.
        config_format
          Which kind of config file is in use. If ``None``, the format
          will be interpreted from the file path.
        fake
          If true, simulated Ophyd devices will be created. Use
          ``connect(mock=True)`` for ophyd-async devices.
        device_classes
          A temporary set of device classes to use for this call
          only. Overrides any device classes given during
          initalization.

        """
        # Load the instrument from config files
        old_classes = self.device_classes
        old_ignored = self.ignored_classes
        # Decide which format to use
        # Parse device configuration files
        with self.open_config_file(config_file, config_format) as (fd, fmt):
            device_defns = self.parse_config(fd, config_format=fmt)
        # Temprary override of device classes
        if device_classes is not None:
            self.device_classes = device_classes
        if ignored_classes is not None:
            self.ignored_classes = ignored_classes
        try:
            # Create device objects
            devices = self.make_devices(device_defns, fake=fake)
        finally:
            self.device_classes = old_classes
            self.ignored_classes = old_ignored
        # Store the connected devices
        self.unconnected_devices.extend(devices)
        for device in devices:
            self.devices.register(device)
