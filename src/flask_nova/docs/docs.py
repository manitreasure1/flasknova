from typing import Any
from flask import (
    Blueprint,
    Response,
    current_app,
    g,
    jsonify,
    url_for,
    render_template_string,
)
from .openapi import generate_openapi


def create_docs_blueprint(
    import_name: str,
    version: str | None,
    security_schemes: Any,
    global_security: Any,
    docs_route: str,
    redoc_route: str,
    openapi_info: dict[str, Any] | None = None,
    json_schema_dialect: str | None = None,
    external_docs: dict[str, Any] | None = None,
    servers: list[dict[str, str]] | None = None,
    cache_schema: bool = True

) -> Blueprint:

    docs_bp = Blueprint("docs", __name__)

    @docs_bp.route("/openapi.json")
    def openapi_json() -> Response:
        if cache_schema and hasattr(g, '_nova_openapi_schema'):
            schema = g._nova_openapi_schema
        else:
            schema = generate_openapi(
                title=import_name,
                app=current_app,
                version=version,
                security_schemes=security_schemes,
                global_security=global_security,
                openapi_info=openapi_info,
                json_schema_dialect=json_schema_dialect,
                external_docs=external_docs,
                servers=servers
            )
            if cache_schema:
                g._nova_openapi_schema = schema

        return jsonify(schema)

    @docs_bp.route(docs_route)
    def swagger_ui() -> str:
        openapi_url = url_for("docs.openapi_json", _external=False)

        return render_template_string(
            """
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ title }}</title>
            <link rel="icon" type="image/png"
                  href="https://unpkg.com/swagger-ui-dist@5.17.14/favicon-32x32.png">
            <link href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css" rel="stylesheet">
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
            <script>
              SwaggerUIBundle({
                url: "{{ openapi_url }}",
                dom_id: '#swagger-ui',
                docExpansion: 'none',
                presets: [
                  SwaggerUIBundle.presets.apis,
                  SwaggerUIBundle.presets.standalone
                ],
                plugins: [
                  SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
              });
            </script>
        </body>
        </html>
        """,
            openapi_url=openapi_url,
            title=f"{import_name} - Swagger",
        )

    @docs_bp.route(redoc_route)
    def redoc_ui() -> str:
        openapi_url = url_for("docs.openapi_json", _external=False)

        return render_template_string(
            """
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ title }}</title>
            <meta charset="utf-8"/>
            <link rel="icon" type="image/png" href="https://favicon.pub/redocly.com">
            <script type="module" src="https://cdn.redoc.ly/redoc/v3.1.0/redoc.standalone.js"> </script>
        </head>
        <body>
            <redoc spec-url="{{ openapi_url }}"></redoc>
        </body>
        </html>
        """,
            openapi_url=openapi_url,
            title=f"{import_name} - ReDoc",
        )

    return docs_bp
