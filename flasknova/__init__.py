from .core import  FlaskNova, NovaBlueprint
from .exceptions import HTTPException, ResponseValidationError
from .logger import get_flasknova_logger
from .status import status
from .d_injection import Depend
from .swagger import swagger_bp
from flask import request

logger = get_flasknova_logger()

# Auto-register Swagger blueprint on FlaskNova app creation
_original_flasknova_init = FlaskNova.__init__

def _flasknova_init_with_swagger(self, import_name, *args, **kwargs):
    _original_flasknova_init(self, import_name, *args, **kwargs)
    self.register_blueprint(swagger_bp, url_prefix="/flasknova")
    
    # Add cache headers for Swagger UI static assets
    @self.after_request
    def add_swagger_cache_headers(response):
        if request.path.startswith('/flasknova/docs'):
            if response.mimetype in ['text/css', 'application/javascript']:
                response.headers['Cache-Control'] = 'public, max-age=86400'
            else:
                response.headers['Cache-Control'] = 'no-store'
        return response

FlaskNova.__init__ = _flasknova_init_with_swagger

__all__ = [
    "FlaskNova",
    "NovaBlueprint",
    "Depend",
    "HTTPException",
    "ResponseValidationError",
    "status",
    "get_flasknova_logger",
    "logger",
]