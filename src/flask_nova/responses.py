from __future__ import annotations
from typing import Any, get_origin, get_args
from flask import jsonify, make_response, Response as FlaskResponse, Request, g, request
import dataclasses
from pydantic import BaseModel, ValidationError
from .exceptions import HTTPException
from .status import status
import inspect
from .utils import resolve_annotation, _bind_custom_class_form, _bind_dataclass_form, _bind_pydantic_form
from .di import Depend
from .multi_part import FormMarker

class ResponseSerializer:
    """Serialize handler returns into Flask responses."""

    def serialize(self, result: Any, response_model: Any | None, flask_request: Request) -> FlaskResponse:
        def serialize_item(item: Any):
            if isinstance(item, tuple):
                return serialize_item(item[0])
            if isinstance(item, (str, bytes)):
                return item
            if hasattr(item, "model_dump"):
                return item.model_dump()
            if hasattr(item, "dict"):
                return item.dict()
            if hasattr(item, "dump"):
                return item.dump()
            if hasattr(item, "to_dict") and callable(getattr(item, "to_dict", None)):
                return item.to_dict()
            if dataclasses.is_dataclass(item) and not isinstance(item, type):
                return dataclasses.asdict(item)
            if isinstance(item, dict):
                return item
            raise TypeError(f"Cannot serialize object of type {type(item)}")

        # Already a Flask Response -> return as is
        if isinstance(result, FlaskResponse):
            return result

        # If response model exists, validate/shape output
        if response_model:
            try:
                origin = get_origin(response_model)
                args = get_args(response_model)

                if origin is list and args:
                    data = self._extract_data(result)
                    status_code = self._extract_status_code(result)
                    data = list(data) if not isinstance(data, list) else data
                    return make_response(jsonify([serialize_item(item) for item in data]), status_code)

                if origin is tuple and args:
                    data = self._extract_data(result)
                    status_code = self._extract_status_code(result)
                    if not isinstance(data, tuple):
                        data = (data,)
                    return make_response(jsonify([serialize_item(item) for item in data]), status_code)

                if origin is None and isinstance(response_model, type):
                    data = self._extract_data(result)
                    status_code = self._extract_status_code(result)
                    if isinstance(data, response_model):
                        model_instance = data
                    elif isinstance(data, BaseModel):
                        model_instance = response_model(**data.model_dump())
                    else:
                        model_instance = response_model(**data)
                    return make_response(jsonify(serialize_item(model_instance)), status_code)

                return make_response(jsonify(result), 200)

            except ValidationError as e:
                raise HTTPException(
                    status_code=status.INTERNAL_SERVER_ERROR,
                    detail="Response model validation failed: " + str(e),
                    title="Response Validation Error",
                    instance=flask_request.full_path
                )

        # Fallback
        if isinstance(result, tuple):
            data = self._extract_data(result)
            status_code = self._extract_status_code(result)
            return make_response(jsonify(serialize_item(data)), status_code)

        # Ensures str/bytes are wrapped
        if isinstance(result, (str, bytes)):
            return make_response(result)

        return make_response(jsonify(serialize_item(result)), 200)

    def _extract_data(self, result: Any):
        return result[0] if isinstance(result, tuple) else result

    def _extract_status_code(self, result: Any, default = 200) -> int:
        if isinstance(result, tuple):
            possible_status = result[1] if len(result) > 1 else default
            if not isinstance(possible_status, int) and hasattr(possible_status, "value") and isinstance(getattr(possible_status, "value", None), int):
                return possible_status.value
            elif isinstance(possible_status, int):
                return possible_status
        return default




