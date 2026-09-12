from __future__ import annotations

from flask.globals import request_ctx, g, request
from flask.wrappers import Response, Request
from flask.typing import HeadersValue
from flask.app import Flask as _Flask
from flask.json import jsonify

from pydantic import BaseModel
from werkzeug.datastructures import Headers

from .helpers import __builder___, __builder_update__
from .docs import create_docs_blueprint
from .exceptions import HTTPException
from .serializer import Serializer
from .logger import json_logger
from .binder import Binder
from .typed import Method, deprecated

import collections.abc as cabc
from enum import Enum
import typing as t
import logging
import secrets
import sys
import os

if t.TYPE_CHECKING:
    from flask.typing import RouteCallable, ResponseReturnValue
    from flask.sansio.blueprints import Blueprint
    from flask.sansio.scaffold import T_route
    from werkzeug.routing import Rule


class FlaskNova(_Flask):
    _binder = Binder
    _serializer = Serializer
    _default_urls: dict[str, str] = {}

    def __init__(
        self,
        import_name: str | None = None,
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
        if not import_name:
            main = sys.modules.get("__main__")
            if main and getattr(main, "__file__", None):
                import_name = "__main__"
            else:
                import_name = __name__

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
        # ? add security

        self._rule: str = ""  # let's call this SnoopShot
        self._method: str = ""

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

        if self.config.get("FLASKNOVA_ENABLE_DOCS", True):
            self.register_blueprint(create_docs_blueprint(self))

    def add_url_rule(
        self,
        rule: str,
        endpoint: str | None = None,
        view_func: RouteCallable | None = None,
        provide_automatic_options: bool | None = None,
        **options: dict[str, t.Any],
    ) -> None:
        self._default_urls.update(
            {
                "swagger_route": self.config.get("FLASKNOVA_SWAGGWER_ROUTE", "/docs"),
                "redoc_route": self.config.get("FLASKNOVA_REDOC_ROUTE", "/redoc"),
                "scalar_route": self.config.get("FLASKNOVA_SCALAR_ROUTE", "/scalar"),
            }
        )
        if view_func:
            __builder___(self, rule, view_func, options)

        if self.blueprints:
            __builder_update__(self)

        return super().add_url_rule(
            rule, endpoint, view_func, provide_automatic_options, **options
        )

    def register_blueprint(self, blueprint: Blueprint, **options: t.Any) -> None:
        if options.get("url_prefix"):
            self.logger.warning(
                "set `url_prefix` at the class level `NovaBlueprint(..., url_prefix=..,)` to avoid url mismatch!"
            )
        return super().register_blueprint(blueprint, **options)

    def dispatch_request(
        self,
    ) -> ResponseReturnValue:
        req: Request = request_ctx.request
        if req.routing_exception is not None:
            self.raise_routing_exception(request=req)

        method = req.method
        rule: Rule = req.url_rule  # type: ignore
        if (
            getattr(rule, "provide_automatic_options", False)
            and req.method == "OPTIONS"
        ):
            return self.make_default_options_response()

        view_args: dict[str, t.Any] | None = {}

        _method_graph: dict[str, dict[str, t.Any]] | None = (
            self._compiled_validators.get(
                method,
            )
        )
        binders = (
            _method_graph[rule.rule].get("request")
            if _method_graph and _method_graph.get(rule.rule)
            else None
        )
        if binders:
            for field_name, field_obj in binders.items():
                result = self._binder(field_name, field_obj, req).make_request()
                view_args[field_name] = result  # type: ignore[index]
        self._method = method
        self._rule = req.url_rule.rule  # type: ignore
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

        **versionadded**: 0.2.0
        """

        status: int | None = None
        headers: HeadersValue | None = None
        response_ = None
        _method_graph: dict[str, dict[str, t.Any]] = self._compiled_validators.get(
            self._method, {}
        )
        serializer_obj = _method_graph.get(self._rule)
        self._method = ""
        if (
            (
                not isinstance(rv, (str, bytes, bytearray))
                or isinstance(rv, cabc.Iterator)
            )
            and serializer_obj
            and rv
            and not isinstance(rv, Response)
            and serializer_obj.get("response")
            and serializer_obj["response"].get("type")
            and serializer_obj["response"]["type"] != "any"
        ):
            result = None
            response_obj = serializer_obj["response"]
            if hasattr(rv, "__annotations__"):
                result = self._serializer(rv, response_obj).serialize(True)
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
                result = self._serializer(response_, response_obj).serialize(True)
            elif isinstance(rv, dict):
                result = self._serializer(rv, response_obj).serialize()

            if not result:
                raise TypeError(
                    f"The view function for {request.endpoint!r} did not"
                    " return a valid response. The function either returned"
                    " None or ended without a return statement."
                )
            res = jsonify(result)
            if status:
                res.status = status
            if headers:
                res.headers.update(headers)
            return res
        return super().make_response(rv)  # pyright: ignore[reportArgumentType]

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
        *,
        methods: list[Method] = ["GET"],
        status_code: int | None = None,
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        additionalOperations: dict[str, t.Any] | None = None,
        externalDocs: dict[str, t.Any] | None = None,
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
            additionalOperations: other information about the route
            externalDocs: external documentation for this operation
            deprecated: mark the endpoint as deprecated
            options: Additional Flask route options.

        Returns:
            A decorator that registers the endpoint with Flask.
        """
        options["_route_meta"] = {
            "methods": methods[0],
            "status_code": status_code,
            "tags": tags,
            "summary": summary,
            "description": description,
            "servers": servers,
            "responses": responses,
            "response_model": response_model,
            "additionalOperations": additionalOperations,
            "externalDocs": externalDocs,
            "deprecated": deprecated,
        }
        return super().route(rule, methods=methods, **options)

    # todo: introduce `cache: bool` as metadata only in `GET`
    def get(  # type: ignore
        self,
        rule: str,
        *,
        status_code: int | None = None,
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        additionalOperations: dict[str, t.Any] | None = None,
        externalDocs: dict[str, t.Any] | None = None,
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
        options["_route_meta"] = {
            "methods": "GET",
            "status_code": status_code,
            "tags": tags,
            "summary": summary,
            "description": description,
            "servers": servers,
            "responses": responses,
            "response_model": response_model,
            "additionalOperations": additionalOperations,
            "externalDocs": externalDocs,
            "deprecated": deprecated,
        }
        return super().route(rule, methods=["GET"], **options)

    def post(  # type: ignore
        self,
        rule: str,
        *,
        status_code: int | None = None,
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        additionalOperations: dict[str, t.Any] | None = None,
        externalDocs: dict[str, t.Any] | None = None,
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
        options["_route_meta"] = {
            "methods": "POST",
            "status_code": status_code,
            "tags": tags,
            "summary": summary,
            "description": description,
            "servers": servers,
            "responses": responses,
            "response_model": response_model,
            "additionalOperations": additionalOperations,
            "externalDocs": externalDocs,
            "deprecated": deprecated,
        }
        return super().route(rule, methods=["POST"], **options)

    def put(  # type: ignore
        self,
        rule: str,
        *,
        status_code: int | None = None,
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        additionalOperations: dict[str, t.Any] | None = None,
        externalDocs: dict[str, t.Any] | None = None,
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
        options["_route_meta"] = {
            "methods": "PUT",
            "status_code": status_code,
            "tags": tags,
            "summary": summary,
            "description": description,
            "servers": servers,
            "responses": responses,
            "response_model": response_model,
            "additionalOperations": additionalOperations,
            "externalDocs": externalDocs,
            "deprecated": deprecated,
        }
        return super().route(rule, methods=["PUT"], **options)

    def patch(  # type: ignore
        self,
        rule: str,
        *,
        status_code: int | None = None,
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        additionalOperations: dict[str, t.Any] | None = None,
        externalDocs: dict[str, t.Any] | None = None,
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
        options["_route_meta"] = {
            "methods": "PATCH",
            "status_code": status_code,
            "tags": tags,
            "summary": summary,
            "description": description,
            "servers": servers,
            "responses": responses,
            "response_model": response_model,
            "additionalOperations": additionalOperations,
            "externalDocs": externalDocs,
            "deprecated": deprecated,
        }
        return super().route(rule, methods=["PATCH"], **options)

    def delete(  # type: ignore
        self,
        rule: str,
        *,
        status_code: int | None = None,
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        additionalOperations: dict[str, t.Any] | None = None,
        externalDocs: dict[str, t.Any] | None = None,
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
        options["_route_meta"] = {
            "methods": "DELETE",
            "status_code": status_code,
            "tags": tags,
            "summary": summary,
            "description": description,
            "servers": servers,
            "responses": responses,
            "response_model": response_model,
            "additionalOperations": additionalOperations,
            "externalDocs": externalDocs,
            "deprecated": deprecated,
        }
        return super().route(rule, methods=["DELETE"], **options)

    @deprecated(
        "The `option` decorator is deprecated and will be removed in FlaskNova 0.2.x."
        "\nIt no longer has any effect and can be safely removed",
    )
    def options(self, *args, **kwargs): ...

    @deprecated(
        "The `head` decorator is deprecated and will be removed in FlaskNova 0.2.x."
        "\nIt no longer has any effect and can be safely removed",
    )
    def head(self, *args, **kwargs): ...
