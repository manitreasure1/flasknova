from flasknova.logger import get_flasknova_logger
from typing import get_type_hints
from flask import Flask
import dataclasses
import pydantic
import inspect
import re


def generate_openapi(
    app: Flask,
    title="FlaskNova API",
    version="1.0.0",
    security_schemes=None,
    global_security=None
):
    logger = get_flasknova_logger()
    paths = {}
    components = {"schemas": {}}

    def is_pydantic_model(annotation):
        try:
            return (
                annotation is not None and
                isinstance(annotation, type) and
                issubclass(annotation, pydantic.BaseModel)
            )
        except ImportError:
            return False

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
        sig = inspect.signature(view_func)
        type_hints = getattr(view_func, "__annotations__", {})

        methods = [m for m in (rule.methods or []) if m in {"GET", "POST", "PUT", "DELETE"}]

        # Extract path parameters from the rule
        path_params = []
        for match in re.finditer(r'<([^>]+)>', rule.rule):
            param = match.group(1)
            # Handle type e.g. <int:engineer_id>
            if ':' in param:
                param_type, param_name = param.split(':', 1)
            else:
                param_type, param_name = 'string', param
            path_params.append({
                "name": param_name,
                "in": "path",
                "required": True,
                "schema": {"type": "integer" if param_type == "int" else "string"}
            })

        for method in methods:
            if rule.rule not in paths:
                paths[rule.rule] = {}

            operation = {
                "tags": tags,
                "parameters": path_params.copy(),
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                                "schema": (
                                    {"$ref": f"#/components/schemas/{response_model.__name__}"}
                                    if response_model and hasattr(response_model, 'model_json_schema')
                                    else {"type": "object"}
                                )
                            }
                        }
                    }
                }
            }

            found_body = False
            for name, param in sig.parameters.items():
                annotation = type_hints.get(name, param.annotation)
                if found_body:
                    continue
                # --- Pydantic model ---
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
                # --- Dataclass ---
                elif is_dataclass_model(annotation):
                    try:
                        pdc_cls = pydantic.dataclasses.dataclass(annotation)
                        pyd_model = getattr(pdc_cls, '__pydantic_model__', None)
                        if pyd_model is None:
                            # fallback: try to create a model from fields
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
                # --- Custom class ---
                elif is_custom_class(annotation):
                    try:
                        
                        
                        hints = get_type_hints(annotation)
                        if not hints:
                            hints = getattr(annotation, '__annotations__', {})
                        fields = {}
                        for k, v in hints.items():
                            # Use ... for required fields, or the class attribute if present
                            if hasattr(annotation, k):
                                default = getattr(annotation, k)
                            else:
                                default = ...
                            fields[k] = (v, default)
                        if not fields:
                            logger.warning(f"Custom class {annotation} has no valid fields for schema.")
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
                            logger.warning(f"WARNING: Generated schema for {annotation} is empty: {schema}")
                    except Exception as e:
                        logger.error(f"Failed to create Pydantic model from custom class {annotation}: {e}")
                # Fallback: generic object schema if nothing else worked
            if not found_body:
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"}
                        }
                    }
                }
            # Add response model schema to components
            if response_model and hasattr(response_model, 'model_json_schema'):
                components["schemas"][response_model.__name__] = response_model.model_json_schema(ref_template="#/components/schemas/{model}")

            paths[rule.rule][method.lower()] = operation

    openapi = {
        "openapi": "3.0.0",
        "info": {
            "title": title,
            "version": version
        },
        "paths": paths
    }
    if components["schemas"]:
        openapi["components"] = components


    # --- Dynamic Security Schemes ---
    # If user provides security_schemes/global_security, use them; else default to BearerAuth
    if security_schemes is None and global_security is None:
        # Default: BearerAuth enabled
        security_schemes = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }
        global_security = [{"BearerAuth": []}]

    # Only add security schemes if explicitly provided or defaulted
    if security_schemes and global_security:
        if "components" not in openapi:
            openapi["components"] = {}
        openapi["components"].setdefault("securitySchemes", {})
        openapi["components"]["securitySchemes"].update(security_schemes)
        openapi["security"] = global_security

    return openapi
