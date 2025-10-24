from . import exceptions  # noqa: F401
from ._version import get_versions  # noqa: F401
from .instrument import Instrument  # noqa: F401
from .registry import Registry  # noqa: F401

__version__ = get_versions()["version"]
del get_versions

# TODO: fill this in with appropriate star imports:
__all__ = ["Instrument", "exceptions", "Registry"]
