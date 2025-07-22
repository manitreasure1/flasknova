from flask import Flask as _Flask, Blueprint as _Blueprint, request, jsonify, g, make_response
from flasknova.exceptions import HTTPException, ResponseValidationError
from typing import get_type_hints, get_origin, get_args, Literal, Optional
from pydantic import BaseModel, ValidationError
from flasknova.d_injection import Depend
from flasknova.status import status
from flasknova.swagger import create_swagger_blueprint
from flasknova.logger import get_flasknova_logger
from functools import wraps
import dataclasses
import inspect

Method = Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
logger = get_flasknova_logger()

async def _bind_route_parameters(func, sig: inspect.Signature, type_hints):
    """Bind parameters for route handlers, handling dependencies and request body parsing."""
    bound_values = {}
    for name, param in sig.parameters.items():
        annotation = type_hints.get(name)
        default = param.default
        if isinstance(default, Depend):
            dep_func = default.dependency
            if not hasattr(g, "_nova_deps"):
                g._nova_deps = {}
            if dep_func not in g._nova_deps:
                if inspect.iscoroutinefunction(dep_func):
                    g._nova_deps[dep_func] = await dep_func()
                else:
                    g._nova_deps[dep_func] = dep_func()
            bound_values[name] = g._nova_deps[dep_func]

        elif annotation and issubclass(annotation, BaseModel):
            try:
                json_data = request.get_json(force=True)
                bound_values[name] = annotation(**json_data)
            except ValidationError as e:
                raise ResponseValidationError(detail=str(e), original_exception=e, instance=request.full_path)
        elif annotation and hasattr(annotation, '__init__') and annotation not in (str, int, float, bool, dict, list):
            try:
                json_data = request.get_json(force=True)
                bound_values[name] = annotation(**json_data)
            except Exception as e:
                raise ResponseValidationError(detail=f"Custom model binding failed: {e}", original_exception=e, instance=request.full_path)
        elif annotation in (int, str, float, bool, dict, list):
            value = request.view_args.get(name) if request.view_args and name in request.view_args else None
            if value is None:
                json_data = request.get_json(silent=True) or {}
                value = json_data.get(name, default if default is not inspect.Parameter.empty else None)
            try:
                if value is not None and annotation is not None:
                    if annotation is bool:
                        value = value if isinstance(value, bool) else str(value).lower() in ("true", "1", "yes", "on")
                    else:
                        value = annotation(value)
            except Exception:
                raise HTTPException(status_code=400, detail=f"Parameter '{name}' must be of type {annotation.__name__}")
            bound_values[name] = value
        else:
            bound_values[name] = request
    return bound_values


def extract_status_code(data, default=200):
    """Extract status code from tuple or enum, or return default."""
    if isinstance(data, tuple):
        possible_status = data[1] if len(data) > 1 else default
        if not isinstance(possible_status, int) and hasattr(possible_status, 'value') and isinstance(getattr(possible_status, 'value', None), int):
            return possible_status.value
        elif isinstance(possible_status, int):
            return possible_status
    return default

def extract_data(data):
    """Extract main data from tuple or return as is."""
    return data[0] if isinstance(data, tuple) else data

def _serialize_response(result, response_model, request):    
    def serialize_item(item):
        if isinstance(item, tuple):
            return serialize_item(item[0])
        elif isinstance(item, (str, bytes)):
            return item
        elif hasattr(item, 'model_dump'):
            return item.model_dump()
        elif hasattr(item, 'dict'):
            return item.dict()
        elif hasattr(item, 'dump'):
            return item.dump()
        elif dataclasses.is_dataclass(item) and not isinstance(item, type):
            return dataclasses.asdict(item)
        elif hasattr(item, 'to_dict') and callable(getattr(item, 'to_dict', None)):
            return item.to_dict() #type: ignore
        elif isinstance(item, dict):
            return item
        raise TypeError(f"Cannot serialize object of type {type(item)}")

    # If the result is already a Flask Response (e.g., from make_response), return as is
    if hasattr(result, 'is_streamed') and callable(getattr(result, 'get_data', None)):
        return result

    if response_model:
        try:
            origin = get_origin(response_model)
            args = get_args(response_model)
            if origin is list and args:
                data = extract_data(result)
                status_code = extract_status_code(result)
                data = list(data) if not isinstance(data, list) else data
                return make_response(jsonify([serialize_item(item) for item in data]), status_code)
            elif origin is tuple and args:
                data = extract_data(result)
                status_code = extract_status_code(result)
                if not isinstance(data, tuple):
                    data = (data,)
                return make_response(jsonify([serialize_item(item) for item in data]), status_code)

            elif origin is None and isinstance(response_model, type):
                data = extract_data(result)
                status_code = extract_status_code(result)
                if isinstance(data, response_model):
                    model_instance = data
                elif isinstance(data, BaseModel):
                    model_instance = response_model(**data.model_dump())
                else:
                    model_instance = response_model(**data)
                return make_response(jsonify(serialize_item(model_instance)), status_code)
            # If not a model or list, just jsonify the result
            return make_response(jsonify(result), 200)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.INTERNAL_SERVER_ERROR,
                detail="Response model validation failed: " + str(e),
                title="Response Validation Error",
                instance=request.full_path
            )
    # Fallback serialization for result
    if isinstance(result, tuple):
        data = extract_data(result)
        status_code = extract_status_code(result)
        return make_response(jsonify(serialize_item(data)), status_code)
    return make_response(jsonify(serialize_item(result)), 200) if not isinstance(result, (str, bytes)) else result


