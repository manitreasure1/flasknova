![Publish to PyPI](https://github.com/manitreasure1/flasknova/actions/workflows/publish.yml/badge.svg)
![Downloads](https://static.pepy.tech/badge/flask-nova)

<p align="center">
  <img src="https://img.shields.io/pypi/v/flask-nova.svg?color=blue" alt="PyPI version">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Swagger%20UI-Auto-blueviolet" alt="Swagger UI">
  <img src="https://img.shields.io/badge/ReDoc-Auto-red" alt="ReDoc">
</p>


FlaskNova — lightweight Flask extension for automatic OpenAPI, docs,
request validation, typed routing, and response serialization.

**Overview**
FlaskNova provides small, focused tools to make building typed HTTP APIs with
Flask easier: automatic OpenAPI generation, lightweight documentation UIs,
request/response binders, and helpers for errors and logging.

**Features (brief descriptions)**
- **OpenAPI & docs**: Produces an OpenAPI document (`/openapi.json`) and
  exposes lightweight UI routes (`/docs`, `/redoc`, `/scalar`) for quick
  inspection and manual testing.
- **Request parsing & validation**: Bind and validate inputs using Pydantic
  models, dataclasses, or custom binder classes; includes `Form` and `File`
  helpers for form data and uploads.
- **Response serialization**: Describe responses with `response_model` and
  return native types; the library serializes Pydantic/dataclass/custom
  objects consistently before returning JSON.
- **Typed routing & `NovaBlueprint`**: Method-specific decorators (`@app.get`,
  `@app.post`, etc.) accept metadata and `response_model` to keep routes
  explicit and documented.
- **Dependency injection**: `Depend` allows small provider callables to supply
  route arguments (useful for auth, services, or computed values).
- **Error handling & status helpers**: RFC 7807 problem-detail responses and a
  `status` helper module for common HTTP status codes and consistency.
- **CLI utilities**: Minimal CLI commands to generate request examples and
  inspect route metadata for development convenience.
- **Logging**: Optional structured JSON logger when `ANSI_COLOR_JSON_LOG` is
  enabled in the app config.

Installation

```bash
pip install flask-nova
```

Minimal example

```python
from flask_nova import FlaskNova, status
from pydantic import BaseModel

app = FlaskNova(__name__)

class User(BaseModel):
    username: str
    email: str

@app.post("/users", response_model=User)
def create_user(data: User):
    return data, status.CREATED

if __name__ == "__main__":
    app.run()
```

Examples
- See usage examples and bindings in the repository: [examples/nova2.py](examples/nova2.py#L1).

Documentation
- Full docs and examples: https://manitreasure1.github.io/flasknova

License
- MIT
