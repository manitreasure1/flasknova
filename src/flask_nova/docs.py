from __future__ import annotations

from flask import Blueprint, Response, jsonify, render_template_string, url_for


def create_docs_blueprint(app) -> Blueprint:
    """internal blueprint for docs

    - openapi.json
    - swagger ui
    - redoc ui
    - scalar ui

    """

    docs_bp = Blueprint("docs", __name__)
    swagger_route = app._default_urls["swagger_route"]
    redoc_route = app._default_urls["redoc_route"]
    scalar_route = app._default_urls["scalar_route"]

    @docs_bp.get("/openapi.json")
    def openapi_json() -> Response:
        return jsonify(app.openapi)

    @docs_bp.get(swagger_route)
    def swagger_ui() -> str:
        openapi_url = url_for("docs.openapi_json")
        return render_template_string(
            """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ title }}</title>
            <link href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" rel="stylesheet">
        </head>
        <body>
            <div id="swagger-ui"></div>

            <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>

            <script>
                window.onload = () => {
                    window.ui = SwaggerUIBundle({
                        url: '{{ openapi_url }}',
                        dom_id: '#swagger-ui',
                        presets: [
                            SwaggerUIBundle.presets.apis,
                        ],
                    });
                };
            </script>
        </body>
        </html>
        """,
            openapi_url=openapi_url,
            title="",
        )

    @docs_bp.get(redoc_route)
    def redoc_ui() -> str:
        openapi_url = url_for("docs.openapi_json")
        return render_template_string(
            """
            <!DOCTYPE html>
            <html>
            <head>
                <title>{{ title }}</title>
                <meta charset="utf-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
            </head>
            <body>
                <redoc spec-url='{{ openapi_url }}'></redoc>
                <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"> </script>
            </body>
            </html>
            """,
            openapi_url=openapi_url,
            title="",
        )

    @docs_bp.get(scalar_route)
    def scalar_ui():
        openapi_url = url_for("docs.openapi_json")
        return render_template_string(
            """
            <!doctype html>
            <html>
            <head>
                <title>{{ title }}</title>
                <meta charset="utf-8" />
                <meta
                name="viewport"
                content="width=device-width, initial-scale=1" />
            </head>
            <body>
                <div id="app"></div>
                <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
                <script>
                Scalar.createApiReference('#app', {
                    url: '{{ openapi_url }}',

                })
                </script>
            </body>
            </html>
            """,
            openapi_url=openapi_url,
            title="",
        )

    return docs_bp