class FlaskNova(_Flask):
    def __init__(self, import_name):
        super().__init__(import_name)
        self.register_error_handler(HTTPException, self._handle_http_exception)

    
    def setup_swagger(self, info:Optional[dict]=None):
        self._flasknova_openapi_info = info or {}
        
        swagger_enabled = self.config.get("FLASKNOVA_SWAGGER_ENABLED", True)
        docs_path = self.config.get("FLASKNOVA_SWAGGER_ROUTE", "/docs")

        if not swagger_enabled:
            return
        swagger_bp = create_swagger_blueprint(docs_route=docs_path)
        self.register_blueprint(swagger_bp)

        @self.after_request
        def add_swagger_cache_headers(response):
            if request.path.startswith(docs_path):
                if response.mimetype in ['text/css', 'application/javascript']:
                    response.headers['Cache-Control'] = 'public, max-age=86400'
                else:
                    response.headers['Cache-Control'] = 'no-store'
            return response

    def _handle_http_exception(self, error: HTTPException):
        problem = {
            "type": error.type,
            "title": error.title,
            "status": error.status_code,
            "detail": error.detail,
            "instance": error.instance or request.full_path
        }
        return jsonify(problem), error.status_code

    def route(
            self,
            rule: str,
            *,
            methods: list[Method] = ["GET"],
            tags: list[str] | None = None,
            response_model: type | None = None,
            summary: str | None = None,
            description: str | None = None,
            **options
        ):      
        def decorator(func):
            is_async = inspect.iscoroutinefunction(func)
            sig = inspect.signature(func)
            type_hints = get_type_hints(func)
            
            func._flasknova_tags = tags or []
            func._flasknova_response_model = response_model
            func._flasknova_summary = summary
            func._flasknova_description = description

            @wraps(func)
            async def wrapper(*args, **kwargs):
                bound_values = await _bind_route_parameters(func, sig, type_hints)
                if isinstance(bound_values, tuple):
                    return bound_values 
                try:
                    if is_async:
                        result = await func(**bound_values)
                    else:
                        result = func(**bound_values)
                except HTTPException as e:
                    raise                
                return _serialize_response(result, response_model, request)

            # Filter out custom keys before passing to Flask’s add_url_rule()
            FLASK_ALLOWED_ROUTE_ARGS = {
                "methods", "endpoint", "defaults", "strict_slashes",
                "redirect_to", "alias", "host", "provide_automatic_options"
            }
            flask_options = {
                k: v for k, v in options.items() if k in FLASK_ALLOWED_ROUTE_ARGS
            }

            # Clean up any lingering custom keys
            flask_options.pop("response_model", None)
            flask_options.pop("tags", None)
            if hasattr(func, "__dict__"):
                func.__dict__.pop("response_model", None)
                func.__dict__.pop("tags", None)

            self.add_url_rule(rule,
                              endpoint=func.__name__,
                              view_func=wrapper,
                              methods=methods,
                              **flask_options)
            return func

        return decorator


class NovaBlueprint(_Blueprint):
    def route(
            self,
            rule: str,
            *,
            methods: list[Method] = ["GET"],
            tags: list[str] | None = None,
            response_model: type | None = None,
            summary: str | None = None,
            description: str | None = None,
            **options
        ):  
        """
        A Blueprint-style .route() that accepts:
        - methods, tags,
        - response_model 
        """

        def decorator(func):
            is_async = inspect.iscoroutinefunction(func)
            sig = inspect.signature(func)
            type_hints = get_type_hints(func)

            func._flasknova_tags = tags or []
            func._flasknova_response_model = response_model
            func._flasknova_summary = summary
            func._flasknova_description = description

            @wraps(func)
            async def wrapper(*args, **kwargs):
                bound_values = await _bind_route_parameters(func, sig, type_hints)
                if isinstance(bound_values, tuple):
                    return bound_values  # error response from _bind_route_parameters
                try:
                    if is_async:
                        result = await func(**bound_values)
                    else:
                        result = func(**bound_values)
                except HTTPException as e:
                    raise
                return _serialize_response(result, response_model, request)

            # Filter out custom keys before passing to Flask’s add_url_rule()
            FLASK_ALLOWED_ROUTE_ARGS = {
                "methods", "endpoint", "defaults", "strict_slashes",
                "redirect_to", "alias", "host", "provide_automatic_options"
            }
            flask_options = {
                k: v for k, v in options.items() if k in FLASK_ALLOWED_ROUTE_ARGS
            }

            # Clean up any lingering custom keys
            flask_options.pop("response_model", None)
            flask_options.pop("tags", None)
            if hasattr(func, "__dict__"):
                func.__dict__.pop("response_model", None)
                func.__dict__.pop("tags", None)

            # Finally register the route on this blueprint
            self.add_url_rule(rule,
                              endpoint=func.__name__,
                              view_func=wrapper,
                              methods=methods,
                              **flask_options)
            return func

        return decorator



