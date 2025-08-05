
from flask import Flask as _Flask, Blueprint as _Blueprint, request, jsonify, g, make_response
from typing import Any, get_type_hints, get_origin, get_args, Literal, Optional, List, Union
from flask_nova.exceptions import HTTPException, ResponseValidationError
from flask_nova.d_injection import Depend, resolve_dependencies
from flask_nova.swagger import create_swagger_blueprint
from flask_nova.logger import get_flasknova_logger
from pydantic import BaseModel, ValidationError
from flask_nova.status import status
from functools import wraps
from enum import Enum
import dataclasses
import inspect
from flask_nova.multi_part import Form
from flask_nova.utils import (
                    _bind_custom_class_form,
                   _bind_dataclass_form,
                   _bind_pydantic_form,
                   resolve_annotation,
                   extract_status_code,
                   extract_data
                   )


Method = Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
logger = get_flasknova_logger()


async def _bind_route_parameters(func, sig: inspect.Signature, type_hints):
    """Bind parameters for route handlers, handling dependencies and request body parsing."""
    bound_values = {}
    for name, param in sig.parameters.items():
        annotation = type_hints.get(name)
        base_type, dependency = resolve_annotation(annotation)
        default = param.default

        if isinstance(default, Depend):
            dep_func = (dependency or default).dependency
            if not hasattr(g, "_nova_deps"):
                g._nova_deps = {}
            if dep_func not in g._nova_deps:
                if inspect.iscoroutinefunction(dep_func):
                    g._nova_deps[dep_func] = await dep_func()
                else:
                    g._nova_deps[dep_func] = dep_func()
            bound_values[name] = g._nova_deps[dep_func]

        # Todo: resolve form 500 error 
        elif dependency is Form:
            if request.content_type is None or not any(
                request.content_type.startswith(t)
                for t in ["multipart/form-data", "application/x-www-form-urlencoded"]
            ):
                raise HTTPException(
                    status_code=status.UNSUPPORTED_MEDIA_TYPE,
                    detail="The endpoint expects form data, but the request has an incorrect content type."
                )
            if isinstance(base_type, type) and issubclass(base_type, BaseModel):
                bound_values[name] = _bind_pydantic_form(base_type)
            elif dataclasses.is_dataclass(base_type):
                bound_values[name] = _bind_dataclass_form(base_type)
            elif isinstance(base_type, type):
                bound_values[name] = _bind_custom_class_form(base_type)


        elif base_type and isinstance(base_type, type) and issubclass(annotation, BaseModel):
            try:
                bound_values[name] = base_type.model_validate(request.form)
            except ValidationError as e:
                raise ResponseValidationError(detail=str(e), original_exception=e, instance=request.full_path)
        elif base_type and hasattr(annotation, '__init__') and annotation not in (str, int, float, bool, dict, list):
            try:
                json_data = request.get_json(force=True)
                bound_values[name] = annotation(**json_data)
            except Exception as e:
                raise ResponseValidationError(detail=f"Custom model binding failed: {e}", original_exception=e, instance=request.full_path)
        elif base_type in (int, str, float, bool, dict, list):
            value = request.view_args.get(name) if request.view_args and name in request.view_args else None
            if value is None:
                json_data = request.get_json(silent=True) or {}
                value = json_data.get(name, default if default is not inspect.Parameter.empty else None)
            try:
                if value is not None and base_type is not None:
                    if annotation is bool:
                        value = value if isinstance(value, bool) else str(value).lower() in ("true", "1", "yes", "on")
                    else:
                        value = annotation(value)
            except Exception:
                raise HTTPException(status_code=400, detail=f"Parameter '{name}' must be of type {base_type.__name__}")
            bound_values[name] = value
        else:
            bound_values[name] = request
    return bound_values





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
            tags: Optional[List[Union[str, Enum]]] = None,
            response_model: Any | None = None,
            summary: str | None = "",
            description: str | None = "",
            provide_automatic_options: bool | None = None,
            **options
        ):
       
        def decorator(func):
            is_async = inspect.iscoroutinefunction(func)
            sig = inspect.signature(func)
            type_hints = get_type_hints(func)
            
            f = resolve_dependencies(func)

            setattr(f, "_flasknova_tags", tags or [])
            setattr(f, "_flasknova_response_model", response_model)
            setattr(f, "_flasknova_summary", summary)
            setattr(f, "_flasknova_description", description)

            @wraps(f)
            async def wrapper(*args, **kwargs):
                bound_values = await _bind_route_parameters(f, sig, type_hints)
                if isinstance(bound_values, tuple):
                    return bound_values 
                try:
                    if is_async:
                        result = await f(**bound_values)
                    else:
                        result = f(**bound_values)
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
                              provide_automatic_options=provide_automatic_options,
                              **flask_options)
            return func

        return decorator


class NovaBlueprint(_Blueprint):
    def route(
            self,
            rule: str,
            *,
            methods: list[Method] = ["GET"],
            tags: Optional[List[Union[str, Enum]]] = None,
            response_model: Any | None = None,
            summary: str | None = "",
            description: str | None = "",
            provide_automatic_options: bool | None = None,
            **options: Any
        ):  
        """
        ### ~ Example
        ```
        class GreetModel(BaseModel):
            message: str
            name: str

        @app.route("/",
            methods=["GET"],
            tags=["Greet"],
            summary="Greet Flask",
            response_model=GreetModel,
            description="Recieve Greetings from flask"
        )
        def index():
            return {"message=Hello, name=Flask!"}
        ```
        #### A Blueprint-style `.route()` that accepts:
        - methods,
        - tags,
        - response_model,
        - summary,
        - description,
        - provide_automatic_options,
        - **options
        """

        def decorator(func):
            is_async = inspect.iscoroutinefunction(func)
            sig = inspect.signature(func)
            type_hints = get_type_hints(func)

            f = resolve_dependencies(func)


            setattr(f, "_flasknova_tags", tags or [])
            setattr(f, "_flasknova_response_model", response_model)
            setattr(f, "_flasknova_summary", summary)
            setattr(f, "_flasknova_description", description)

            @wraps(f)
            async def wrapper(*args, **kwargs):
                bound_values = await _bind_route_parameters(f, sig, type_hints)
                if isinstance(bound_values, tuple):
                    return bound_values  # error response from _bind_route_parameters
                try:
                    if is_async:
                        result = await f(**bound_values)
                    else:
                        result = f(**bound_values)
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
                              provide_automatic_options=provide_automatic_options,
                              **flask_options)
            return func

        return decorator



