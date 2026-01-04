from ..logger import get_flasknova_logger
from typing import Any, get_type_hints, Dict
from flask import Flask
import dataclasses
import pydantic
import inspect
import re
from ..di import Depend
from ..types import FLASK_TO_OPENAPI_TYPES
from ..multi_part import FormMarker


def map_type_to_openapi(py_type: Any) -> Dict[str, Any]:
    if py_type in (int,):
        return {"type": "integer"}
    if py_type in (float,):
        return {"type": "number"}
    if py_type in (bool,):
        return {"type": "boolean"}
    if getattr(py_type, '__name__', '').lower() == 'uuid':
        return {"type": "string", "format": "uuid"}
    return {"type": "string"}


def generate_openapi(
    app: Flask,
    title: str,
    version: str| None,
    security_schemes=None,
    global_security=None
)-> Dict[str, Any]:

    logger = get_flasknova_logger()


    paths = {}
    components = {"schemas": {}}
    info = getattr(app, "_flasknova_openapi_info", None)



    def is_pydantic_model(annotation):
        return (
            annotation is not None and
            isinstance(annotation, type) and
            issubclass(annotation, pydantic.BaseModel)
        )

    def is_dataclass_model(annotation):
        return annotation is not None and isinstance(annotation, type) and dataclasses.is_dataclass(annotation)

    def is_custom_class(annotation):
        return (
            annotation is not None and
            isinstance(annotation, type) and
            hasattr(annotation, '__annotations__') and
            not is_pydantic_model(annotation) and
            not is_dataclass_model(annotation)
        )

    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'static':
            continue

        view_func = app.view_functions[rule.endpoint]
        tags = getattr(view_func, "_flasknova_tags", [])
        response_model = getattr(view_func, "_flasknova_response_model", None)
        summary = getattr(view_func, "_flasknova_summary", None)
        description = getattr(view_func, "_flasknova_description", None)



        doc = inspect.getdoc(view_func)
        doc_summary, doc_description = None, None



        if doc:
            lines = doc.strip().split('\n')
            doc_summary = lines[0]
            doc_description = '\n'.join(lines[1:]).strip() if len(lines) > 1 else None

        sig = inspect.signature(view_func)

        type_hints = getattr(view_func, "__annotations__", {})
        methods = [m for m in (rule.methods or []) if m in {"GET", "POST", "PUT", "DELETE", "PATCH"}]

        openapi_path = re.sub(r'<(?:[^:<>]+:)?([^<>]+)>', r'{\1}', rule.rule)


        path_params = []


        for match in re.finditer(r'<([^>]+)>', rule.rule):
            param = match.group(1)
            if ':' in param:
                param_type, param_name = param.split(':', 1)
            else:
                param_type, param_name = 'string', param

            openapi_type, openapi_format = FLASK_TO_OPENAPI_TYPES.get(param_type, ("string", None))
            schema = {"type": openapi_type}
            if openapi_format:
                schema["format"] = openapi_format

            path_params.append({
                "name": param_name,
                "in": "path",
                "required": True,
                "schema": schema
            })

        for method in methods:
            if openapi_path not in paths:
                paths[openapi_path] = {}

            operation = {
                "tags": tags,
                "summary": summary or doc_summary,
                "description": description or doc_description,
                "parameters": path_params.copy(),
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"}

                            }
                        }
                    }
                }
            }

            if response_model and hasattr(response_model, 'model_json_schema'):
                components["schemas"][response_model.__name__] = response_model.model_json_schema(ref_template="#/components/schemas/{model}")
                operation["responses"]["200"]["content"]["application/json"]["schema"] = {"$ref": f"#/components/schemas/{response_model.__name__}"}

            found_body = False
            for name, param in sig.parameters.items():
                if found_body:
                    break
                annotation = type_hints.get(name, param.annotation)

                default = param.default
                is_form = isinstance(default, FormMarker)


                if not is_form and (hasattr(default, "type_") or hasattr(default, "model")):
                    is_form = True

                if is_form:
                    model_cls = getattr(default, "type_", None) or getattr(default, "model", None)
                    form_props = {}

                    if model_cls and inspect.isclass(model_cls) and is_pydantic_model(model_cls):
                        try:
                            components[model_cls.__name__] = model_cls.model_json_schema(ref_template="#/components/schemas/{model}")
                        except Exception:
                            pass


                        fields = getattr(model_cls, "model_fields", None) or getattr(model_cls, "__fields__", None) or {}
                        for fn, finfo in fields.items():


                            f_ann = getattr(finfo, "annotation", None) or getattr(finfo, "type", None) or str
                            form_props[fn] = map_type_to_openapi(f_ann)
                    else:
                        form_props[name] = {"type": "string"}



                    operation["requestBody"] = {
                        "required": True,
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "properties": form_props}
                            }
                        },
                    }


                    found_body = True
                    continue

                if is_pydantic_model(annotation):
                    try:
                        schema = annotation.model_json_schema(ref_template="#/components/schemas/{model}")
                        components["schemas"][annotation.__name__] = schema
                        operation["requestBody"] = {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": f"#/components/schemas/{annotation.__name__}"}
                                }
                            }
                        }
                        found_body = True
                        continue
                    except Exception as e:
                        logger.error(f"Failed to generate schema for Pydantic model {annotation}: {e}")
                elif is_dataclass_model(annotation):
                    try:
                        pdc_cls = pydantic.dataclasses.dataclass(annotation)
                        pyd_model = getattr(pdc_cls, '__pydantic_model__', None)
                        if pyd_model is None:
                            fields = {}
                            for field in dataclasses.fields(annotation):
                                default = field.default if field.default is not dataclasses.MISSING else ...
                                fields[field.name] = (field.type, default)
                            pyd_model = pydantic.create_model(annotation.__name__, **fields)
                        schema = pyd_model.model_json_schema(ref_template="#/components/schemas/{model}")
                        if schema:
                            components["schemas"][pyd_model.__name__] = schema
                            operation["requestBody"] = {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": f"#/components/schemas/{pyd_model.__name__}"}
                                    }
                                }
                            }
                            found_body = True
                            continue
                        else:
                            logger.warning(f"Generated schema for dataclass {annotation} is empty: {schema}")
                    except Exception as e:
                        logger.error(f"Failed to convert dataclass {annotation} to Pydantic: {e}")
                elif is_custom_class(annotation):
                    try:
                        hints = get_type_hints(annotation)
                        if not hints:
                            hints = getattr(annotation, '__annotations__', {})
                        fields = {}
                        for k, v in hints.items():
                            if hasattr(annotation, k):
                                default = getattr(annotation, k)
                            else:
                                default = ...
                            fields[k] = (v, default)
                        if not fields and not isinstance(param.default, Depend):
                            logger.warning(f"Custom class {annotation} has no valid fields for schema.")
                        pyd_model = pydantic.create_model(annotation.__name__, **fields)
                        schema = pyd_model.model_json_schema(ref_template="#/components/schemas/{model}")
                        is_empty = not schema.get('properties')
                        if schema and not is_empty:

                            components["schemas"][pyd_model.__name__] = schema
                            operation["requestBody"] = {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": f"#/components/schemas/{pyd_model.__name__}"}
                                    }
                                }
                            }
                            found_body = True
                            continue
                        elif not isinstance(param.default, Depend):
                            logger.warning(f"WARNING: Generated schema for {annotation} is empty: {schema}")
                    except Exception as e:
                        logger.error(f"Failed to create Pydantic model from custom class {annotation}: {e}")

            paths[openapi_path][method.lower()] = operation


    if not isinstance(info, dict):
        info = {}
    openapi = {
        "openapi": "3.0.0",
        "info": {
            **info,
            "title": info.get("title", title),
            "version": info.get("version", version),
        },
        "paths": paths
    }


    if components["schemas"]:
        openapi["components"] = components

    if security_schemes:
        openapi.setdefault("components", {}).setdefault("securitySchemes", {})
        openapi["components"]["securitySchemes"].update(security_schemes)
    if global_security:
        openapi["security"] = global_security

    return openapi









