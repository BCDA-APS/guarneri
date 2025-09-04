from . import exceptions
from ._version import get_versions
from .instrument import Instrument

__version__ = get_versions()["version"]
del get_versions

# TODO: fill this in with appropriate star imports:
__all__ = ["Instrument", "exceptions"]
