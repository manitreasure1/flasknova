from pydantic import BaseModel, ValidationError, create_model
from typing import Type, get_args, get_origin, Annotated, Any, Union, Tuple
from .exceptions import HTTPException
from .di import Depend
from flask import request
from flask_nova.status import status
from .multi_part import FormMarker
import inspect


FLASK_ALLOWED_ROUTE_ARGS = {
                "methods", "endpoint", "defaults", "strict_slashes",
                "redirect_to", "alias", "host", "provide_automatic_options"
            }


ParamDefault = Union[Depend[Any], FormMarker, None, inspect._empty]
ParamItem = Tuple[str, ParamDefault]

def resolve_annotation(annotation, default=inspect.Parameter.empty)-> ParamItem:
    if annotation and get_origin(annotation) is Annotated:
        base_type, *extras = get_args(annotation)
        for extra in extras:
            if isinstance(extra, (Depend, FormMarker)):
                return base_type, extra
        return base_type, None

    if isinstance(default, (Depend, FormMarker)):
        return annotation, default

    return annotation, None


def _bind_pydantic_form(model_class: type[BaseModel])-> BaseModel:
    if request.content_type is None or not any(
        request.content_type.startswith(t)
        for t in ["multipart/form-data", "application/x-www-form-urlencoded"]
    ):
        raise HTTPException(
            status_code=status.UNSUPPORTED_MEDIA_TYPE,
            detail="The endpoint expects form data, but the request has an incorrect content type.",
        )
    form_data = request.form.to_dict()
    try:
        return model_class.model_validate(form_data)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.UNPROCESSABLE_ENTITY,
            detail=e.errors(),
            title="Form Validation Error"
        )

def _bind_dataclass_form(dataclass_class: Type[Any])->Any:
    TempModel = create_model(
        'DataclassFormWrapper',
        data=(dataclass_class, ...)
    )
    try:
        form_data = request.form.to_dict()
        validated_wrapper = TempModel(data=form_data)
        return getattr(validated_wrapper, "data")
    except Exception as e:
        raise HTTPException(
            status_code=status.UNPROCESSABLE_ENTITY,
            detail=f"Dataclass binding failed: {e}",
            title="Form Validation Error"
        )


def _bind_custom_class_form(custom_class: Type[Any])-> Any:
    try:
        form_data = request.form.to_dict()
        return custom_class(**form_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.UNPROCESSABLE_ENTITY,
            detail=f"Custom class binding failed: {e}",
            title="Form Validation Error"
        )


def filter_options(func, **options) -> dict[str, Any]:
    flask_options = {
                k: v for k, v in options.items() if k in FLASK_ALLOWED_ROUTE_ARGS
            }
    flask_options.pop("response_model", None)
    flask_options.pop("tags", None)
    if hasattr(func, "__dict__"):
        func.__dict__.pop("response_model", None)
        func.__dict__.pop("tags", None)

    return flask_options
