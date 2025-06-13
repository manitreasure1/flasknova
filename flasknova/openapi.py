import inspect
from pydantic import BaseModel
from flask import Flask
from flasknova import get_flasknova_logger


log = get_flasknova_logger()


def generate_openapi(app: Flask, title="FlaskNova API", version="1.0.0"):
    paths = {}
    components = {"schemas": {}}

    def is_pydantic_model(annotation):
        return (
            annotation is not None and
            inspect.isclass(annotation) and
            issubclass(annotation, BaseModel)
        )

    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'static':
            continue

        view_func = app.view_functions[rule.endpoint]
        log.info(f"view function ----------------------------------{view_func}")
        tags = getattr(view_func, "_flasknova_tags", [])
        log.info(f"------------tags--------------->{tags}")
        response_model = getattr(view_func, "_flasknova_response_model", None)
        log.info(f"-------response models--------->{response_model}")
        sig = inspect.signature(view_func)
        type_hints = getattr(view_func, "__annotations__", {})
        log.info(f"type hints -----------{type_hints}")

        methods = [m for m in rule.methods if m in {"GET", "POST", "PUT", "DELETE"}]

        for method in methods:
            if rule.rule not in paths:
                paths[rule.rule] = {}

            operation = {
                "tags": tags,
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
                if is_pydantic_model(annotation) and not found_body:
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
    return openapi
