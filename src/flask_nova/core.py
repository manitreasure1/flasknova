from typing_extensions import Annotated, Doc
from .router import NovaBlueprint
from flask import Flask as _Flask, request, Response, jsonify
from . import types as nt
from enum import Enum
import typing as t
import os
from .docs.docs import create_docs_blueprint
from .exceptions import HTTPException

class FlaskNova(_Flask):
    """
    Main entry point for creating a FlaskNova application.

    #### Example:
    ```python
    from flask_nova import FlaskNova

    app = FlaskNova(__name__)
    ```
    """

    def __init__(
        self,
        *,
        import_name: Annotated[
            str,
            Doc(
                """
                The name of the application package or module.
                Typically use `__name__` so Flask can locate
                templates and static files relative to this module.
                """
            ),
        ],
        static_url_path: Annotated[
            str | None,
            Doc(
                """
                URL prefix for serving static files.
                Defaults to `'/static'` if `None`.
                """
            ),
        ] = None,
        static_folder: Annotated[
            str | os.PathLike[str] | None,
            Doc(
                """
                Filesystem path to the folder containing static files
                such as JavaScript, CSS, or images.
                Defaults to `'static'` in the application root.
                """
            ),
        ] = None,
        static_host: Annotated[
            str | None,
            Doc(
                """
                Optional host to serve static files from
                (for example, a CDN). `None` uses the app's own host.
                """
            ),
        ] = None,
        host_matching: Annotated[
            bool,
            Doc(
                """
                Enable matching the request host against the route’s
                `<host>` patterns.
                Set to `True` to use host-based routing.
                """
            ),
        ] = False,
        subdomain_matching: Annotated[
            bool,
            Doc(
                """
                Enable subdomain matching for routes.
                Useful for applications responding to
                multiple subdomains (e.g., `api.example.com`).
                """
            ),
        ] = False,
        template_folder: Annotated[
            str | os.PathLike[str] | None,
            Doc(
                """
                Directory containing Jinja2 templates.
                Defaults to `'templates'` in the application root.
                """
            ),
        ] = "templates",
        instance_path: Annotated[
            str | None,
            Doc(
                """
                Path to the instance folder for configuration
                or data not under version control.
                If omitted, Flask creates one automatically.
                """
            ),
        ] = None,
        instance_relative_config: Annotated[
            bool,
            Doc(
                """
                If `True`, file paths provided to `app.config.from_pyfile`
                are relative to the instance folder instead of the root path.
                """
            ),
        ] = False,
        root_path: Annotated[
            str | None,
            Doc(
                """
                The application root directory.
                Flask uses this to locate resources
                when not using the default.
                """
            ),
        ] = None,
        summary: Annotated[
            t.Optional[str],
            Doc(
                """
                A concise summary of your API.

                Example:
                    ```python
                    app = FlaskNova(__name__, summary="The Lite Nova")
                    ```
                """
            ),
        ] = None,
        description: Annotated[
            t.Optional[str],
            Doc(
                """
                A detailed description of the API (supports Markdown).

                Example:
                    ```python
                    app = FlaskNova(
                        __name__,
                        description=\"\"\"Find options within options.
                        **Nova — the new era**\"\"\"
                    )
                    ```
                """
            ),
        ] = None,
        version: Annotated[
            str,
            Doc(
                """
                The API version string.

                Example:
                    ```python
                    app = FlaskNova(__name__, version="0.0.1")
                    ```
                """
            ),
        ],
    ) -> None:
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
        self.register_error_handler(HTTPException, self._handle_http_exception)
        self.description = description
        self.version = version
        self.summary = summary
        self.nova_blueprints = NovaBlueprint("nova", import_name)

        swagger_enabled = self.config.get("FLASKNOVA_ENABLED_DOCS", True)
        if swagger_enabled:
            self._setup_docs()


    def _setup_docs(self):
        docs_path = self.config.get("FLASKNOVA_SWAGGER_ROUTE", "/docs")
        redoc_route = self.config.get("FLASKNOVA_REDOC_ROUTE", "/redoc")

        docs_bp = create_docs_blueprint(
            import_name=self.import_name,
            version=self.version,
            security_schemes="",
            global_security="",
            docs_route=docs_path,
            redoc_route=redoc_route
            )
        self.register_blueprint(docs_bp)


        @self.after_request
        def add_cache_headers(response: Response):
            if request.path.startswith(docs_path) or request.path.startswith(redoc_route):
                if response.mimetype in ['text/css', 'application/javascript']:
                    response.headers['Cache-Control'] = 'public, max-age=86400'
                else:
                    response.headers['Cache-Control'] = 'no-store'
            return response

    def _handle_http_exception(self, error: HTTPException):
        problem = {
            "type": error.type,
            "title": error.title,
            "status": error.status_code,
            "detail": error.detail,
            "instance": error.instance or request.full_path
        }
        return jsonify(problem), error.status_code



    def route(
        self,
        rule: Annotated[
            str,
            Doc(
                """
                URL path (rule) for the endpoint,
                such as `"/home"` or `"/api/items/<int:id>"`.
                """
            ),
        ],
        *,
        methods: Annotated[
            t.List[nt.Method],
            Doc(
                """
                HTTP methods supported by this route,
                e.g., `["GET", "POST"]`.
                """
            ),
        ],
        tags: Annotated[
            t.Optional[t.List[t.Union[str, Enum]]],
            Doc(
                """
                Optional list of tags (strings or Enums) to group or
                categorize this endpoint in API documentation.
                """
            ),
        ] = None,
        response_model: Annotated[
            t.Any | None,
            Doc(
                """
                Optional schema or Pydantic model describing the
                expected response body for documentation and validation.
                """
            ),
        ] = None,
        summary: Annotated[
            t.Optional[str],
            Doc("Short summary of the endpoint's purpose."),
        ] = None,
        description: Annotated[
            t.Optional[str],
            Doc("Detailed description of the endpoint (Markdown supported)."),
        ] = None,
        provide_automatic_options: bool | None = None,
        **options: t.Any,
    ) -> t.Callable[[nt.DecoratedCallable], nt.DecoratedCallable]:
        """
        Register a new route with the specified HTTP methods.

        Args:
            rule: URL path (e.g., `"/items"`).
            methods: HTTP methods allowed (e.g., ["GET", "POST"]).
            tags: Tags to group or categorize this endpoint in documentation.
            response_model: Optional schema/model for the response body.
            summary: Short, one-line endpoint summary.
            description: Longer Markdown-formatted endpoint description.
            provide_automatic_options: Whether to add an automatic OPTIONS handler.
            **options: Additional keyword arguments passed to `add_url_rule`.
        """
        return self.nova_blueprints.route(
            rule=rule,
            methods=methods,
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            provide_automatic_options=provide_automatic_options,
            options=options
        )



    def get(  # type: ignore[override]
        self,
        rule: Annotated[
            str,
            Doc('URL path (e.g., "/home") for the GET endpoint.'),
        ],
        *,
        tags: Annotated[
            t.Optional[t.List[t.Union[str, Enum]]],
            Doc("Optional list of tags for API documentation grouping."),
        ] = None,
        response_model: Annotated[
            t.Any | None,
            Doc("Optional schema/model describing the expected response body."),
        ] = None,
        summary: Annotated[
            str | None,
            Doc("Short summary of the GET endpoint's purpose."),
        ] = "",
        description: Annotated[
            str | None,
            Doc("Detailed description of the GET endpoint (Markdown supported)."),
        ] = "",
        **options: t.Any,
    ):
        """
        Decorator to register a **GET** endpoint.

        Args:
            rule: URL path (e.g., `"/items"`).
            tags: Tags to group this endpoint in API documentation.
            response_model: Schema/model for the expected response.
            summary: One-line summary of what this endpoint does.
            description: Markdown description of the endpoint.
            **options: Extra keyword arguments passed to `add_url_rule`.
        """
        return self.nova_blueprints._method_route(
            rule,
            method="GET",
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            **options,
        )

    def post( # type: ignore[override]
        self,
        rule: Annotated[str, Doc('URL path (e.g., "/home") for the POST endpoint.')],
        *,
        tags: Annotated[
            t.Optional[t.List[t.Union[str, Enum]]],
            Doc("Optional list of tags for API documentation grouping."),
        ] = None,
        response_model: Annotated[
            t.Any | None,
            Doc("Optional schema/model describing the expected response body."),
        ] = None,
        summary: Annotated[
            str | None,
            Doc("Short summary of the POST endpoint's purpose."),
        ] = "",
        description: Annotated[
            str | None,
            Doc("Detailed description of the POST endpoint (Markdown supported)."),
        ] = "",
        **options: t.Any,
    ):
        """
        Decorator to register a **POST** endpoint.

        Args:
            rule: URL path (e.g., `"/items"`).
            tags: Tags to group this endpoint in API documentation.
            response_model: Schema/model for the expected response.
            summary: One-line summary of what this endpoint does.
            description: Markdown description of the endpoint.
            **options: Extra keyword arguments passed to `add_url_rule`.
        """
        return self.nova_blueprints._method_route(
            rule,
            method="POST",
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            **options,
        )

    def put(  # type: ignore
        self,
        rule: Annotated[str, Doc('URL path (e.g., "/home") for the PUT endpoint.')],
        *,
        tags: Annotated[
            t.Optional[t.List[t.Union[str, Enum]]],
            Doc("Optional list of tags for API documentation grouping."),
        ] = None,
        response_model: Annotated[
            t.Any | None,
            Doc("Optional schema/model describing the expected response body."),
        ] = None,
        summary: Annotated[
            str | None,
            Doc("Short summary of the PUT endpoint's purpose."),
        ] = "",
        description: Annotated[
            str | None,
            Doc("Detailed description of the PUT endpoint (Markdown supported)."),
        ] = "",
        **options: t.Any,
    ):
        """
        Decorator to register a **PUT** endpoint.

        Args:
            rule: URL path (e.g., `"/items"`).
            tags: Tags to group this endpoint in API documentation.
            response_model: Schema/model for the expected response.
            summary: One-line summary of what this endpoint does.
            description: Markdown description of the endpoint.
            **options: Extra keyword arguments passed to `add_url_rule`.
        """
        return self.nova_blueprints._method_route(
            rule,
            method="PUT",
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            **options,
        )

    def delete(  # type: ignore
        self,
        rule: Annotated[str, Doc('URL path (e.g., "/home") for the DELETE endpoint.')],
        *,
        tags: Annotated[
            t.Optional[t.List[t.Union[str, Enum]]],
            Doc("Optional list of tags for API documentation grouping."),
        ] = None,
        response_model: Annotated[
            t.Any | None,
            Doc("Optional schema/model describing the expected response body."),
        ] = None,
        summary: Annotated[
            str | None,
            Doc("Short summary of the DELETE endpoint's purpose."),
        ] = "",
        description: Annotated[
            str | None,
            Doc("Detailed description of the DELETE endpoint (Markdown supported)."),
        ] = "",
        **options: t.Any,
    ):
        """
        Decorator to register a **DELETE** endpoint.

        Args:
            rule: URL path (e.g., `"/items"`).
            tags: Tags to group this endpoint in API documentation.
            response_model: Schema/model for the expected response.
            summary: One-line summary of what this endpoint does.
            description: Markdown description of the endpoint.
            **options: Extra keyword arguments passed to `add_url_rule`.
        """
        return self.nova_blueprints._method_route(
            rule,
            method="DELETE",
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            **options,
        )

    def patch(  # type: ignore
        self,
        rule: Annotated[str, Doc('URL path (e.g., "/home") for the PATCH endpoint.')],
        *,
        tags: Annotated[
            t.Optional[t.List[t.Union[str, Enum]]],
            Doc("Optional list of tags for API documentation grouping."),
        ] = None,
        response_model: Annotated[
            t.Any | None,
            Doc("Optional schema/model describing the expected response body."),
        ] = None,
        summary: Annotated[
            str | None,
            Doc("Short summary of the PATCH endpoint's purpose."),
        ] = "",
        description: Annotated[
            str | None,
            Doc("Detailed description of the PATCH endpoint (Markdown supported)."),
        ] = "",
        **options: t.Any,
    ):
        """
        Decorator to register a **PATCH** endpoint.

        Args:
            rule: URL path (e.g., `"/items"`).
            tags: Tags to group this endpoint in API documentation.
            response_model: Schema/model for the expected response.
            summary: One-line summary of what this endpoint does.
            description: Markdown description of the endpoint.
            **options: Extra keyword arguments passed to `add_url_rule`.
        """
        return self.nova_blueprints._method_route(
            rule,
            method="PATCH",
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            **options,
        )

    def head(
        self,
        rule: Annotated[str, Doc('URL path (e.g., "/home") for the HEAD endpoint.')],
        *,
        tags: Annotated[
            t.Optional[t.List[t.Union[str, Enum]]],
            Doc("Optional list of tags for API documentation grouping."),
        ] = None,
        response_model: Annotated[
            t.Any | None,
            Doc("Optional schema/model describing the expected response body."),
        ] = None,
        summary: Annotated[
            str | None,
            Doc("Short summary of the HEAD endpoint's purpose."),
        ] = "",
        description: Annotated[
            str | None,
            Doc("Detailed description of the HEAD endpoint (Markdown supported)."),
        ] = "",
        **options: t.Any,
    ):
        """
        Decorator to register a **HEAD** endpoint.

        Args:
            rule: URL path (e.g., `"/status"`).
            tags: Tags to group this endpoint in API documentation.
            response_model: Schema/model for the expected response.
            summary: One-line summary of what this endpoint does.
            description: Markdown description of the endpoint.
            **options: Extra keyword arguments passed to `add_url_rule`.
        """
        return self.nova_blueprints._method_route(
            rule,
            method="HEAD",
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            **options,
        )

    def options(
        self,
        rule: Annotated[str, Doc('URL path (e.g., "/home") for the OPTIONS endpoint.')],
        *,
        tags: Annotated[
            t.Optional[t.List[t.Union[str, Enum]]],
            Doc("Optional list of tags for API documentation grouping."),
        ] = None,
        response_model: Annotated[
            t.Any | None,
            Doc("Optional schema/model describing the expected response body."),
        ] = None,
        summary: Annotated[
            str | None,
            Doc("Short summary of the OPTIONS endpoint's purpose."),
        ] = "",
        description: Annotated[
            str | None,
            Doc("Detailed description of the OPTIONS endpoint (Markdown supported)."),
        ] = "",
        **options: t.Any,
    ):
        """
        Decorator to register an **OPTIONS** endpoint.

        Args:
            rule: URL path (e.g., `"/status"`).
            tags: Tags to group this endpoint in API documentation.
            response_model: Schema/model for the expected response.
            summary: One-line summary of what this endpoint does.
            description: Markdown description of the endpoint.
            **options: Extra keyword arguments passed to `add_url_rule`.
        """
        return self.nova_blueprints._method_route(
            rule,
            method="OPTIONS",
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            **options,
        )
