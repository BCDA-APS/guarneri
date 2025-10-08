# src/guarneri/decorators.py
"""Decorators for accessing instrument devices in plans."""

import functools
import inspect
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .instrument import Instrument

# Track the most recently created instrument
_current_instrument: Optional["Instrument"] = None


def with_registry(func: Callable) -> Callable:
    """
    Decorator that provides access to the instrument's device registry.
    Injects 'oregistry' as the first argument to the decorated function.

    Example:
        @with_registry
        def my_plan(oregistry, num: int = 1):
            detector = oregistry["my_detector"]
            yield from bp.count([detector], num=num)
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if _current_instrument is None:
            raise RuntimeError(
                "No instrument has been created. Call init_instrument() first."
            )
        return func(_current_instrument.devices, *args, **kwargs)

    return wrapper


def with_devices(*device_names):
    """
    Decorator that resolves specific named devices from strings to device objects.

    Example:
        @with_devices("sim_det", "eric_motor")
        def my_plan(eric_motor="my_motor", sim_det="my_detector"):
            yield from bps.mv(eric_motor, 5)
            yield from bp.count([sim_det])
    """

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if _current_instrument is None:
                raise RuntimeError(
                    "No instrument has been created. Call init_instrument() first."
                )
            oregistry = _current_instrument.devices
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()

            # Replace specified device names with actual devices
            for param_name in device_names:
                if param_name in bound.arguments:
                    value = bound.arguments[param_name]
                    if isinstance(value, str) and value in oregistry:
                        bound.arguments[param_name] = oregistry[value]

            return func(*bound.args, **bound.kwargs)

        return wrapper

    return decorator
