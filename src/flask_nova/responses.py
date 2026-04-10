from __future__ import annotations
from typing import Any, Callable, Dict, get_origin, get_args
from flask import jsonify, make_response, Response as FlaskResponse, Request, request
import dataclasses
from pydantic import BaseModel, ValidationError
from .exceptions import HTTPException
from .status import status
import inspect
from .utils import (
    resolve_annotation,
    bind_custom_class_form,
    bind_dataclass_form,
    bind_pydantic_form,
)
from .di import Depend
from .multi_part import FileMarker, FormMarker


class ResponseSerializer:
    """Serialize handler returns into Flask responses."""

    def serialize(
        self, result: Any, response_model: Any | None, flask_request: Request
    ) -> FlaskResponse:
        def serialize_item(item: Any) -> Any:
            rules: list[tuple[Callable[[Any], bool], Callable[[Any], Any]]] = [
                (lambda value: isinstance(value, tuple), lambda value: serialize_item(value[0])),
                (lambda value: isinstance(value, (str, bytes)), lambda value: value),
                (lambda value: hasattr(value, "model_dump"), lambda value: value.model_dump()),
                (lambda value: hasattr(value, "dict"), lambda value: value.dict()),
                (lambda value: hasattr(value, "dump"), lambda value: value.dump()),
                (
                    lambda value: hasattr(value, "to_dict")
                    and callable(getattr(value, "to_dict", None)),
                    lambda value: value.to_dict(),
                ),
                (
                    lambda value: dataclasses.is_dataclass(value) and not isinstance(value, type),
                    lambda value: dataclasses.asdict(value),
                ),
                (lambda value: isinstance(value, dict), lambda value: value),
            ]
            for predicate, transform in rules:
                if predicate(item):
                    return transform(item)
            raise TypeError(f"Cannot serialize object of type {type(item)}")

        # Already a Flask Response -> return as is
        if isinstance(result, FlaskResponse):
            res = _response_model(
                self, response_model, result, serialize_item, flask_request
            )
            return res

        # If response model exists, validate/shape output
        if response_model:
            res = _response_model(
                self, response_model, result, serialize_item, flask_request
            )
            return res

        # Fallback
        if isinstance(result, tuple):
            data = self.extract_data(result)
            status_code = self.extract_status_code(result)
            headers = self.extract_headers(result)
            response = make_response(jsonify(serialize_item(data)), status_code)
            if headers:
                response.headers.extend(headers)
            return response

        # Ensures str/bytes are wrapped
        if isinstance(result, (str, bytes)):
            return make_response(result)

        return make_response(jsonify(serialize_item(result)), 200)

    def extract_data(self, result: Any) -> Any:
        if not isinstance(result, tuple):
            return result
        if len(result) == 0:
            return None
        return result[0]

    def extract_status_code(self, result: Any, default: int = 200) -> int:
        if not isinstance(result, tuple):
            return default
        if len(result) >= 2 and isinstance(result[1], int):
            return result[1]
        if len(result) >= 2 and hasattr(result[1], "value"):
            value = getattr(result[1], "value", None)
            if isinstance(value, int):
                return value
        return default

    def extract_headers(self, result: Any) -> dict[str, str] | None:
        if not isinstance(result, tuple):
            return None
        if len(result) == 3 and isinstance(result[2], dict):
            return result[2]
        if len(result) == 2 and isinstance(result[1], dict):
            return result[1]
        return None


