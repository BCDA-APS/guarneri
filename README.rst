==========================
Guarneri Instrument Maker
==========================


.. image:: https://img.shields.io/pypi/v/guarneri.svg
        :target: https://pypi.python.org/pypi/guarneri


A package for creating Ophyd and Ophyd-async devices from configuration
files.

Instead of instantiating devices directly in python, Guarneri reads a
configuration file and creates/connects the devices for you. This
provides the following benefits:

1) Beamline configuration is in a human-readable configuration file (e.g. TOML).
2) Other tools can modify the configuration file if needed.
3) Devices can be connected in parallel (faster).
4) Missing devices are handled gracefully.
5) Devices can be simulated/mocked by changing a single value in the config file.


Usage
-----

Let's say **you have some ophyd and ophyd-async devices** defined
(with type hints) in a file called ``devices.py``. This is not
specific to guarneri, just regular Ophyd.

.. code-block:: python

    from ophyd_async.epics import epics_signal_rw
    from ophyd_async.core import AsyncDevice
    from ophyd import Device, Component
    
    from guarneri import Instrument
    
    class MyDevice(Device):
        description = Component(".DESC")
    
    
    class MyAsyncDevice(AsyncDevice):
        def __init__(self, prefix: str, name: str = ""):
            self.description = epics_signal_rw(str, f"{prefix}.DESC")
    	super().__init__(name=name)


    def area_detector_factory(hdf: bool=True):
        # Create devices here using the arguments
        area_detector = ...
	return area_detector


Instead of instantiating these in a python startup script, Guarneri
will let you **create devices from a TOML configuration file**. First
we create a TOML file (e.g. ``instrument.toml``) with the necessary parameters, these map
directly onto the arguments of the device's ``__init__()``, or the
arguments of a factory that returns a device.


.. code-block:: toml

    [my_device.device1]
    prefix = '255id:'
    
    [async_device.device3]
    prefix = '255id:'

    [area_detector.sim_det]
    hdf = true


Then in your beamline startup code, create a Guarneri instrument and
load the config files.

.. code-block:: python

    from io import StringIO
		
    from devices import MyDevice, MyAsyncDevice, area_detector_factory
    
    # Prepare the instrument device
    instrument = Instrument({
        "my_device": MyDevice,
	"async_device": MyAsyncDevice,
	"area_detector": area_detector_factory,
    })

    # Create the devices from the TOML configuration file
    instrument.load_config_files("instrument.toml")
    # Optionally connect all the devices
    await instrument.connect_devices()

    # Now use the devices for science!
    instrument.devices['device_1'].description.get()


The first argument to ``guarneri.Instrument.__init__()`` is a mapping
of TOML section names to device classes. Guarneri then introspects the
device or factory to decide which TOML keys and types are valid. In
the above example, the heading ``[my_device.device1]`` will create an
instance of ``MyDevice()`` with the name ``"device1"`` and prefix
``"255id:"``. This is equivalent to ``MyDevice(prefix="255id:",
name="device1")``.


What About Happi?
-----------------

Happi has a similar goal to Guarneri, but with a different
scope. While Happi is meant for facility-level configuration (e.g.
LCLS), Guarneri is aimed at individual beamlines at a synchrotron.
Happi uses ``HappiItem`` classes with ``ItemInfo``
objects to describe the devices definitions, while Guarneri uses the
device classes themselves. Happi provides a python client for adding
and modifying the devices, while Guarneri uses human-readable
configuration files.

**Which one is better?** Depends on what you're trying to do. If you
want a **flexible and scalable** system that **shares devices across a
facility**, try Happi. If you want a way to **get devices running
quickly** on your beamline before users show up, try Guarneri.


Documentation
-------------

Sphinx-generated documentation for this project can be found here:
https://spc-group.github.io/guarneri/

Requirements
------------

Describe the project requirements (i.e. Python version, packages and how to install them)

Installation
------------

The following will download the package and load it into the python environment.

.. code-block:: bash

    git clone https://github.com/spc-group/guarneri
    pip install guarneri

For development of guarneri, install as an editable project with all
development dependencies using:

.. code-block:: bash

    pip install -e ".[dev]"


Running the Tests
-----------------
::

  $ pip install -e .
  $ pytest -vv
