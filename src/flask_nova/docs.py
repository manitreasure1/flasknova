from flask import Blueprint, Response, jsonify, render_template_string, url_for


def create_docs_blueprint(app) -> Blueprint:
    docs_bp = Blueprint("docs", __name__)

    @docs_bp.get("/openapi.json")
    def openpai_json() -> Response:
        return jsonify(app.openapi)

    @docs_bp.get("/docs")
    def swagger_ui() -> str:
        openapi_url = url_for("docs.openapi_json", _external=False)
        return render_template_string("""""", openapi_url="openapi_url", title="")

    @docs_bp.get("/redoc")
    def redoc_ui() -> str:
        openapi_url = url_for("docs.openapi_json", _external=False)
        return render_template_string("""""", openapi_url="openapi_url", title="")

    @docs_bp.get("/scalar")
    def scalar_ui():
        openapi_url = url_for("docs.openapi_json", _external=False)
        return render_template_string("""""", openapi_url="openapi_url", title="")

    return docs_bp
