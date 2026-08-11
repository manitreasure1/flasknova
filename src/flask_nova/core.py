from __future__ import annotations

from flask import Flask as _Flask, Request, Response, jsonify, request, g
from flask.globals import request_ctx
from flask.typing import HeadersValue
from werkzeug.datastructures import Headers

from .helpers import type_builder, TypeChecker, __openapi__
from .exceptions import HTTPException
from .docs import create_docs_blueprint
from .serializer import Serializer
from .logger import json_logger
from .binder import Binder
from .typed import Method

from enum import Enum
from uuid import UUID
import inspect as ip
import typing as t
import warnings
import logging
import secrets
import os
import re

if t.TYPE_CHECKING:
    from werkzeug.routing import Rule
    from flask.typing import RouteCallable, ResponseReturnValue
    from flask.sansio.scaffold import T_route


class FlaskNova(_Flask):
    def __init__(
        self,
        import_name: str = __name__,
        *,
        static_url_path: str | None = None,
        static_folder: str | os.PathLike[str] | None = "static",
        static_host: str | None = None,
        host_matching: bool = False,
        subdomain_matching: bool = False,
        template_folder: str | os.PathLike[str] | None = "templates",
        instance_path: str | None = None,
        instance_relative_config: bool = False,
        root_path: str | None = None,
        version: str | None = None,
        summary: str | None = None,
        description: str | None = None,
        contact: dict[str, str] | None = None,
        license: dict[str, str] | None = None,
        terms_of_service: str | None = None,
        external_docs: dict[str, str] | None = None,
    ) -> None:
        self._compiled_validators: dict[str, t.Any] = {}
        self.openapi: dict[str, t.Any] = {}

        super().__init__(
            import_name,
            static_url_path,
            static_folder,
            static_host,
            host_matching,
            subdomain_matching,
            template_folder,
            instance_path,
            instance_relative_config,
            root_path,
        )
        self.description = description
        self.version = version
        self.summary = summary
        self.contact = contact
        self.license = license
        self.terms_of_service = terms_of_service
        self.external_docs = external_docs

        # ? add
        # tags, externalDocs, servers, security

        self._binder = Binder
        self._serializer = Serializer
        self.__rule: str = ""  # let's call this SnoopShot

        @self.errorhandler(code_or_exception=HTTPException)
        def _http_exc(e: HTTPException) -> tuple[Response, int]:
            return self._to_rfc7807(e), e.status_code

        @self.before_request
        def _trace_request() -> None:
            incoming_trace: str | None = request.headers.get(key="traceparent")

            if incoming_trace and len(incoming_trace.split(sep="-")) == 4:
                parts: list[str] = incoming_trace.split(sep="-")
                trace_id: str = parts[1]
            else:
                trace_id = secrets.token_hex(nbytes=16)
            g.trace_id = trace_id

        self.register_blueprint(create_docs_blueprint(self))

    def add_url_rule(
        self,
        rule: str,
        endpoint: str | None = None,
        view_func: RouteCallable | None = None,
        provide_automatic_options: bool | None = None,
        **options: dict[str, t.Any],
    ) -> None:

        if view_func:
            schema_cache: dict[str, dict[str, t.Any]] = self._build_schema_cache(
                rule, view_func, options
            )
            self._compiled_validators[rule] = schema_cache

            operationId: str = view_func.__name__
            route_meta: dict[str, t.Any] | None = options.pop(rule, None)

            tags: list[str] | None = []
            servers: list[dict[str, str]] | None = []
            if route_meta:
                tags = route_meta.get("tags")
                servers = route_meta.get("servers")

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
            open_api_meta["operationId"] = operationId

            build: dict[str, t.Any] = {}
            info: dict[str, str | dict[str, str]] = {}

            if not rule.startswith(
                ("/docs", "/openapi", "/redoc", "/static", "swagger")
            ):
                build[rule] = open_api_meta
                route_spec = __openapi__(build)

                # todo: MOVE IN SEPARATE FUNCTION------------------/
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
                    self.openapi.setdefault("paths", {}).update(route_spec["paths"])
                    self.openapi.setdefault("components", {}).update(
                        route_spec["components"]
                    )
                if tags:
                    self.openapi.setdefault("tags", []).extend(tags)
                    self.openapi["tags"] = list(set(self.openapi["tags"]))
                if servers:
                    self.openapi.setdefault("servers", []).extend(servers)

        return super().add_url_rule(
            rule, endpoint, view_func, provide_automatic_options, **options
        )

    def _build_schema_cache(
        self,
        rule: str,
        view_func: RouteCallable,
        options: dict[str, t.Any],
    ) -> dict[str, dict[str, t.Any]]:
        build: dict[str, t.Any] = {}
        signature: ip.Signature = ip.signature(view_func)
        route_meta: dict | None = options.get(rule)
        return_type = t.get_type_hints(obj=view_func).get("return")

        build["request"] = self._request_signature(rule, signature)
        build["response"] = self._response_signature(route_meta, return_type)
        return build

    def _response_signature(
        self, route_meta: dict | None, return_type: t.Any
    ) -> dict[str, str | t.Any | None] | dict[str, str | t.Any] | None:
        response = None
        status = None
        headers = None
        # todo - add status and headers to route metadata
        if route_meta and route_meta.get("response_model"):
            response = route_meta.get("response_model")

        elif return_type:
            r_args: tuple[t.Any, ...] = t.get_args(tp=return_type)
            if t.get_origin(return_type) is tuple and r_args[0] not in (
                int,
                float,
                dict,
                str,
                Response,
            ):

                len_rt: int = len(r_args)
                if len_rt == 3:
                    response, status, headers = r_args
                elif len_rt == 2:
                    if not isinstance(r_args[1], (dict, tuple, list)):
                        response, status = r_args
                    else:
                        response, headers = r_args
            else:
                response = return_type

        typed_result = type_builder(TypeChecker(response))
        if typed_result:
            typed_result.update({"status": status, "headers": headers})
        return typed_result

    def _request_signature(
        self, rule: str, signature: ip.Signature
    ) -> dict[str, t.Any]:
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

            if name and type_ in (str, int, float, UUID):
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

    def dispatch_request(
        self,
    ) -> ResponseReturnValue:
        req: Request = request_ctx.request
        if req.routing_exception is not None:
            self.raise_routing_exception(request=req)

        rule: Rule = req.url_rule  # type: ignore
        if (
            getattr(rule, "provide_automatic_options", False)
            and req.method == "OPTIONS"
        ):
            return self.make_default_options_response()

        view_args: dict[str, t.Any] | None = {}
        binders = self._compiled_validators[rule.rule].get("request")
        if binders:
            for field_name, field_obj in binders.items():
                result = self._binder(field_name, field_obj, req).make_request()
                view_args[field_name] = result  # type: ignore[index]

        self.__rule = req.url_rule.rule  # type: ignore
        return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)  # type: ignore[arg-type]

    def make_response(self, rv: ResponseReturnValue | type) -> Response:
        """
        override :meth:`~Flask.make_response` to add  **native return type dispatcher**
        ```
        @app.get("/")
        def get_items(item_id: UUID) -> ItemResponse
            item = item_service(item_id)
            if not item: ...
            return item # item will be serialize with fields in `ItemResponse`
        ```
        _Note_: This does not override the `reponse_model` in the route decorator

        **versionadded**: 0.1.3
        """
        status: int | None = None
        headers: HeadersValue | None = None
        response_ = None

        serializer_obj = self._compiled_validators.get(self.__rule)

        if serializer_obj and rv:
            response_obj = serializer_obj.get("response")
            if isinstance(rv, type) and rv not in (int, float, str, Response):
                result = self._serializer(rv, response_obj).serialize()
                return jsonify(result)

            elif isinstance(rv, tuple):
                len_rv: int = len(rv)
                if len_rv == 3:
                    (
                        response_,
                        status,
                        headers,
                    ) = rv  # type: ignore
                elif len_rv == 2:
                    if not isinstance(rv[1], (Headers, dict, list, tuple)):
                        response_, status = rv  # type: ignore
                    else:
                        response_, headers = rv  # pyright: ignore[reportAssignmentType]

                result = self._serializer(response_, response_obj).serialize()
                r_o: Response = jsonify(result)
                if status:
                    r_o.status = status
                if headers:
                    r_o.headers.update(headers)
                return r_o
        return super().make_response(rv)  # type: ignore

    @property
    def logger(self) -> logging.Logger:
        if not self.config.get("ANSI_COLOR_JSON_LOG") == True:
            return super().logger
        return json_logger(self)

    def _to_rfc7807(self, e: HTTPException) -> Response:
        """Convert an `HTTPException` into an RFC 7807 JSON response.

        The response includes the standard problem-detail fields, application
        extensions, and tracing information for correlating the error with logs.
        """

        trace_id = g.trace_id
        span_id: str = secrets.token_hex(8)
        w3c_traceparent: str = f"00-{trace_id}-{span_id}-01"

        if self.debug:
            self.logger.error(e.title, exc_info=True)
        payload = {
            "type": e.type,
            "title": e.title,
            "status": e.status_code,
            "detail": e.detail,
            "instance": e.instance or request.path,
            "trace_id": trace_id,
        }
        extensions = e.extensions or {}
        payload |= extensions
        response: Response = jsonify(payload)
        response.content_type = "application/problem+json"
        response.headers["traceparent"] = w3c_traceparent
        return response

    def route(  # type: ignore
        self,
        rule: str,
        methods: list[Method],
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        deprecated: bool = False,
        **options: t.Any,
    ) -> t.Callable[[T_route], T_route] | type:
        """Register a route and attach Nova API metadata.

        Args:
            rule: URL pattern handled by the endpoint.
            methods: HTTP methods accepted by the route.
            tags: Groups used when generating API documentation.
            summary: Short endpoint description.
            description: Detailed endpoint description.
            servers: Server URLs associated with the endpoint.
            responses: Documented response definitions.
            response_model: Type used to describe the endpoint response.
            options: Additional Flask route options.

        Returns:
            A decorator that registers the endpoint with Flask.
        """
        options[rule] = {
            "methods": methods[0],
            "tags": tags,
            "summary": summary,
            "description": description,
            "servers": servers,
            "responses": responses,
            "response_model": response_model,
            "deprecated": deprecated,
        }
        return super().route(rule, methods=methods, **options)

    # todo: introduce `cache: bool` as metadata only in `GET`
    def get(  # type: ignore
        self,
        rule: str,
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        deprecated: bool = False,
        **options: t.Any,
    ) -> t.Callable[[T_route], T_route] | type:
        """Register a GET endpoint.

        The method-specific decorator currently forwards only Flask route options.
        The Nova metadata arguments are accepted for API compatibility but are not
        stored or used by the current implementation except `response_model`.
        ```
        @app.get(
            "/users",
            summary="List users",
            response_model=list[User],
            )
        ```
        """
        options[rule] = {
            "methods": "GET",
            "tags": tags,
            "summary": summary,
            "description": description,
            "servers": servers,
            "responses": responses,
            "response_model": response_model,
            "deprecated": deprecated,
        }
        return super().route(rule, methods=["GET"], **options)

    def post(  # type: ignore
        self,
        rule: str,
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        deprecated: bool = False,
        **options: t.Any,
    ) -> t.Callable[[T_route], T_route] | type:
        """Register a POST endpoint.

        The method-specific decorator currently forwards only Flask route options.
        The Nova metadata arguments are accepted for API compatibility but are not
        stored or used by the current implementation except `response_model`.
        ```
        @app.post(
            "/users",
            summary="List users",
            response_model=list[User],
            )
        ```
        """
        options[rule] = {
            "methods": "POST",
            "tags": tags,
            "summary": summary,
            "description": description,
            "servers": servers,
            "responses": responses,
            "response_model": response_model,
            "deprecated": deprecated,
        }
        return super().route(rule, methods=["POST"], **options)

    def put(  # type: ignore
        self,
        rule: str,
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        deprecated: bool = False,
        **options: t.Any,
    ) -> t.Callable[[T_route], T_route] | type:
        """Register a PUT endpoint.

        The method-specific decorator currently forwards only Flask route options.
        The Nova metadata arguments are accepted for API compatibility but are not
        stored or used by the current implementation except `response_model`.
        ```
        @app.put(
            "/users",
            summary="Update users",
            )
        ```
        """
        options[rule] = {
            "methods": "PUT",
            "tags": tags,
            "summary": summary,
            "description": description,
            "servers": servers,
            "responses": responses,
            "response_model": response_model,
            "deprecated": deprecated,
        }
        return super().route(rule, methods=["PUT"], **options)

    def patch(  # type: ignore
        self,
        rule: str,
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        deprecated: bool = False,
        **options: t.Any,
    ) -> t.Callable[[T_route], T_route] | type:
        """Register a PATCH endpoint.

        The method-specific decorator currently forwards only Flask route options.
        The Nova metadata arguments are accepted for API compatibility but are not
        stored or used by the current implementation except `response_model`.
        ```
        @app.patch(
            "/users",
            summary="Update user",
            )
        ```
        """
        options[rule] = {
            "methods": "PATCH",
            "tags": tags,
            "summary": summary,
            "description": description,
            "servers": servers,
            "responses": responses,
            "response_model": response_model,
            "deprecated": deprecated,
        }
        return super().route(rule, methods=["PATCH"], **options)

    def delete(  # type: ignore
        self,
        rule: str,
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        deprecated: bool = False,
        **options: t.Any,
    ) -> t.Callable[[T_route], T_route] | type:
        """Register a DELETE endpoint.

        The method-specific decorator currently forwards only Flask route options.
        The Nova metadata arguments are accepted for API compatibility but are not
        stored or used by the current implementation except `response_model`.
        ```
        @app.delete(
            "/users",
            summary="Logout user",
            )
        ```
        """
        options[rule] = {
            "methods": "DELETE",
            "tags": tags,
            "summary": summary,
            "description": description,
            "servers": servers,
            "responses": responses,
            "response_model": response_model,
            "deprecated": deprecated,
        }
        return super().route(rule, methods=["DELETE"], **options)

    @warnings.deprecated(
        "The `option` decorator is deprecated and will be removed in FlaskNova 0.2.x."
        "\nIt no longer has any effect and can be safely removed",
    )
    def options(self, *args, **kwargs): ...

    @warnings.deprecated(
        "The `head` decorator is deprecated and will be removed in FlaskNova 0.2.x."
        "\nIt no longer has any effect and can be safely removed",
    )
    def head(self, *args, **kwargs): ...
