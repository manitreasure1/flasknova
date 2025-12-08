from typing import Any
from flask import Blueprint, current_app, jsonify, url_for, render_template_string
from .openapi import generate_openapi


def create_docs_blueprint(
        import_name: str,
        version: str,
        security_schemes: Any,
        global_security: Any,
        docs_route: str = "/swagger",
        redoc_route: str = "/redoc",
    ):

    docs_bp = Blueprint("docs", __name__)


    @docs_bp.route("/openapi.json")
    def openapi_json():
        schema = generate_openapi(
            title=import_name,
            app=current_app,
            version=version,
            security_schemes=security_schemes,
            global_security=global_security
        )


        return jsonify(schema)


    @docs_bp.route(docs_route)
    def swagger_ui():
        openapi_url = url_for("docs.openapi_json", _external=False)

        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ title }}</title>
            <link rel="icon" type="image/png"
                  href="https://unpkg.com/swagger-ui-dist@4.15.5/favicon-32x32.png">
            <link href="https://unpkg.com/swagger-ui-dist/swagger-ui.css" rel="stylesheet">
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
            <script>
              SwaggerUIBundle({
                url: "{{ openapi_url }}",
                dom_id: '#swagger-ui',
                docExpansion: 'none'
              });
            </script>
        </body>
        </html>
        """, openapi_url=openapi_url, title=f"{import_name} - Swagger")


    @docs_bp.route(redoc_route)
    def redoc_ui():
        openapi_url = url_for("docs.openapi_json", _external=False)

        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ title }}</title>
            <meta charset="utf-8"/>
            <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
        </head>
        <body>
            <redoc spec-url="{{ openapi_url }}"></redoc>
        </body>
        </html>
        """, openapi_url=openapi_url, title=f"{import_name} - ReDoc")

    return docs_bp
