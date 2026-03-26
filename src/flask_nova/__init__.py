from .core import FlaskNova
from .router import NovaBlueprint
from .multi_part import Form, guard
from .exceptions import HTTPException, ResponseValidationError
from .di import Depend
from .status import status
from .logger import get_flasknova_logger

spa = None
get_esbuild_binary = None
try:
    import spa as _spa  # optional package installed via flask-nova[spa]
    spa = _spa
    if hasattr(spa, "get_esbuild_binary"):
        get_esbuild_binary = spa.get_esbuild_binary
except ImportError:
    pass

__all__ = [
    "FlaskNova",
    "NovaBlueprint",
    "Form",
    "guard",
    "HTTPException",
    "ResponseValidationError",
    "Depend",
    "get_flasknova_logger",
    "status",
]
if spa is not None:
    __all__.append("spa")
if get_esbuild_binary is not None:
    __all__.append("get_esbuild_binary")
