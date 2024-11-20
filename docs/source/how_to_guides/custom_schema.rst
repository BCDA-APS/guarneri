Custom Configurations
=====================

By default, :py:meth:`guarneri.instrument.Instrument.load()` expects
a TOML/YAML configuration file with a certain structure to it, it's
"schema". However, this is **easy to override**, allowing for custom
schema, or even entirely new sources of configuration (possibly not
even a file).

To do this, subclass :py:meth:`guarneri.instrument.Instrument`, and
override one of the following methods:

:py:meth:`~guarneri.instrument.Instrument.parse_config`
    Called for all configurations first, may call other methods
    below. Override for an entirely new source of configuration.
:py:meth:`~guarneri.instrument.Instrument.parse_toml_file`
   Called if *config_file* has the ``.toml`` extension. Override to
   customize the TOML schema.
:py:meth:`~guarneri.instrument.Instrument.parse_yaml_file`
   Called if *config_file* has the ``.yaml`` extension. Override to
   customize the YAML schema.

The new method should **open and parse the file** (or otherwise
retrieve the configuration), then **produce a sequence of device
defitions**.

Each method **accepts the path to the config file** as its
*config_file* argument. Despite the name, this argument could also be
the URI of a web API, database, or other non-file source of
configuration.

These methods also need to return a sequence of device defitions,
*devices*, that will be used by the
:py:meth:`~guarneri.instrument.Instrument` to create and connect to
actual device objects. Each item in *devices* should be a dictionary
with the following structure:

.. code-block:: python

   {
      "device_class": "ophyd.motor.EpicsMotor",
      "kwargs": {
          "name": "my_device",
          "prefix": "255idcVME:m1",
       },
   }

This defintion will result in the following call:

.. code-block:: python

   from ophyd.motor import EpicsMotor
   EpicsMotor(name="my_device", prefix="255idcVME:m1")


Example
-------

Putting it all together, the following example shows how to implement
this approach to create the same static devices regardless of the
configuration.


.. code-block:: python

   from guarneri import Instrument as InstrumentBase

   class Instrument(InstrumentBase):
       def parse_config(config_file):
           with open(config_file, mode="rt") as fd:
               # Do something with the file contents here
               pass
           return [
               {
                   "device_class": "ophyd.motor.EpicsMotor",
                   "kwargs": {
                       "name": "my_device",
                       "prefix": "255idcVME:m1",
                   },
               }
           ]
