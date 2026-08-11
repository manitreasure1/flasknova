![Publish to PyPI](https://github.com/manitreasure1/flasknova/actions/workflows/publish.yml/badge.svg)
![Downloads](https://static.pepy.tech/badge/flask-nova)

<p align="center">
  <img src="https://img.shields.io/pypi/v/flask-nova.svg?color=blue" alt="PyPI version">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Swagger%20UI-Auto-blueviolet" alt="Swagger UI">
  <img src="https://img.shields.io/badge/ReDoc-Auto-red" alt="ReDoc">
</p>




# FlaskNova

**A modern and lightweight extension for Flask that add automatic OpenAPI schema, Swagger UI, request validation, typed routing, and structured responses.**

---

## Features

* Automatic OpenAPI schema generation
Redoc `/redoc`, Swagger ui `/docs`, Scalar `/scalar`.
* Request validation using `Pydantic`, `Dataclass`, `Custom class` binders
* Response model serialization (Pydantic, dataclass, or custom class)
* Docstring-based or keyword-based `summary` and `description` for endpoints
* Customizable Swagger UI and Redoc route path and OpenAPI metadata
* Swagger support for `MERMAID`, `FETCHREQUEST`,
* Clean modular routing with `NovaBlueprint`
* Built-in HTTP status codes (`flasknova.status`)
* RFC 7807 Problem Details Exception Handler
* **`Form()` parsing for form data**
* **`File()` parsing for file upload**
* **`@guard()` decorator for combining multiple decorators (e.g. JWT + roles)**
* **Cli** command for generating `.http` and `.py` routes endpoints and validation data types, and full route information

---

## Why FlaskNova?

FlaskNova brings modern API development to Flask:
* **Automatic Redoc/OpenAPI/Scaler/Swagger UI**: Instantly document and test your API.
* **Flexible serialization**: Use Pydantic, dataclasses, or custom classes (with type hints).
* **Dependency injection**: Cleaner, more testable route logic.
* **Unified error handling and status codes**: Consistent and robust.
* **logging**: Built-in, unified logger.
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

class User(BaseModel):
    username: str
    email: str

@app.route("/users", methods=["POST"], response_model=User, summary="Create a new user")
def create_user(data: User):
    return data, status.CREATED

if __name__ == "__main__":
    app.run(debug=True)
```

Visit [http://localhost:5000/docs](http://localhost:5000/docs) to see your API documentation!.


## Documentation
For full usage guides, including Blueprints, Dependency Injection, and CLI tools, please see the [Full Documentation](manitreasure1.github.io/flasknova).

MIT License | Built by [manitreasure1](https://github.com/manitreasure1)
