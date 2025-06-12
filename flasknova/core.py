from flask import Flask as _Flask, Blueprint as _Blueprint, request, jsonify, g
from typing import get_type_hints
from pydantic import BaseModel, ValidationError
import inspect
from .exceptions import HTTPException, ResponseValidationError
from .status import status
from .d_injection import Depend



async def _bind_route_parameters(func, sig, type_hints):
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
        else:
            bound_values[name] = request
    return bound_values


def _serialize_response(result, response_model, request):
    if response_model:
        try:
            if isinstance(result, response_model):
                model_instance = result
            else:
                model_instance = response_model(**result)
            return jsonify(model_instance.model_dump())
        except ValidationError as e:
            raise HTTPException(
                status_code=status.INTERNAL_SERVER_ERROR,
                detail="Response model validation failed: " + str(e),
                title="Response Validation Error",
                instance=request.full_path
            )
    if isinstance(result, BaseModel):
        return jsonify(result.model_dump())
    return result


class FlaskNova(_Flask):
    def __init__(self, import_name):
        super().__init__(import_name)
        self.register_error_handler(HTTPException, self._handle_http_exception)

    def _handle_http_exception(self, error: HTTPException):
        problem = {
            "type": error.type,
            "title": error.title,
            "status": error.status_code,
            "detail": error.detail,
            "instance": error.instance or request.full_path
        }
        return jsonify(problem), error.status_code

    def route(self, rule, *, methods=["GET"], tags=None, response_model=None, **options):

        def decorator(func):
            is_async = inspect.iscoroutinefunction(func)
            sig = inspect.signature(func)
            type_hints = get_type_hints(func)
            func._flasknova_tags = tags or []
            func._flasknova_response_model = response_model

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





class NovaBlueprint(_Blueprint):
    def route(self, rule, *, methods=["GET"], tags=None, response_model=None, **options):
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
