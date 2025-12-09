from flask.sansio.scaffold import setupmethod
from typing_extensions import Annotated, Doc
from flask import Blueprint as _Blueprint
from . import types as nt
from enum import Enum
import typing as t
import os
from .responses import ResponseSerializer
from .route_refactor import RouteFactory

class NovaBlueprint(_Blueprint):
    """
    #### Example:
    ```python
    from flask_nova import FlaskNova

    app = NovaBluePrint("sub")
    ```
    """

    def __init__(
        self,
        name: Annotated[
            str,
            Doc(
                """
                """
            ),
        ],
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
         *,
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
        template_folder: Annotated[
            str | os.PathLike[str] | None,
            Doc(
                """
                Directory containing Jinja2 templates.
                Defaults to `'templates'` in the application root.
                """
            ),
        ] = "templates",
        url_prefix: Annotated[
            str | None,
            Doc(
                """
                """
            ),
        ] = None,
        subdomain: Annotated[
            str | None,
            Doc(
                """
                """
            ),
        ] = None,
        url_defaults: Annotated[
            dict[str, t.Any] | None,
            Doc(
                """
                """
            ),
        ] = None,
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
        **kwargs
    ):

        super().__init__(
            name,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            static_host,
            root_path,
        )
        self._serializer = ResponseSerializer()
        self.route_factory = RouteFactory(self._serializer)

    def _method_route( # type: ignore[override]
        self,
        rule: str,
        method: nt.Method,
        *,
        tags: t.Optional[t.List[t.Union[str, Enum]]] = None,
        response_model: t.Any | None = None,
        summary: str | None = "",
        description: str | None = "",
        **options: t.Any,
    ) -> t.Callable[[nt.RouteHandler], nt.RouteHandler]:
        if "methods" in options:
            raise TypeError("Use the 'route' decorator to use the 'methods' argument.")
        for key in ("tags", "response_model", "summary", "description"):
            if key in options:
                raise TypeError(f"Use the 'route' decorator to set '{key}'.")

        return self.route(
            rule,
            methods=[method],
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            **options,
        )

    @setupmethod
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

        return self.route_factory.build(
            owner=self,
            rule=rule,
            methods=methods,
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            provide_automatic_options=provide_automatic_options,
            options=options,
        )



    @setupmethod
    def get( # type: ignore[override]
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
        return self._method_route(
            rule,
            method="GET",
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            **options,
        )

    @setupmethod
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
        return self._method_route(
            rule,
            method="POST",
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            **options,
        )

    @setupmethod
    def put( # type: ignore[override]
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
        return self._method_route(
            rule,
            method="PUT",
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            **options,
        )


    @setupmethod
    def delete( # type: ignore[override]
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
        return self._method_route(
            rule,
            method="DELETE",
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            **options,
        )

    @setupmethod
    def patch( # type: ignore[override]
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
        return self._method_route(
            rule,
            method="PATCH",
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            **options,
        )


    @setupmethod
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
        return self._method_route(
            rule,
            method="HEAD",
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            **options,
        )

    @setupmethod
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
        return self._method_route(
            rule,
            method="OPTIONS",
            tags=tags,
            response_model=response_model,
            summary=summary,
            description=description,
            **options,
        )



