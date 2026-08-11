from __future__ import annotations

from .typed import FileMarker, FormMarker
from .di import Depend

from dataclasses import is_dataclass
from pydantic import BaseModel, TypeAdapter
from uuid import UUID
import inspect as ip
import typing as t
import re


class TypeChecker:
    def __init__(self, annotation, default: t.Any | None = None) -> None:
        self.annotation = annotation
        self.default = default

    def _is_dependency(self) -> bool:
        return isinstance(self.default, Depend)

    def _is_custom_class_form(self) -> bool:
        return self._is_custom_class() and self._is_form()

    def _is_dataclass_form(self) -> bool:
        return self._is_dataclass() and self._is_form()

    def _is_basemodel_form(self) -> bool:
        return self._is_form() and self._is_basemodel()

    def _is_basemodel(self) -> bool:
        return isinstance(self.annotation, type) and issubclass(
            self.annotation, BaseModel
        )

    def _is_custom_class(self) -> bool:
        return hasattr(self.annotation, "to_dict")

    def _is_dataclass(self) -> bool:
        return is_dataclass(self.annotation)

    def _is_file(self) -> bool:
        return isinstance(self.default, FileMarker)

    def _is_form(self) -> bool:
        return isinstance(self.default, FormMarker)


def _map_types(
    type_: type | t.Union[t.Any, t.Any],
) -> dict[str, dict[str, str] | list[dict[str, t.Any]]]:
    """map python types to openapi spec types"""
    map_type = {
        str: {"type": "string"},
        "string": {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        UUID: {"type": "string", "format": "uuid"},
        None: "null",
        list: {"type": "array"},
        set: {"type": "array"},
        dict: "object",
        t.Any: {},
    }
    if t.get_origin(type_) is t.Union:
        return {"anyOf": [_map_types(t) for t in t.get_args(type_)]}
    return map_type.get(type_, {})  # type: ignore[return-value]


def _gen_schema(type_: type | t.Any) -> dict[str, t.Any]:
    """this generates schema for custom classes with :attr:`to_dict`.

    raise TypeError when there is no :attr:`__annotations__`
    """
    if not hasattr(type_, "__annotations__"):
        raise TypeError(f"{type_.__name__} has no annotations")

    result: dict[str, t.Any] = {}
    properties: dict[str, t.Any] = {}
    description: str | None = ip.getdoc(type_)
    for field_name, field_type in type_.__annotations__.items():
        properties[field_name] = _map_types(field_type)

    result["type"] = "object"
    result["properties"] = properties
    result["title"] = type_.__name__
    if description:
        result["description"] = description
    return result


def type_builder(
    type_checker: TypeChecker,
) -> dict[str, str | t.Any | None] | dict[str, str | t.Any] | None:

    if type_checker._is_dependency():
        return {"type": "dependency", "default": type_checker.default}

    if type_checker._is_file():
        return {"type": "file", "default": type_checker.default}

    if type_checker._is_custom_class_form():
        return {
            "type": "customclassform",
            "object": type_checker.annotation,
            "default": type_checker.default,
        }

    if type_checker._is_dataclass_form():
        return {
            "type": "dataclassform",
            "object": type_checker.annotation,
            "default": type_checker.default,
        }

    if type_checker._is_basemodel_form():
        return {
            "type": "basemodelform",
            "object": type_checker.annotation,
            "default": type_checker.default,
        }
    if type_checker._is_basemodel():
        return {"type": "basemodel", "object": type_checker.annotation}

    if type_checker._is_dataclass():
        return {"type": "dataclass", "object": type_checker.annotation}

    if type_checker._is_custom_class():
        return {"type": "customclass", "object": type_checker.annotation}

    if type_checker._is_form():
        return {"type": "form", "default": type_checker.default}


def __openapi__(open_api_meta: dict[str, t.Any]) -> dict[str, t.Any]:

    route_spec: dict[str, t.Any] = {}

    for rule, meta_obj in open_api_meta.items():

        method = meta_obj.pop("methods", None)
        req = meta_obj.pop("request", None)
        res = meta_obj.pop("response", None)

        parameters: list[dict[str, t.Any]] = []
        request_body: dict[str, t.Any] = {}
        route_schemas: dict[str, t.Any] = {}

        if req:
            for param, obj in req.items():
                match obj["type"]:
                    case "query":
                        parameters.append(
                            {
                                "name": param,
                                "in": "query",
                                "required": True,
                                "style": "form",
                                "schema": _map_types(obj["object"]),
                                "uniqueItems": True,
                            }
                        )
                    case "path":
                        parameters.append(
                            {
                                "name": param,
                                "in": "path",
                                "required": True,
                                "style": "simple",
                                "schema": _map_types(obj["object"]),
                            }
                        )
                    case "basemodel":
                        properties = obj["object"].model_json_schema(
                            ref_template="#/components/schemas/{model}"
                        )
                        route_schemas[obj["object"].__name__] = properties
                        request_body["content"] = {
                            "application/json": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{obj["object"].__name__}"
                                }
                            }
                        }
                    case "dataclass":
                        properties = TypeAdapter(obj["object"]).json_schema(
                            ref_template="#/components/schemas/{model}"
                        )
                        route_schemas[obj["object"].__name__] = properties
                        request_body["content"] = {
                            "application/json": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{obj["object"].__name__}"
                                }
                            }
                        }
                    case "customclass":
                        properties = _gen_schema(obj["object"])
                        route_schemas[obj["object"].__name__] = properties
                        request_body["content"] = {
                            "application/json": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{obj["object"].__name__}"
                                }
                            }
                        }
                    case "basemodelform":
                        properties = obj["object"].model_json_schema(
                            ref_template="#/components/schemas/{model}"
                        )
                        route_schemas[obj["object"].__name__] = properties

                        request_body["content"] = {
                            "application/x-www-form-urlencoded": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{obj["object"].__name__}"
                                }
                            }
                        }
                    case "dataclassform":
                        properties = TypeAdapter(obj["object"]).json_schema(
                            ref_template="#/components/schemas/{model}"
                        )
                        route_schemas[obj["object"].__name__] = properties
                        request_body["content"] = {
                            "application/x-www-form-urlencoded": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{obj["object"].__name__}"
                                }
                            }
                        }
                    case "customclassform":
                        properties = _gen_schema(obj["object"])
                        route_schemas[obj["object"].__name__] = properties
                        request_body["content"] = {
                            "application/x-www-form-urlencoded": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{obj["object"].__name__}"
                                }
                            }
                        }
                    case "file":
                        request_body["content"] = {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                }
                            }
                        }
                    case "form":
                        request_body["content"] = {
                            "application/x-www-form-urlencoded": {
                                "schema": {
                                    "type": "object",
                                }
                            }
                        }
        if res:
            match res["type"]:
                case "basemodel":
                    properties = res["object"].model_json_schema(
                        ref_template="#/components/schemas/{model}"
                    )
                    route_schemas[res["object"].__name__] = properties
                case "dataclass":
                    properties = TypeAdapter(res["object"]).json_schema(
                        ref_template="#/components/schemas/{model}"
                    )
                    route_schemas[res["object"].__name__] = properties

                case "customclass":
                    properties = _gen_schema(res["object"])
                    route_schemas[res["object"].__name__] = properties
        if method:
            path_key: str = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", rule)
            route_spec["paths"] = {path_key: {}}
            route_spec["paths"][path_key][method.lower()] = {**meta_obj}

            if parameters:
                route_spec["paths"][path_key][method.lower()]["parameters"] = parameters
            if request_body:
                request_body["required"] = True
                route_spec["paths"][path_key][method.lower()][
                    "requestBody"
                ] = request_body
        if route_schemas:
            route_spec["components"] = route_schemas

    return route_spec
