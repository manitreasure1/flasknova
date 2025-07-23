from flask import Blueprint, jsonify, render_template_string, current_app, url_for
from flask_nova.openapi import generate_openapi

def create_swagger_blueprint(docs_route="/doc"):
    swagger_bp = Blueprint("swagger", __name__)

    @swagger_bp.route("/openapi.json")
    def openapi_json():
        return jsonify(generate_openapi(current_app))

    @swagger_bp.route(docs_route)
    def swagger_ui():
        openapi_url = url_for("swagger.openapi_json", _external=False)
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Swagger UI</title>
            <link rel="icon" type="image/png" href="https://unpkg.com/swagger-ui-dist@4.15.5/favicon-32x32.png">
            <link href="https://unpkg.com/swagger-ui-dist/swagger-ui.css" rel="stylesheet">
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
            <script>
              SwaggerUIBundle({
                url: "{{ openapi_url }}",
                dom_id: '#swagger-ui'
              });
            </script>
        </body>
        </html>
        """, openapi_url=openapi_url)

    return swagger_bp
