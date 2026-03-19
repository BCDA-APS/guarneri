from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from ophyd import Component
from ophyd import Device as DeviceV1
from ophyd import EpicsSignal
from ophyd_async.core import Device

from guarneri import Instrument, exceptions

toml_file = Path(__file__).parent.parent.resolve() / "iconfig_example.toml"
yaml_file = Path(__file__).parent.parent.resolve() / "iconfig_example.yaml"


class ThreadedDevice(DeviceV1):
    description = Component(EpicsSignal, ".DESC")


class AsyncDevice(Device):
    def __init__(
        self,
        scaler_prefix: str,
        scaler_channel: int,
        preamp_prefix: str,
        voltmeter_prefix: str,
        voltmeter_channel: int,
        counts_per_volt_second: float,
        name: str = "",
        auto_name: bool | None = None,
        *args,
        **kwargs,
    ):
        kwargs.setdefault("name", name)
        super().__init__(*args, **kwargs)


def load_devices(num_devices=0):
    for i in num_devices:
        yield AsyncDevice()


@pytest.fixture()
def instrument():
    inst = Instrument(
        {
            "async_device": AsyncDevice,
            "factory_device": load_devices,
            "threaded_device": ThreadedDevice,
        }
    )
    # with open(toml_file, mode="tr", encoding="utf-8") as fd:
    #     inst.parse_toml_file(fd)
    return inst


def test_validate_missing_params(instrument):
    defn = {
        # "scaler_prefix": "scaler_1:",
        # "scaler_channel": 3,
        # "preamp_prefix": "preamp_1:",
        # "voltmeter_prefix": "labjack_1:",
        # "voltmeter_channel": 1,
        # "counts_per_volt_second": 1e-6,
        # "name": "",
        # "auto_name": None,
    }
    with pytest.raises(Exception):
        instrument.validate_params(defn, AsyncDevice)


def test_validate_optional_params(instrument):
    defn = {
        "scaler_prefix": "scaler_1:",
        "scaler_channel": 3,
        "preamp_prefix": "preamp_1:",
        "voltmeter_prefix": "labjack_1:",
        "voltmeter_channel": 1,
        "counts_per_volt_second": 1e-6,
        # "name": "",
        # "auto_name": None,
    }
    instrument.validate_params(defn, AsyncDevice)


def test_validate_wrong_types(instrument):
    defn = {
        "scaler_prefix": "scaler_1:",
        "scaler_channel": "3",
        "preamp_prefix": "preamp_1:",
        "voltmeter_prefix": "labjack_1:",
        "voltmeter_channel": "1",
        "counts_per_volt_second": 1e-6,
        "name": "",
        "auto_name": None,
    }
    with pytest.raises(exceptions.InvalidConfiguration):
        instrument.validate_params(defn, AsyncDevice)


@pytest.fixture()
def config_io_toml():
    with open(toml_file, mode="rt") as fd:
        yield fd


@pytest.fixture()
def config_io_yaml():
    with open(yaml_file, mode="rt") as fd:
        yield fd


def test_parse_toml_config(config_io_toml, instrument):
    cfg = instrument.parse_config(config_io_toml, config_format="toml")
    assert len(cfg) > 0
    dfn = cfg[0]
    assert dfn["device_class"] == "async_device"


def test_parse_yaml_config(config_io_yaml, instrument):
    cfg = instrument.parse_config(config_io_yaml, config_format="yaml")
    assert len(cfg) > 0
    dfn = cfg[0]
    assert dfn["device_class"] == "ophyd.Signal"


def test_make_unknown_class(instrument):
    """Check that unresolvable device classes only raise a warning."""
    instrument.device_classes = {}
    defns = [
        {
            "device_class": "module.tardis",
            "kwargs": {
                "name": "the tardis",
            },
        }
    ]
    with pytest.warns() as warned:
        devices = instrument.make_devices(defns=defns, fake=True)
    assert len(warned) == 1
    assert "tardis" in str(warned[0].message)
    assert len(devices) == 0


def test_make_async_devices(instrument, monkeypatch):
    devices = instrument.make_devices(
        [
            {
                "device_class": "async_device",
                "kwargs": {
                    "scaler_prefix": "255idcVME:3820:",
                    "scaler_channel": 2,
                    "preamp_prefix": "255idc:SR03:",
                    "voltmeter_prefix": "255idc:LabJackT7_1:",
                    "voltmeter_channel": 1,
                    "counts_per_volt_second": 10e6,
                    "name": "I0",
                },
            },
        ],
        fake=True,
    )
    assert len(devices) == 1
    assert devices[0].name == "I0"


def test_make_threaded_devices(instrument, monkeypatch):
    monkeypatch.setattr(instrument, "validate_params", MagicMock(return_value=True))
    devices = instrument.make_devices(
        [
            {
                "device_class": "threaded_device",
                "kwargs": {
                    "prefix": "255idcVME:",
                    "name": "I0",
                },
            },
        ],
        fake=True,
    )
    assert len(devices) == 1
    assert devices[0].name == "I0"


async def test_connect(instrument):
    # N.B., this really only tests ohpyd-async devices
    instrument.load(config_file=toml_file, fake=True)
    async_devices = [
        d for d in instrument.unconnected_devices if hasattr(d, "_connect_task")
    ]
    sync_devices = [
        d for d in instrument.unconnected_devices if hasattr(d, "connected")
    ]
    assert len(async_devices) > 0
    assert len(sync_devices) > 0
    # Make mocked connect methods
    for device in async_devices:
        device.connect = AsyncMock(return_value=None)
    # Connect the device
    await instrument.connect(mock=True)
    # Are devices connected afterwards?
    # NB: This doesn't actually test the code for threaded devices
    assert all([d.connect.called for d in async_devices])
    assert len(instrument.unconnected_devices) == 0


