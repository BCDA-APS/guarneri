from collections import ChainMap
from collections.abc import Mapping

from typing import IO, Callable

import tomlkit


def parse_config(config_file: IO, config_format: str, parsers: Mapping[str, Callable] = {}) -> list[dict]:
    """Parse an instrument configuration file.

    *parsers* can contain a mapping of language (e.g. "yaml") to a
    callable that will parse that language. Each parser should return
    a sequence of device definitions, similar to:

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

    If a parser for a given language is not found, the default parser
    for this language will be used.

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
    # Add in default parsers
    parsers = ChainMap(parsers, default_parsers)
    # Parse the file
    for name in ["all", config_format, "default"]:
        if name in parsers:
            return parsers[name](config_file)
    else:
        raise ValueError(f"Unhandled config file format: {config_format}")


def parse_json_file(config_file: IO[str]) -> list[dict]:
    """Produce device definitions from a JSON file.

    See ``Instrument.parse_config()`` for details.

    """


def parse_yaml_file(config_file: IO[str]) -> list[dict]:
    """Produce device definitions from a YAML file.

    See ``Instrument.parse_config()`` for details.

    """
    raise NotImplementedError


def parse_toml_file(config_file: IO[str]) -> list[dict]:
    """Produce device definitions from a TOML file.

    See ``Instrument.parse_config()`` for details.

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



default_parsers = {
    "json": parse_json_file,
    "yaml": parse_yaml_file,
    "toml": parse_toml_file,
}
