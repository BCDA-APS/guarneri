"""Helper functions for Guarneri."""

from collections.abc import Callable, Sequence
from importlib import import_module
from typing import TypeAlias

from ophyd import Device as ThreadedDevice
from ophyd_async.core import Device as AsyncDevice

Device: TypeAlias = AsyncDevice | ThreadedDevice
Loader: TypeAlias = Callable[..., Device | Sequence[Device]] | type[Device]


def dynamic_import(full_path: str) -> Loader:
    """
    Import the object given its import path as text.

    Motivated by specification of class names for plugins
    when using ``apstools.devices.ad_creator()``.

    EXAMPLES::

        obj = dynamic_import("ophyd.EpicsMotor")
        m1 = obj("gp:m1", name="m1")

        IocStats = dynamic_import("instrument.devices.ioc_stats.IocInfoDevice")
        gp_stats = IocStats("gp:", name="gp_stats")
    """

    if "." not in full_path:
        # fmt: off
        raise ValueError(
            "Must use a dotted path, no local imports."
            f" Received: {full_path!r}"
        )
        # fmt: on

    if full_path.startswith("."):
        # fmt: off
        raise ValueError(
            "Must use absolute path, no relative imports."
            f" Received: {full_path!r}"
        )
        # fmt: on

    module_name, object_name = full_path.rsplit(".", 1)
    module_object = import_module(module_name)
    import_object = getattr(module_object, object_name)

    return import_object
