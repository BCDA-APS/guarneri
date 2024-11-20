from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from ophyd import Component
from ophyd import Device as DeviceV1
from ophyd import EpicsSignal
from ophyd_async.core import Device

from guarneri import Instrument, exceptions

toml_file = Path(__file__).parent.parent.resolve() / "iconfig_example.toml"


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
        name="",
        auto_name: bool = None,
        *args,
        **kwargs,
    ):
        super().__init__(name=name, *args, **kwargs)


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


@pytest.mark.parametrize("cfg_file", [toml_file, str(toml_file)])
def test_parse_config(cfg_file, instrument):
    cfg = instrument.parse_config(cfg_file)
    assert len(cfg) > 0
    dfn = cfg[0]
    assert dfn["device_class"] == "async_device"


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
