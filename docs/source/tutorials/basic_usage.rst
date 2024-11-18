Getting Started
===============

This tutorial will guide you through how to set up a basic Guarneri
:py:class:`~guarneri.instrument.Instrument()` instance that can create
devices from a configuration file.

The steps are:

1. Create an instance of :py:class:`~guarneri.instrument.Instrument()`
2. Load a configuration file to create devices
3. Connect to those devices


Create an Instrument
--------------------

The first step is to create an instance of
:py:class:`~guarneri.instrument.Instrument()`. We will also provide it
some hints about what devices to create.

.. code-block:: python

   from guarneri import Instrument
   from ophyd_async.epics.motor import Motor
   
   instrument = Instrument({"motor": Motor})


Load Config File
----------------

Next we need to write a configuration file that works with our
instrument device.

.. code-block:: toml
   :caption: config.toml

   [[ motor ]]
   name = "m1"
   prefix = "255idcVME:m1"
   
   [[ motor ]]
   name = "m2"
   prefix = "255idcVME:m2"

Then, back in our main file we can load in this configuration file:

.. code-block:: python
   :caption: startup.py

   instrument.load("config.toml")

This command has now read the contents of the configuration file, and
has created the corresponding devices, though these devices are **not
yet connected**. These can be accessed using the Instrument's
:py:meth:`~guarneri.instrument.Instrument.devices` attribute.

.. code-block:: python

   assert isinstance(instrument.devices['m1'], Motor)

