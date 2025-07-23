from src.flask_nova import FlaskNova

app = FlaskNova(__name__)

# 1. Summary, description, and tags explicitly provided
@app.route(
    "/status",
    methods=["GET"],
    summary="Get system status",
    description="Returns a JSON object with the current system status (e.g., disabled or not).",
    tags=["System"]
)
def get_status():
    return {"status": "disabled"}

# 2. Docstring-based summary/description with tags
@app.route("/info", methods=["GET"], tags=["Meta"])
def info():
    """Get app info.

    Returns metadata about the application setup, routes, and configuration.
    """
    return {"info": "App is using FlaskNova with Swagger UI."}

# 3. Both docstring and explicit summary/description/tags
@app.route(
    "/", 
    methods=["GET"],
    summary="Root welcome endpoint",
    description="Returns a JSON message indicating that this is the root of the API.",
    tags=["Welcome"]
)
def root():
    """This is the root endpoint.

    Returns a welcome message to the API consumers.
    """
    return {"message": "Welcome to FlaskNova API"}

if __name__ == '__main__':
    app.setup_swagger(info={
            "title": "FlaskNova API test",
            "version": "1.2.3",
            "description": "Beautiful API for modern apps.",
            "termsOfService": "https://example.com/terms",
            "contact": {
                "name": "Team FlaskNova",
                "url": "https://github.com/flasknova",
                "email": "support@flasknova.dev"
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        })
    app.run(debug=True)
