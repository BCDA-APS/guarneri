# src/guarneri/decorators.py
"""Decorators for accessing instrument devices in plans."""

import functools
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from .instrument import Instrument

# Track the most recently created instrument
_instrument: Optional["Instrument"] = None


def with_registry(func: Callable) -> Callable:
    """
    Decorator that provides access to the instrument's device registry.
    Injects 'oregistry' as the first argument to the decorated function.
    """

    @functools.wraps(func)
    def wrapper(*args, oregistry=None, **kwargs):
        if oregistry is None:
            if _instrument is None:
                raise RuntimeError("Instrument not set. Call set_instrument() first.")
            else:
                oregistry = _instrument.devices
        return func(oregistry, *args, **kwargs)

    return wrapper
