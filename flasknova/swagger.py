from flask import Blueprint, jsonify, render_template_string, current_app
from .openapi import generate_openapi 


swagger_bp = Blueprint("swagger", __name__)

@swagger_bp.route("/openapi.json")
def openapi_json():
    return jsonify(generate_openapi(current_app))



@swagger_bp.route("/docs")
def swagger_ui():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
      <head>
        <title>Swagger UI</title>
        <link href="https://unpkg.com/swagger-ui-dist/swagger-ui.css" rel="stylesheet">
      </head>
      <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
        <script>
          SwaggerUIBundle({
            url: '/flasknova/openapi.json',
            dom_id: '#swagger-ui'
          });
        </script>
      </body>
    </html>
    """)