# todo : add File request
async def bind_route_parameters(
    func: Callable[..., Any],
    sig: inspect.Signature,
    type_hints: Any
) -> Dict[str, Any]:
    """Bind parameters for route handlers, handling dependencies and request body parsing."""
    try:
        bound_values = {}

        for name, param in sig.parameters.items():
            annotation = param.annotation
            default = param.default
            base_type, dependency = resolve_annotation(annotation, default=default)

            if isinstance(default, Depend) or isinstance(dependency, Depend):
                # Dependency injection is handled through resolve_dependencies.
                continue

            if isinstance(dependency, FileMarker):
                if request.content_type is None or not request.content_type.startswith(
                    "multipart/form-data"
                ):
                    raise HTTPException(
                        status_code=status.UNSUPPORTED_MEDIA_TYPE,
                        detail="The endpoint expects multipart form-data for file upload.",
                    )

                if dependency.multiple:
                    files = request.files.getlist(name)
                    if not files:
                        raise HTTPException(
                            status_code=status.UNPROCESSABLE_ENTITY,
                            detail=f"No files provided for '{name}'.",
                            title="File Upload Required",
                        )
                    bound_values[name] = files
                else:
                    file_obj = request.files.get(name)
                    if file_obj is None:
                        raise HTTPException(
                            status_code=status.UNPROCESSABLE_ENTITY,
                            detail=f"No file provided for '{name}'.",
                            title="File Upload Required",
                        )
                    bound_values[name] = file_obj
                continue

            if isinstance(dependency, FormMarker):
                if request.content_type is None or not any(
                    request.content_type.startswith(t)
                    for t in [
                        "multipart/form-data",
                        "application/x-www-form-urlencoded",
                    ]
                ):
                    raise HTTPException(
                        status_code=status.UNSUPPORTED_MEDIA_TYPE,
                        detail="The endpoint expects form data, but the request has an incorrect content type.",
                    )

                form_data = request.form.to_dict(flat=True)  # type: ignore
                if not form_data:
                    raise HTTPException(
                        status_code=status.UNPROCESSABLE_ENTITY,
                        detail="Empty form data. Ensure the request includes fields and uses the correct Content-Type.",
                        title="Empty Form Submission",
                    )

                form_type = dependency.type_ or base_type
                if (
                    form_type
                    and isinstance(form_type, type)
                    and issubclass(form_type, BaseModel)
                ):
                    try:
                        bound_values[name] = bind_pydantic_form(model_class=form_type)
                    except ValidationError as e:
                        raise HTTPException(
                            status_code=status.UNPROCESSABLE_ENTITY,
                            detail=e.errors(),
                            title="Form Validation Error",
                        )

                elif (
                    form_type
                    and isinstance(form_type, type)
                    and dataclasses.is_dataclass(form_type)
                ):
                    bound_values[name] = bind_dataclass_form(form_type)

                elif isinstance(form_type, type):
                    bound_values[name] = bind_custom_class_form(form_type)

                else:
                    bound_values[name] = form_data
                continue

            if (
                base_type
                and isinstance(base_type, type)
                and issubclass(base_type, BaseModel)
            ):
                if request.content_type and request.content_type.startswith(
                    "application/json"
                ):
                    try:
                        json_data = request.get_json(force=True)
                        bound_values[name] = base_type.model_validate(json_data)
                    except ValidationError as e:
                        raise HTTPException(
                            status_code=status.UNPROCESSABLE_ENTITY,
                            detail=e.errors(),
                            title="JSON Validation Error",
                        )
                else:
                    raise HTTPException(
                        status_code=status.UNSUPPORTED_MEDIA_TYPE,
                        detail="Expected JSON for this model, but received unsupported content type.",
                    )
                continue

            if dataclasses.is_dataclass(base_type) and isinstance(base_type, type):
                if request.content_type and request.content_type.startswith(
                    "application/json"
                ):
                    try:
                        json_data = request.get_json(force=True)
                        bound_values[name] = base_type(**json_data)  # type: ignore
                    except Exception as e:
                        raise HTTPException(
                            status_code=status.UNPROCESSABLE_ENTITY,
                            detail=f"Dataclass JSON binding failed: {e}",
                            title="Dataclass Binding Error",
                        )
                else:
                    raise HTTPException(
                        status_code=status.UNSUPPORTED_MEDIA_TYPE,
                        detail="Expected JSON for dataclass, but received unsupported content type.",
                    )
                continue

            if (
                isinstance(base_type, type)
                and hasattr(base_type, "to_dict")
                and base_type not in (str, int, float, bool, dict, list)
            ):
                if request.content_type and request.content_type.startswith(
                    "application/json"
                ):
                    try:
                        json_data = request.get_json(force=True)
                        bound_values[name] = base_type(**json_data)
                    except Exception as e:
                        raise HTTPException(
                            status_code=status.UNPROCESSABLE_ENTITY,
                            detail=f"Custom class JSON binding failed: {e}",
                            title="Custom Class Binding Error",
                        )
                else:
                    raise HTTPException(
                        status_code=status.UNSUPPORTED_MEDIA_TYPE,
                        detail="Expected JSON for custom class, but received unsupported content type.",
                    )
                continue

            if base_type in (int, str, float, bool, dict, list):
                value = None
                if request.view_args and name in request.view_args:
                    value = request.view_args.get(name)
                else:
                    json_data = request.get_json(silent=True) or {}
                    value = json_data.get(
                        name,
                        default if default is not inspect.Parameter.empty else None,
                    )

                try:
                    if value is not None and base_type is not None:
                        if base_type is bool:
                            value = str(value).lower() in ("true", "1", "yes", "on")  # type: ignore
                        else:
                            value = base_type(value)  # type: ignore
                except Exception:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Parameter '{name}' must be of type {base_type.__name__}",  # type: ignore
                    )
                bound_values[name] = value
                continue
            bound_values[name] = request

        return bound_values

    except HTTPException:
        raise


def _response_model(
    self: ResponseSerializer,
    response_model: Any,
    result: FlaskResponse | Any,
    serialize_item: Callable[[Any], Any],
    flask_request: Request,
):
    if not response_model:
        return result
    try:
        origin = get_origin(response_model)
        args = get_args(response_model)
        if origin is list and args:
            raw_data = self.extract_data(result)
            status_code = self.extract_status_code(result)
            data_list = list(raw_data) if not isinstance(raw_data, list) else raw_data
            return make_response(
                jsonify([serialize_item(item) for item in data_list]), status_code
            )
        if origin is tuple and args:
            raw_data = self.extract_data(result)
            status_code = self.extract_status_code(result)
            if isinstance(raw_data, tuple):
                data_tuple = raw_data
            else:
                if hasattr(raw_data, '__iter__') and not isinstance(raw_data, (str, bytes)):
                    data_tuple = tuple(raw_data)  # type: ignore
                else:
                    data_tuple = (raw_data,)
            return make_response(
                jsonify([serialize_item(item) for item in data_tuple]), status_code
            )

        if origin is None and isinstance(response_model, type):
            data = self.extract_data(result)
            status_code = self.extract_status_code(result)
            if isinstance(data, response_model):
                model_instance = data
            elif isinstance(data, BaseModel):
                model_instance = response_model(**data.model_dump())
            else:
                model_instance = response_model(**data)  # type: ignore
            return make_response(jsonify(serialize_item(model_instance)), status_code)

        return make_response(jsonify(result), 200)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.INTERNAL_SERVER_ERROR,
            detail="Response model validation failed: " + str(e),
            title="Response Validation Error",
            instance=flask_request.full_path,
        )
