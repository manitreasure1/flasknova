from __future__ import annotations

from .typed import FileMarker, FormMarker
from .di import Depend

from pydantic import BaseModel, TypeAdapter
from flask.wrappers import Response

from dataclasses import is_dataclass
from uuid import UUID
import inspect as ip
import typing as t
import re

if t.TYPE_CHECKING:
    from flask.typing import RouteCallable


# region Openapi
class TypeChecker:
    """detect annotation
    - dependency
    - form
        - custom class form
        - dataclass form
        - basemodel form
    - custom class
    - dataclass
    - basemodel
    - file
    """

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
) -> dict[str, str | t.Any | None] | dict[str, str | t.Any] | None:  # type: ignore
    """
    check annotation type using :cls:`TypeChecker`
    and return a dict object containing info about the annotation type
    ```
    {
        "type": "customclassform",
        "object": <User>,
        "default": <Form>,
    }
    ```
    """

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
        return {
            "type": "form",
            "object": type_checker.annotation,
            "default": type_checker.default,
        }
    return None


def __openapi__(open_api_meta: dict[str, t.Any]) -> dict[str, t.Any]:

    route_spec: dict[str, t.Any] = {}
    for rule, meta_obj in open_api_meta.items():
        method: str | None = meta_obj.pop("methods", None)
        req: dict[str, t.Any] | None = meta_obj.pop("request", None)
        res: dict[str, t.Any] | None = meta_obj.pop("response", None)

        responses: dict[str, dict[t.Any, t.Any]] | None = meta_obj.get("responses")

        parameters: list[dict[str, t.Any]] = []
        request_body: dict[str, t.Any] = {}
        route_schemas: dict[str, t.Any] = {}
        properties: dict[str, dict[str, str] | str] = {}

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
                                    "$ref": f"#/components/schemas/{obj['object'].__name__}"
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
                                    "$ref": f"#/components/schemas/{obj['object'].__name__}"
                                }
                            }
                        }
                    case "customclass":
                        properties = _gen_schema(obj["object"])
                        route_schemas[obj["object"].__name__] = properties
                        request_body["content"] = {
                            "application/json": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{obj['object'].__name__}"
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
                                    "$ref": f"#/components/schemas/{obj['object'].__name__}"
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
                                    "$ref": f"#/components/schemas/{obj['object'].__name__}"
                                }
                            }
                        }
                    case "customclassform":
                        properties = _gen_schema(obj["object"])
                        route_schemas[obj["object"].__name__] = properties
                        request_body["content"] = {
                            "application/x-www-form-urlencoded": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{obj['object'].__name__}"
                                }
                            }
                        }
                    case "file":
                        name: str = obj["default"].name or param
                        description: str | None = obj["default"].description

                        properties = {
                            name: {"type": "string", "format": "binary"},
                        }
                        if description:
                            properties["description"] = description

                        request_body["content"] = {
                            "multipart/form-data": {
                                "schema": {"type": "object", "properties": properties},
                            }
                        }

                    case "form":
                        request_body["content"] = {
                            "application/x-www-form-urlencoded": {
                                "schema": {
                                    "type": "object",
                                    "properties": {param: _map_types(obj["object"])},
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

            if res.get("status"):
                res__: dict[str, t.Any] = {}
                status_code = (
                    str(res["status"]) if isinstance(res["status"], int) else "200"
                )
                res__[status_code] = {}

                if res["type"] in ("customclass", "dataclass", "basemodel"):
                    res__[status_code]["application/json"] = {
                        "schema": {
                            "$ref": f"#/components/schemas/{res['object'].__name__}"
                        }
                    }
                if responses and not responses.get(status_code):
                    meta_obj["responses"].update(res__)
                else:
                    meta_obj["responses"] = res__

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
            route_spec["components"] = {}
            route_spec["components"]["schemas"] = route_schemas
    return route_spec


# region Validator Builder


def _request_signature(rule: str, signature: ip.Signature) -> dict[str, t.Any]:
    """Request Meta builder"""

    build: dict[str, t.Any] = {}
    paths: list[str] = []
    get_paths: list[str] = re.findall(pattern=r"<([^>]+)>", string=rule)

    for path in get_paths:
        if ":" in path:
            paths.append(path.split(sep=":")[1])
        else:
            paths.append(path)

    for name, param in signature.parameters.items():
        annotation = param.annotation
        default = param.default
        if t.get_origin(annotation) is t.Annotated:
            type_, *default_ = t.get_args(annotation)  # type: ignore[assignment]
        else:
            type_ = annotation if annotation is not ip._empty else None
            default_ = default if default is not ip._empty else None  # type: ignore[assignment]
        default_ = default_[0] if isinstance(default_, list) else default_

        if name and type_ in (str, int, float, UUID) and not default_:
            if name in paths:
                pq = {"type": "path", "object": type_}
            else:
                pq = {"type": "query", "object": type_}
            build[name] = pq
        elif name and not type_ and not default_:
            build[name] = {"type": "query", "object": str}
        else:
            build[name] = type_builder(
                type_checker=TypeChecker(annotation=type_, default=default_)
            )
    return build


def _response_signature(
    response_model: type | None, return_type: t.Any
) -> dict[str, str | t.Any | None] | dict[str, str | t.Any] | None:
    """Response Meta builder"""
    response = None
    status = None
    headers = None

    if response_model:
        response = response_model
    elif return_type:
        r_args: tuple[t.Any, ...] = t.get_args(return_type)
        len_rt: int = len(r_args)

        if t.get_origin(return_type) is tuple and r_args[0] not in (
            int,
            float,
            str,
            Response,
        ):
            if len_rt == 3:
                response, status, headers = r_args
            elif len_rt == 2:
                if not isinstance(r_args[1], (dict, tuple, list)):
                    response, status = r_args
                    if t.get_origin(r_args[1]) is t.Literal:
                        status = r_args[1].__args__[0]
                else:
                    response, headers = r_args
        else:
            response = return_type

    typed_result: dict[str, t.Any] | None = None
    if isinstance(response, tuple) or t.get_origin(response) is tuple:
        typed_result = {"type": response}
        if status:
            typed_result["status"] = status
        if headers:
            typed_result["headers"] = headers
    else:
        typed_result = type_builder(TypeChecker(response))
        if typed_result:
            typed_result.update({"status": status, "headers": headers})
        else:
            typed_result = {"type": "any", "status": status, "headers": headers}
    return typed_result


def _build_schema_cache(

    rule: str, view_func: RouteCallable, route_meta: dict[str, t.Any] | None
) -> dict[str, dict[str, t.Any]]:
    """
    Update :func:`_request_signature` and :func:`_response_signature` to a compiled obj

    versionadded 0.2.0
    """

    build: dict[str, t.Any] = {}
    response_model: type | None = None
    signature: ip.Signature = ip.signature(view_func)
    return_type = t.get_type_hints(obj=view_func).get("return")

    if route_meta:
        response_model = route_meta.get("response_model")

    build["request"] = _request_signature(rule, signature)
    build["response"] = _response_signature(response_model, return_type)
    return build


def __builder___(
    self,
    rule: str,
    view_func: RouteCallable,
    options: dict[str, t.Any],
    is_blueprint: bool = False,
) -> None:
    """generate :cls:`FlaskNova` and NovaBlueprint :attr:`_compiled_validators` and :attr:`openapi` schema

    Args:
        rule: the current url passing trough `add_url_rule`
        view_func: the corresponding func associated with the rule
        options: extra info provide by add_url_rule
        is_blueprint: check if add_url_rule it has certain attr

    versionadded 0.2.0
    """

    schema_cache: dict[str, dict[str, t.Any]] = {}
    rule_graph: dict[str, dict[str, t.Any]] = {}

    route_meta: dict[str, t.Any] | None = options.pop("_route_meta", None)
    _static_url_path = self.static_url_path if self.static_url_path else "static"

    method = route_meta["methods"] if route_meta else None
    tags = route_meta.get("tags") if route_meta else []
    servers = route_meta.get("servers") if route_meta else []

    schema_cache = _build_schema_cache(rule, view_func, route_meta)

    if not _static_url_path in rule:
        rule_graph[rule] = schema_cache

    if route_meta:
        self._compiled_validators.setdefault(method, {}).update(rule_graph)

        for name, value in route_meta.items():
            if not value:
                route_meta.pop(name)
            route_meta = {**route_meta}
        route_meta.pop("response_model", None)

        open_api_meta: dict[str, t.Any | dict[str, t.Any]] = {
            **route_meta,
            **schema_cache,
        }
    else:
        open_api_meta = schema_cache
    open_api_meta["operationId"] = view_func.__name__

    build_openapi_meta: dict[str, t.Any] = {}
    info: dict[str, str | dict[str, str]] = {}

    docs_url = ["/docs", "/openapi", "/redoc", "/swagger", _static_url_path]
    if not is_blueprint:
        swagger_url = self.config.get("FLASKNOVA_SWAGGWER_ROUTE", None)
        redoc_url = self.config.get("FLASKNOVA_REDOC_ROUTE", None)
        scalar_url = self.config.get("FLASKNOVA_SCALAR_ROUTE", None)

        if swagger_url:
            docs_url.append(swagger_url)
        if redoc_url:
            docs_url.append(redoc_url)
        if scalar_url:
            docs_url.append(scalar_url)

    if not rule.startswith(tuple(docs_url)):
        build_openapi_meta[rule] = open_api_meta
        route_spec = __openapi__(build_openapi_meta)

        if not is_blueprint:
            self.openapi["openapi"] = "3.2.0"
            if self.external_docs:
                self.openapi["externalDocs"] = self.external_docs
            if self.summary:
                info["summary"] = self.summary
            if self.version:
                info["version"] = self.version
            if self.description:
                info["description"] = self.description
            if self.contact:
                info["contact"] = self.contact
            if self.license:
                info["license"] = self.license
            if self.terms_of_service:
                info["termsOfService"] = self.terms_of_service
            self.openapi["info"] = info

        if route_spec:
            if (
                self.openapi.get("paths")
                and self.openapi["paths"].get(rule)
                and route_spec.get("paths")
            ):
                self.openapi["paths"][rule].update(route_spec["paths"][rule])

            elif route_spec.get("paths"):
                self.openapi.setdefault("paths", {}).update(route_spec["paths"])

            if route_spec.get("components"):

                self.openapi.setdefault("components", {"schemas": {}})

                self.openapi["components"]["schemas"].update(
                    route_spec["components"]["schemas"]
                )
        if tags:
            self.openapi.setdefault("tags", []).extend(tags)
            self.openapi["tags"] = list(set(self.openapi["tags"]))
        if servers:
            self.openapi.setdefault("servers", []).extend(servers)


def __builder_update__(self) -> None:
    """Update existing object generated by :func:`__builder___`, targeting bluprints`

    versionadded 0.2.0
    """

    for _, blueprint in self.blueprints.items():
        if hasattr(blueprint, "_compiled_validators"):
            _compiled_validators = getattr(blueprint, "_compiled_validators")
            openapi = getattr(blueprint, "openapi")
            for method, method_obj in _compiled_validators.items():

                if method in self._compiled_validators.keys():
                    self._compiled_validators[method].update(method_obj)
                else:
                    self._compiled_validators.setdefault(method, {}).update(method_obj)

            if self.openapi.get("paths") and openapi.get("paths"):
                self.openapi["paths"].update(openapi["paths"])
            elif openapi.get("paths"):
                self.openapi["paths"] = openapi["paths"]

            if (
                self.openapi.get("components")
                and openapi.get("components")
                and self.openapi["components"].get("schemas")
                and openapi["components"].get("schemas")
            ):
                self.openapi["components"]["schemas"].update(
                    openapi["components"]["schemas"]
                )
            elif openapi.get("components") and openapi.get("components").get("schemas"):
                self.openapi["components"]["schemas"] = openapi["components"]["schemas"]

            if self.openapi.get("tags") and openapi.get("tags"):
                self.openapi["tags"].extend(openapi["tags"])
                self.openapi["tags"] = list(set(self.openapi["tags"]))
            elif openapi.get("tags"):
                self.openapi["tags"] = openapi["tags"]

            if self.openapi.get("servers") and openapi.get("servers"):
                self.openapi["servers"].extend(openapi["servers"])
            elif openapi.get("servers"):
                self.openapi["servers"] = openapi["servers"]
