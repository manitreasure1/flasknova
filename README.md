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

## 🚀 Features

* ✅ Automatic OpenAPI 3.0 schema generation
* ✅ Built-in Swagger UI at `/docs` (configurable), Redoc at `/redoc`
* ✅ Request validation using Pydantic models
* ✅ Response model serialization (Pydantic, dataclass, or custom class with `to_dict`)
* ✅ Docstring-based or keyword-based `summary` and `description` for endpoints
* ✅ Typed URL parameters (`<int:id>`, `<uuid:id>`, etc.)
* ✅ Customizable Swagger UI and Redoc route path and OpenAPI metadata
* ✅ Configurable via `FLASKNOVA_ENABLED_DOCS` and `FLASKNOVA_SWAGGER_ROUTE` and `FLASKNOVA_REDOC_ROUTE`
* ✅ Clean modular routing with `NovaBlueprint`
* ✅ Built-in HTTP status codes (`flasknova.status`)
* ✅ New: **`Form()` parsing for form data**
* ✅ New: **`@guard()` decorator for combining multiple decorators (e.g. JWT + roles)**
* ✅ Minimal boilerplate and highly extensible
* ✅ **65%** type hints support

---

## 📑 Table of Contents

* [Why FlaskNova?](#why-flasknova)
* [Installation](#installation)
* [Quick Example](#quick-example)
* [Route Documentation Options](#route-documentation-options)
* [Typed URL Parameters](#typed-url-parameters)
* [Enabling Docs UI](#enabling-docs-ui)
* [Response Models](#response-models)
* [Form Parsing](#form-parsing)
* [Guard Decorator](#guard-decorator)
* [Status Codes](#status-codes)
* [Error Handling](#error-handling)
* [Response Serialization & Custom Responses](#response-serialization--custom-responses)
* [Logging](#logging)
* [CLI](#cli)
* [FAQ](#faq)
* [Learn More](#-learn-more)
* [License](#-license)
* [Contributing](#-contributing)

---

## Why FlaskNova?

FlaskNova brings modern API development to Flask with a **FastAPI-inspired design**:

* **Automatic OpenAPI/Swagger UI**: Instantly document and test your API.
* **Flexible serialization**: Use Pydantic, dataclasses, or custom classes (with type hints).
* **Dependency injection**: Cleaner, more testable route logic.
* **Unified error handling and status codes**: Consistent and robust.
* **Production-ready logging**: Built-in, unified logger.
* **Minimal boilerplate**: Focus on your business logic, not plumbing.

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
    app.setup_swagger()
    app.run(debug=True)
```

Go to [http://localhost:5000/docs](http://localhost:5000/docs) to try it out in Swagger UI.

---

## Route Documentation Options

### Using `summary` and `description`:

```python
@api.route("/hello", summary="Say hello", description="Returns a greeting message.")
def hello():
    return {"msg": "Hello!"}
```

### Or using a docstring:

```python
@api.route("/hello")
def hello():
    """Say hello.

    Returns a greeting message to the user.
    """
    return {"msg": "Hello!"}
```

---

## Typed URL Parameters

```python
@api.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id: int):
    ...
```

Supported: `int`, `float`, `uuid`, `path`, `string` (default).

---

## Enabling Docs UI

Environment vars:

| Variable                    | Default | Description                 |
| --------------------------- | ------- | --------------------------- |
| `FLASKNOVA_ENABLED_DOCS` | `True`  | Disable Swagger UI if False |
| `FLASKNOVA_SWAGGER_ROUTE`   | `/docs` | Change swagger UI path              |
| `FLASKNOVA_REDOC_ROUTE` | `/redoc` | change redoc ui path |

---

## Response Models

* ✅ Pydantic models
* ✅ Dataclasses
* ✅ Custom classes (`to_dict`, `dict`, or `dump`)

```python
import dataclasses

@dataclasses.dataclass
class User:
    id: int
    name: str

@api.route("/me", response_model=User)
def get_profile():
    return {"id": 1, "name": "nova"}
```

---

## Form Parsing

Use `Form()` to handle form data (like FastAPI’s `Form`).

```python
from flasknova import FlaskNova, NovaBlueprint, Form, status
from pydantic import BaseModel

app = FlaskNova(__name__)
api = NovaBlueprint("api", __name__)

class LoginForm(BaseModel):
    username: str
    password: str

@api.route("/login", methods=["POST"])
def login(data: LoginForm = Form(LoginForm)):
    return {"msg": f"Welcome {data.username}"}, status.OK

app.register_blueprint(api)
```

---

## Guard Decorator

Use `@guard()` to combine multiple decorators (e.g. JWT + roles).

```python
from flasknova import FlaskNova, NovaBlueprint, guard, status
from flask_jwt_extended import jwt_required

app = FlaskNova(__name__)
api = NovaBlueprint("api", __name__)

@api.route("/secure", methods=["GET"])
@guard(jwt_required())
def secure_endpoint():
    return {"msg": "You are authenticated"}, status.OK

# Multiple decorators in one
@api.route("/admin", methods=["GET"])
@guard(jwt_required(), lambda fn: print("Extra check") or fn)
def admin_only():
    return {"msg": "Admin access granted"}, status.OK
```

---

## Status Codes

```python
from flasknova import status

print(status.OK)   # 200
print(status.CREATED)  # 201
print(status.UNPROCESSABLE_ENTITY)  # 422
```

---

## Error Handling

```python
from flasknova import HTTPException, status

raise HTTPException(
    status_code=status.NOT_FOUND,
    detail="User not found",
    title="Not Found"
)
```

---

## Response Serialization & Custom Responses

```python
from flask import make_response, jsonify

@api.route("/custom", methods=["GET"])
def custom():
    data = {"message": "Custom response"}
    response = make_response(jsonify(data), 201)
    response.headers['X-Custom-Header'] = 'Value'
    return response
```

---

## Logging

```python
from flasknova import logger
logger.info("FlaskNova app started!")
```

---
## Cli

Flask-Nova provides a CLI tool to automatically generate HTTP request files (`.http`) and Python test scripts (`.py`) for your Flask routes.

### Usage

#### Command

```bash
flask-nova gen --app <your_app_path> [OPTIONS]
```

#### Required Option

* `--app TEXT` — Your Flask app import path, e.g. `examples.form_ex:app`

#### Optional Options

* `--format [http|py|all]` — File format to generate (default: `all`)
* `--base-url TEXT` — Base URL for requests (default: `http://127.0.0.1:5000`)
* `--output PATH` — Directory to save generated files (default: current directory)

#### Examples

Generate HTTP requests only:

```bash
flask-nova gen --app examples.form_ex:app --format http
```

Generate Python requests only:

```bash
flask-nova gen --app examples.form_ex:app --format py
```

Generate both HTTP and Python requests:

```bash
flask-nova gen --app examples.form_ex:app --format all
```

The generated files will handle:

* JSON for normal routes
* `multipart/form-data` for routes using `Form()`

---

## FAQ

<details>
<summary><strong>Why don't my custom class fields appear in Swagger UI?</strong></summary>
You must add class-level type hints.
</details>

<details>
<summary><strong>Why does my dataclass or custom class not validate requests?</strong></summary>
Only Pydantic models are used for request validation.
</details>

<details>
<summary><strong>Can I use Marshmallow schemas for request validation?</strong></summary>
No, Marshmallow is only supported for response serialization.
</details>

---

## Learn More

* [Flask Documentation](https://flask.palletsprojects.com/)
* [Pydantic Docs](https://docs.pydantic.dev/)

---

## License

MIT License

---

## Contributing

* Fork the repo, create your branch from `main`
* Write tests and keep code clean
* Open a PR with explanation

Issues and features: [GitHub Issues](https://github.com/manitreasure1/flasknova/issues)

---

## PyPI Release

🔗 [FlaskNova on PyPI](https://pypi.org/project/flask-nova/)
🔗 [GitHub Release Notes](https://github.com/manitreasure1/flasknova/releases)
