![Publish to PyPI](https://github.com/manitreasure1/flasknova/actions/workflows/publish.yml/badge.svg)
![Downloads](https://static.pepy.tech/badge/flask-nova)

<p align="center">
  <img src="https://img.shields.io/pypi/v/flask-nova.svg?color=blue" alt="PyPI version">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Swagger%20UI-Auto-blueviolet" alt="Swagger UI">
  <img src="https://img.shields.io/badge/ReDoc-Auto-red" alt="ReDoc">
</p>


# FlaskNova

**A modern and lightweight extension for Flask that brings FastAPI-style features like automatic OpenAPI schema, Swagger UI, request validation, typed routing, and structured responses.**

---

## Features

* Automatic OpenAPI 3.0 schema generation
* Built-in Swagger UI at `/docs` (configurable), Redoc at `/redoc`
* Request validation using Pydantic models
* Response model serialization (Pydantic, dataclass, or custom class with `to_dict`)
* Docstring-based or keyword-based `summary` and `description` for endpoints
* Typed URL parameters (`<int:id>`, `<uuid:id>`, etc.)
* Customizable Swagger UI and Redoc route path and OpenAPI metadata
* Configurable via `FLASKNOVA_ENABLED_DOCS` and `FLASKNOVA_SWAGGER_ROUTE` and `FLASKNOVA_REDOC_ROUTE`
* Clean modular routing with `NovaBlueprint`
* Built-in HTTP status codes (`flasknova.status`)
* **`Form()` parsing for form data**
* **`@guard()` decorator for combining multiple decorators (e.g. JWT + roles)**
* **Cli** command for generating `.http` and `.py` routes endpoints and validation data types
* **65%** type hints support

---

## Why FlaskNova?

FlaskNova brings modern API development to Flask with a **FastAPI-inspired design**:

* **Automatic Redoc/OpenAPI/Swagger UI**: Instantly document and test your API.
* **Flexible serialization**: Use Pydantic, dataclasses, or custom classes (with type hints).
* **Dependency injection**: Cleaner, more testable route logic.
* **Unified error handling and status codes**: Consistent and robust.
* **Production-ready logging**: Built-in, unified logger.

---

## Installation

```bash
pip install flask-nova
```

---

## Quick Example

```python
from flasknova import FlaskNova, NovaBlueprint, status
from pydantic import BaseModel

app = FlaskNova(__name__)
api = NovaBlueprint("api", __name__)

class User(BaseModel):
    username: str
    email: str

@api.route("/users", methods=["POST"], response_model=User, summary="Create a new user")
def create_user(data: User):
    return data, status.CREATED

app.register_blueprint(api)

if __name__ == "__main__":
    app.run(debug=True)
```

Visit [http://localhost:5000/docs](http://localhost:5000/docs) to see your API documentation!.


## Documentation
For full usage guides, including Blueprints, Dependency Injection, and CLI tools, please see the [Full Documentation](https://manitreasure1.github.io/flasknova/).

MIT License | Built by [manitreasure1](https://github.com/manitreasure1)


