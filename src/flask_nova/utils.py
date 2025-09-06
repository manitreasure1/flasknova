
from pydantic import BaseModel, ValidationError, create_model
from typing import Type, get_args, get_origin, Annotated
from flask_nova.exceptions import HTTPException
from flask_nova.d_injection import Depend
from flask import request
from flask_nova.status import status
from flask_nova.multi_part import FormMarker
import inspect

def resolve_annotation(annotation, default=inspect.Parameter.empty):
    if annotation and get_origin(annotation) is Annotated:
        base_type, *extras = get_args(annotation)
        for extra in extras:
            if isinstance(extra, (Depend, FormMarker)):
                return base_type, extra
        return base_type, None

    if isinstance(default, (Depend, FormMarker)):
        return annotation, default

    return annotation, None




def extract_data(data):
    """Extract main data from tuple or return as is."""
    return data[0] if isinstance(data, tuple) else data

def extract_status_code(data, default=200):
    """Extract status code from tuple or enum, or return default."""
    if isinstance(data, tuple):
        possible_status = data[1] if len(data) > 1 else default
        if not isinstance(possible_status, int) and hasattr(possible_status, 'value') and isinstance(getattr(possible_status, 'value', None), int):
            return possible_status.value
        elif isinstance(possible_status, int):
            return possible_status
    return default





def _bind_pydantic_form(model_class: type[BaseModel]):
    if request.content_type is None or not any(
        request.content_type.startswith(t)
        for t in ["multipart/form-data", "application/x-www-form-urlencoded"]
    ):
        raise HTTPException(
            status_code=status.UNSUPPORTED_MEDIA_TYPE,
            detail="The endpoint expects form data, but the request has an incorrect content type.",
        )
    form_data = request.form.to_dict(flat=True) #type: ignore

    try:
        return model_class.model_validate(form_data)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.UNPROCESSABLE_ENTITY,
            detail=e.errors(),
            title="Form Validation Error"
        )


    



def _bind_dataclass_form(dataclass_class):
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
    


def _bind_custom_class_form(custom_class: Type):
    try:
        form_data = request.form.to_dict()
        return custom_class(**form_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.UNPROCESSABLE_ENTITY,
            detail=f"Custom class binding failed: {e}",
            title="Form Validation Error"
        )