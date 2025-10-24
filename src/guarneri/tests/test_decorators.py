from typing import Sequence

import pytest

from guarneri import Registry


class Motor:
    def __init__(self, name: str):
        self.name = name


@pytest.fixture()
def registry():
    return Registry(auto_register=False)


class TestInjectDevices:
    """Tests related to the @registry.inject_devices() decorator."""

    @staticmethod
    def test_as_positional_arg(registry):
        the_motor = {}  # To stash the plan arguments

        @registry.inject_devices(a_motor="my_motor")
        def my_plan(a_motor, /):
            the_motor["device"] = a_motor

        # Define a new motor in the registry
        my_motor = Motor(name="my_motor")
        registry.register(my_motor)
        # Execute the plan and see if the device was looked up
        my_plan()
        assert the_motor["device"] is my_motor

    @staticmethod
    def test_as_kwarg(registry):
        the_motor = {}  # To stash the plan arguments

        @registry.inject_devices(a_motor="my_motor")
        def my_plan(*, a_motor):
            the_motor["device"] = a_motor

        # Define a new motor in the registry
        my_motor = Motor(name="my_motor")
        registry.register(my_motor)
        # Execute the plan and see if the device was looked up
        my_plan()
        assert the_motor["device"] is my_motor

    @staticmethod
    def test_sequence_of_devices(registry):
        """The type annotation says it should be a sequence, so give it a sequence."""
        the_motor = {}  # To stash the plan arguments

        @registry.inject_devices(some_motors="my_motor")
        def my_plan(some_motors: Sequence):
            the_motor["devices"] = some_motors

        # Define a new motor in the registry
        my_motor = Motor(name="my_motor")
        registry.register(my_motor)
        # Execute the plan and see if the device was looked up
        my_plan()
        assert the_motor["devices"] == [my_motor]

    @staticmethod
    def test_device_passed_as_arg(registry):
        """Check that the decorator doesn't overwrite arguments passed in the
        normal way."""
        the_motor = {}  # To stash the plan arguments

        @registry.inject_devices(a_motor="my_motor")
        def my_plan(a_motor, /):
            the_motor["device"] = a_motor

        my_motor = Motor(name="my_motor")
        other_motor = Motor(name="other_motor")
        registry.register(my_motor)
        my_plan(other_motor)
        assert the_motor["device"] is other_motor

    @staticmethod
    def test_device_passed_as_kwarg(registry):
        """Check that the decorator doesn't overwrite arguments passed in the normal way."""
        the_motor = {}  # To stash the plan arguments

        @registry.inject_devices(a_motor="my_motor")
        def my_plan(a_motor):
            the_motor["device"] = a_motor

        my_motor = Motor(name="my_motor")
        other_motor = Motor(name="other_motor")
        registry.register(my_motor)
        my_plan(a_motor=other_motor)
        assert the_motor["device"] is other_motor

    @staticmethod
    def test_device_name_passed_as_arg(registry):
        """Checks that the decorator accepts a device name and resolves it into the device."""
        the_motor = {}  # To stash the plan arguments

        @registry.inject_devices(a_motor=None)
        def my_plan(a_motor):
            the_motor["device"] = a_motor

        my_motor = Motor(name="my_motor")
        registry.register(my_motor)
        my_plan("my_motor")
        assert the_motor["device"] is my_motor

    @staticmethod
    def test_device_name_passed_as_kwarg(registry):
        """Checks that the decorator accepts a device name and resolves it into the device."""
        the_motor = {}  # To stash the plan arguments

        @registry.inject_devices(a_motor=None)
        def my_plan(a_motor):
            the_motor["device"] = a_motor

        my_motor = Motor(name="my_motor")
        registry.register(my_motor)
        my_plan(a_motor="my_motor")
        assert the_motor["device"] is my_motor
