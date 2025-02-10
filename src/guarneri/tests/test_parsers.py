from pathlib import Path

import pytest

from guarneri import parse_config

toml_file = Path(__file__).parent.parent.resolve() / "iconfig_example.toml"


@pytest.fixture()
def config_io():
    with open(toml_file, mode="rt") as fd:
        yield fd


def test_parse_config(config_io):
    cfg = parse_config(config_io, config_format="toml")
    assert len(cfg) > 0
    dfn = cfg[0]
    assert dfn["device_class"] == "async_device"
