from __future__ import annotations

from .helpers import __builder___

from flask.blueprints import Blueprint as _BluePrint
import typing as t
import warnings
import copy
import os


if t.TYPE_CHECKING:
    from flask.typing import RouteCallable
    from flask.sansio.scaffold import T_route
    from .typed import Method
    from enum import Enum


class NovaBlueprint(_BluePrint):
    def __init__(
        self,
        name: str,
        import_name: str = __name__,
        static_folder: str | os.PathLike[str] | None = None,
        static_url_path: str | None = None,
        template_folder: str | os.PathLike[str] | None = None,
        url_prefix: str | None = None,
        subdomain: str | None = None,
        url_defaults: dict[str, t.Any] | None = None,
        root_path: str | None = None,
        cli_group: str | None = None,
    ) -> None:

        self._compiled_validators: dict[str, t.Any] = {}
        self.openapi: dict[str, t.Any] = {}

        super().__init__(
            name,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_group,
        )

    def add_url_rule(
        self,
        rule: str,
        endpoint: str | None = None,
        view_func: RouteCallable | None = None,
        provide_automatic_options: bool | None = None,
        **options: t.Any,
    ) -> None:
        x_rule = copy.copy(rule)
        if self.url_prefix:
            x_rule = self.url_prefix + rule

        if view_func:
            __builder___(self, x_rule, view_func, options, True)

        return super().add_url_rule(
            rule, endpoint, view_func, provide_automatic_options, **options
        )

    def route(  # type: ignore
        self,
        rule: str,
        methods: list[Method] = ["GET"],
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        deprecated: bool = False,
        **options: t.Any,
    ) -> t.Callable[[T_route], T_route] | type:

        options["_route_meta"] = {
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

        options["_route_meta"] = {
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
    ) -> t.Callable[[T_route], T_route]:

        options["_route_meta"] = {
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

    def put(
        self,
        rule: str,  # type: ignore
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        deprecated: bool = False,
        **options: t.Any,
    ) -> t.Callable[[T_route], T_route] | type:

        options["_route_meta"] = {
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

    def patch(
        self,
        rule: str,  # type: ignore
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        deprecated: bool = False,
        **options: t.Any,
    ) -> t.Callable[[T_route], T_route] | type:

        options["_route_meta"] = {
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

    def delete(
        self,
        rule: str,  # type: ignore
        tags: list[t.Union[str, Enum]] | None = None,
        summary: str | None = None,
        description: str | None = None,
        servers: list[dict[str, str]] | None = None,
        responses: dict[str, t.Any] | None = None,
        response_model: type | None = None,
        deprecated: bool = False,
        **options: t.Any,
    ) -> t.Callable[[T_route], T_route] | type:

        options["_route_meta"] = {
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
    def options(self, *args, **kwargs) -> None: ...

    @warnings.deprecated(
        "The `head` decorator is deprecated and will be removed in FlaskNova 0.2.x."
        "\nIt no longer has any effect and can be safely removed",
    )
    def head(self, *args, **kwargs) -> None: ...