def test_load(monkeypatch):
    instrument = Instrument({})
    # Mock out the relevant methods to test
    monkeypatch.setattr(instrument, "parse_toml_file", MagicMock())
    monkeypatch.setattr(instrument, "make_devices", MagicMock(return_value=[]))
    monkeypatch.setenv("HAVEN_CONFIG_FILES", str(toml_file), prepend=False)
    # Execute the loading step
    instrument.load(toml_file, fake=True)
    # Check that the right methods were called
    instrument.parse_toml_file.assert_called_once()
    instrument.make_devices.assert_called_once()


# --- Tests for duplicate YAML key detection (issue #33) ---


class TestDuplicateYamlKeys:
    """Duplicate keys in YAML files must raise DuplicateYamlKey."""

    def test_top_level_duplicate_key(self, instrument, tmp_path):
        """Top-level duplicate keys are detected with file, lines, and key."""
        yaml_content = (
            "ophyd.Signal:\n"
            "- name: sig1\n"
            "  value: 1.0\n"
            "ophyd.Signal:\n"
            "- name: sig2\n"
            "  value: 2.0\n"
        )
        yaml_path = tmp_path / "dup_top.yaml"
        yaml_path.write_text(yaml_content)

        with open(yaml_path, "rt") as fd:
            with pytest.raises(exceptions.DuplicateYamlKey, match="ophyd.Signal"):
                instrument.parse_yaml_file(fd)

    def test_error_message_contains_file_name(self, instrument, tmp_path):
        """The error message must reference the file name."""
        yaml_content = (
            "ophyd.Signal:\n"
            "- name: sig1\n"
            "ophyd.Signal:\n"
            "- name: sig2\n"
        )
        yaml_path = tmp_path / "dup_filename.yaml"
        yaml_path.write_text(yaml_content)

        with open(yaml_path, "rt") as fd:
            with pytest.raises(exceptions.DuplicateYamlKey) as exc_info:
                instrument.parse_yaml_file(fd)
        assert str(yaml_path) in str(exc_info.value)

    def test_error_message_contains_line_numbers(self, instrument, tmp_path):
        """The error message must include both line numbers."""
        yaml_content = (
            "ophyd.Signal:\n"       # line 1
            "- name: sig1\n"        # line 2
            "  value: 1.0\n"        # line 3
            "ophyd.Signal:\n"       # line 4
            "- name: sig2\n"        # line 5
        )
        yaml_path = tmp_path / "dup_lines.yaml"
        yaml_path.write_text(yaml_content)

        with open(yaml_path, "rt") as fd:
            with pytest.raises(exceptions.DuplicateYamlKey) as exc_info:
                instrument.parse_yaml_file(fd)
        msg = str(exc_info.value)
        # First occurrence on line 1, duplicate on line 4
        assert "line 1" in msg
        assert "line 4" in msg

    def test_error_message_contains_duplicate_key_name(self, instrument, tmp_path):
        """The error message must include the actual duplicated key."""
        yaml_content = (
            "ophyd.EpicsMotor:\n"
            "- name: m1\n"
            "ophyd.EpicsMotor:\n"
            "- name: m2\n"
        )
        yaml_path = tmp_path / "dup_key_name.yaml"
        yaml_path.write_text(yaml_content)

        with open(yaml_path, "rt") as fd:
            with pytest.raises(exceptions.DuplicateYamlKey) as exc_info:
                instrument.parse_yaml_file(fd)
        assert "ophyd.EpicsMotor" in str(exc_info.value)

    def test_nested_duplicate_key(self, instrument, tmp_path):
        """Duplicate keys inside a nested mapping are also detected."""
        yaml_content = (
            "ophyd.Signal:\n"
            "- name: sig1\n"
            "  name: sig1_dup\n"
        )
        yaml_path = tmp_path / "dup_nested.yaml"
        yaml_path.write_text(yaml_content)

        with open(yaml_path, "rt") as fd:
            with pytest.raises(exceptions.DuplicateYamlKey, match="name"):
                instrument.parse_yaml_file(fd)

    def test_no_duplicate_keys_succeeds(self, instrument, tmp_path):
        """A valid YAML file without duplicates parses normally."""
        yaml_content = (
            "ophyd.Signal:\n"
            "- name: sig1\n"
            "  value: 1.0\n"
            "ophyd.EpicsMotor:\n"
            "- name: m1\n"
            "  prefix: IOC:m1\n"
        )
        yaml_path = tmp_path / "no_dup.yaml"
        yaml_path.write_text(yaml_content)

        with open(yaml_path, "rt") as fd:
            cfg = instrument.parse_yaml_file(fd)
        assert len(cfg) == 2

    def test_duplicate_key_via_load(self, tmp_path):
        """Duplicate keys are caught when going through the load() path."""
        yaml_content = (
            "ophyd.Signal:\n"
            "- name: sig1\n"
            "ophyd.Signal:\n"
            "- name: sig2\n"
        )
        yaml_path = tmp_path / "dup_load.yaml"
        yaml_path.write_text(yaml_content)

        inst = Instrument({})
        with pytest.raises(exceptions.DuplicateYamlKey, match="ophyd.Signal"):
            inst.load(yaml_path)