async def _bind_route_parameters(func, sig: inspect.Signature, type_hints):
    """Bind parameters for route handlers, handling dependencies and request body parsing."""
    try:
        bound_values = {}

        for name, param in sig.parameters.items():
            annotation = type_hints.get(name)
            default = param.default
            base_type, dependency = resolve_annotation(annotation, default=default)

            if isinstance(default, Depend):
                dep_func = (dependency or default).dependency # type: ignore
                if not hasattr(g, "_nova_deps"):
                    g._nova_deps = {}
                if dep_func not in g._nova_deps:
                    if inspect.iscoroutinefunction(dep_func):
                        g._nova_deps[dep_func] = await dep_func()
                    else:
                        g._nova_deps[dep_func] = dep_func()
                bound_values[name] = g._nova_deps[dep_func]
                continue

            if isinstance(dependency, FormMarker):
                if request.content_type is None or not any(
                    request.content_type.startswith(t)
                    for t in ["multipart/form-data", "application/x-www-form-urlencoded"]
                ):
                    raise HTTPException(
                        status_code=status.UNSUPPORTED_MEDIA_TYPE,
                        detail="The endpoint expects form data, but the request has an incorrect content type."
                    )

                form_data = request.form.to_dict(flat=True)  # type: ignore
                if not form_data:
                    raise HTTPException(
                        status_code=status.UNPROCESSABLE_ENTITY,
                        detail="Empty form data. Ensure the request includes fields and uses the correct Content-Type.",
                        title="Empty Form Submission"
                    )

                form_type = dependency.type_
                if form_type and issubclass(form_type, BaseModel):
                    try:
                        bound_values[name] = _bind_pydantic_form(model_class=form_type)
                    except ValidationError as e:
                        raise HTTPException(
                            status_code=status.UNPROCESSABLE_ENTITY,
                            detail=e.errors(),
                            title="Form Validation Error"
                        )

                elif form_type and dataclasses.is_dataclass(form_type):
                    bound_values[name] = _bind_dataclass_form(form_type)

                elif isinstance(form_type, type):
                    bound_values[name] = _bind_custom_class_form(form_type)

                else:
                    bound_values[name] = form_data
                continue

            if base_type and isinstance(base_type, type) and issubclass(base_type, BaseModel):
                if request.content_type and request.content_type.startswith("application/json"):
                    try:
                        json_data = request.get_json(force=True)
                        bound_values[name] = base_type.model_validate(json_data)
                    except ValidationError as e:
                        raise HTTPException(
                            status_code=status.UNPROCESSABLE_ENTITY,
                            detail=e.errors(),
                            title="JSON Validation Error"
                        )
                else:
                    raise HTTPException(
                        status_code=status.UNSUPPORTED_MEDIA_TYPE,
                        detail="Expected JSON for this model, but received unsupported content type."
                    )
                continue

            if dataclasses.is_dataclass(base_type) and isinstance(base_type, type):
                if request.content_type and request.content_type.startswith("application/json"):
                    try:
                        json_data = request.get_json(force=True)
                        bound_values[name] = base_type(**json_data)
                    except Exception as e:
                        raise HTTPException(
                            status_code=status.UNPROCESSABLE_ENTITY,
                            detail=f"Dataclass JSON binding failed: {e}",
                            title="Dataclass Binding Error"
                        )
                else:
                    raise HTTPException(
                        status_code=status.UNSUPPORTED_MEDIA_TYPE,
                        detail="Expected JSON for dataclass, but received unsupported content type."
                    )
                continue

            if isinstance(base_type, type) and hasattr(base_type, "to_dict") and base_type not in (str, int, float, bool, dict, list):
                if request.content_type and request.content_type.startswith("application/json"):
                    try:
                        json_data = request.get_json(force=True)
                        bound_values[name] = base_type(**json_data)
                    except Exception as e:
                        raise HTTPException(
                            status_code=status.UNPROCESSABLE_ENTITY,
                            detail=f"Custom class JSON binding failed: {e}",
                            title="Custom Class Binding Error"
                        )
                else:
                    raise HTTPException(
                        status_code=status.UNSUPPORTED_MEDIA_TYPE,
                        detail="Expected JSON for custom class, but received unsupported content type."
                    )
                continue

            if base_type in (int, str, float, bool, dict, list):
                value = None
                if request.view_args and name in request.view_args:
                    value = request.view_args.get(name)
                else:
                    json_data = request.get_json(silent=True) or {}
                    value = json_data.get(name, default if default is not inspect.Parameter.empty else None)

                try:
                    if value is not None and base_type is not None:
                        if base_type is bool:
                            value = str(value).lower() in ("true", "1", "yes", "on")
                        else:
                            value = base_type(value)
                except Exception:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Parameter '{name}' must be of type {base_type.__name__}"
                    )
                bound_values[name] = value
                continue
            bound_values[name] = request

        return bound_values

    except Exception as e:
        raise HTTPException(
            status_code=500,
            title="Route Binding Error",
            detail=str(e),
        ) from e
