<p align="center">
  <img src="https://img.shields.io/pypi/v/flasknova.svg?color=blue" alt="PyPI version">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Swagger%20UI-Auto-blueviolet" alt="Swagger UI">
</p>

# FlaskNova

[GitHub Repository](https://github.com/treasureman/flasknova)

FlaskNova is a Flask extension that brings modern API development features to Flask, including:

- **Schema validation** using [Pydantic](https://pydantic-docs.helpmanual.io/) for request and response data
- **Dependency injection** for clean, testable route logic
- **Custom status codes** via a `status` module
- **Custom HTTP exceptions** for robust error handling
- **Unified logging**



---

## Table of Contents
- [Why FlaskNova?](#why-flasknova)
- [Features](#features)
- [Installation](#installation)
- [Quick Example](#quick-example)
- [Pydantic Example](#pydantic-example)
- [Custom Class Example (with Type Hints)](#custom-class-example-with-type-hints)
- [Dataclass Example](#dataclass-example)
- [Status Codes](#status-codes)
- [Error Handling](#error-handling)
- [OpenAPI & Swagger UI](#openapi--swagger-ui)
- [Response Serialization & Custom Responses](#response-serialization--custom-responses)
- [Logging](#logging)
- [Learn More](#learn-more)
- [License](#license)
- [Contributing](#contributing)
- [FAQ](#faq)

---

## Why FlaskNova?

FlaskNova brings modern API development to Flask with:
- **Automatic OpenAPI/Swagger UI**: Instantly document and test your API.
- **Flexible serialization**: Use Pydantic, dataclasses, or custom classes (with type hints) for both requests and responses.
- **Dependency injection**: Cleaner, more testable route logic.
- **Unified error handling and status codes**: Consistent, readable, and robust.
- **Production-ready logging**: Built-in, unified logger for your whole app.
- **Minimal boilerplate**: Focus on your business logic, not plumbing.

FlaskNova is ideal for teams and solo developers who want the power of modern Python API frameworks—without leaving Flask.

---

## Features

- **Swagger UI**: FlaskNova includes automatic Swagger UI documentation for your API. Once your app is running, visit `flasknova/docs` in your browser to explore and test your endpoints interactively.

- **Flexible Serialization**: Validate incoming request data and serialize responses using Pydantic models. For responses, you can return Pydantic models, dataclasses, dictionaries, or objects with a `to_dict()`/`dict()`/`dump()` method. Marshmallow schemas and custom classes with a serialization method are also supported for response serialization. **If you use a custom class, you must implement a `to_dict`, `dict`, or `dump` method—otherwise, FlaskNova will not be able to serialize your object.**
- **Dependency Injection**: Use the `Depend` helper to inject dependencies into your route handlers.
- **Status Codes**: Use the `status` module for readable HTTP status codes (e.g., `status.OK`, `status.UNPROCESSABLE_ENTITY`).
- **Custom HTTP Exceptions**: Raise `HTTPException` or `ResponseValidationError` for consistent error responses.
- **Blueprint Support**: Use `NovaBlueprint` for modular route organization.


---

## Installation

```bash
pip install flasknova 
```


---

## Quick Example


### Pydantic Example
```python
from flasknova import FlaskNova, NovaBlueprint, status, HTTPException
from pydantic import BaseModel

app = FlaskNova(__name__)
api = NovaBlueprint('api', __name__)

class UserSchema(BaseModel):
    username: str
    age: int

users = {}

@api.route('/pyduser', methods=['POST'], response_model=UserSchema)
def create_pyduser(data: UserSchema):
    users[data.username] = data
    return data, status.CREATED

@api.route('/pyduser/<string:username>', methods=['GET'], response_model=UserSchema)
def get_pyduser(username: str):
    user = users.get(username)
    if not user:
        raise HTTPException(status_code=status.NOT_FOUND, detail="User not found", title="Not Found")
    return user
```

```python
from typing import List
@api.route('/pyduser', methods=['GET'], response_model=List[UserSchema], tags=["Pydantic"])
def list_pydusers():
    return users.values()

app.register_blueprint(api)

if __name__ == "__main__":
    app.run(debug=True)
```

### Custom Class Example (with Type Hints)
```python
from flasknova import FlaskNova, NovaBlueprint, status, HTTPException

app = FlaskNova(__name__)
api = NovaBlueprint('api', __name__)

# IMPORTANT: You must add class-level type hints for OpenAPI/Swagger UI to show fields!
class CustomUser:
    id: int
    name: str
    email: str

    def __init__(self, id: int, name: str, email: str):
        self.id = id
        self.name = name
        self.email = email
    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email}

users = {}

@api.route('/customuser', methods=['POST'])
def create_customuser(data: CustomUser):
    users[data.id] = data
    return data, status.CREATED

@api.route('/customuser/<int:user_id>', methods=['GET'])
def get_customuser(user_id: int):
    user = users.get(user_id)
    if not user:
        raise HTTPException(status_code=status.NOT_FOUND, detail="User not found", title="Not Found")
    return user
```

```python
from typing import List
@api.route('/customuser', methods=['GET'], response_model=List[CustomUser], tags=["Custom"])
def list_customusers():
    return users.values()

app.register_blueprint(api)

if __name__ == "__main__":
    app.run(debug=True)
```

### Dataclass Example
```python
from flasknova import FlaskNova, NovaBlueprint, status, HTTPException
import dataclasses

app = FlaskNova(__name__)
api = NovaBlueprint('api', __name__)

@dataclasses.dataclass
class DCUser:
    id: int
    name: str
    email: str

users = {}

@api.route('/dcuser', methods=['POST'])
def create_dcuser(data: DCUser):
    users[data.id] = data
    return data, status.CREATED

@api.route('/dcuser/<int:user_id>', methods=['GET'])
def get_dcuser(user_id: int):
    user = users.get(user_id)
    if not user:
        raise HTTPException(status_code=status.NOT_FOUND, detail="User not found", title="Not Found")
    return user
```

```python
from typing import List
@api.route('/dcuser', methods=['GET'], response_model=List[DCUser], tags=["Dataclass"])
def list_dcusers():
    return users.values()

app.register_blueprint(api)

if __name__ == "__main__":
    app.run(debug=True)
```


---

## Status Codes

Use the `status` module for readable status codes:

```python
from flasknova import status

print(status.OK)  # 200
print(status.UNPROCESSABLE_ENTITY)  # 422
```


---

## Error Handling

Raise `HTTPException` or `ResponseValidationError` for custom error responses:

```python
from flasknova import HTTPException, status

raise HTTPException(
    status_code=status.NOT_FOUND,
    detail="User not found",
    title="Not Found"
)
```




---

## OpenAPI & Swagger UI

FlaskNova automatically generates an OpenAPI 3.0 schema for your app and serves interactive Swagger UI at `/flasknova/docs`.

**Supported request/response types:**

- **Pydantic models**: Full request validation and schema generation.
- **Dataclasses**: Fields and types are shown in Swagger UI (converted to Pydantic models under the hood).
- **Custom classes**: Fields are shown in Swagger UI **if you add class-level type hints** (see above). Type hints in `__init__` are not enough!
- **Marshmallow schemas**: Supported for response serialization only (not for request validation or OpenAPI schema generation).
- **Dictionaries** and objects with a `to_dict()`, `dict()`, or `dump()` method: Supported for response serialization.

**Type Hints are Required for OpenAPI!**

If you want your custom class or dataclass fields to appear in Swagger UI, you must add class-level type hints:

```python
class MyCustom:
    id: int
    name: str
    # ...
```

If you only add type hints in `__init__`, they will NOT be detected for OpenAPI schema generation.

**Example:**

```python
class Bad:
    def __init__(self, id: int):
        self.id = id  # <-- This will NOT show up in Swagger UI!
```


---

## Response Serialization & Custom Responses

FlaskNova automatically serializes your route responses using **Pydantic models**. For responses, you may also return dataclasses, dictionaries, or objects with a `to_dict()`/`dict()`/`dump()` method, or Marshmallow schemas—these will be serialized to JSON.

You can still return Flask `make_response` objects directly from your route handlers, giving you full control over headers, cookies, and advanced response customization when needed.

**Examples:**

```python
from flask import make_response, jsonify

@api.route('/custom', methods=["GET"])
def custom():
    data = {"message": "Custom response"}
    response = make_response(jsonify(data), 201)
    response.headers['X-Custom-Header'] = 'Value'
    return response
```

If you return a Flask `Response` (such as from `make_response`), FlaskNova will pass it through untouched. Otherwise, it will serialize your data and wrap it in a proper JSON response with the correct status code.


---

## Logging

Access the unified logger:

```python
from flasknova import logger
logger.info("FlaskNova app started!")
```


---

## Learn More

If you are new to Flask or want to learn more about the core framework, visit the official Flask documentation: [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)




---

## License

MIT License

---

## Contributing

Contributions are welcome! To get started:

- Fork the repository and create your branch from `main`.
- Ensure your code is well-tested and follows the existing style.
- If adding a feature or fixing a bug, please include tests and update documentation as needed.
- Open a pull request with a clear description of your changes.

For questions, suggestions, or bug reports, please open an issue on [GitHub](https://github.com/treasureman/flasknova/issues).

---

## FAQ

<details>
<summary><strong>Why don't my custom class fields appear in Swagger UI?</strong></summary>

You must add class-level type hints (not just in `__init__`). Example:
```python
class MyCustom:
    id: int
    name: str
```
</details>

<details>
<summary><strong>Why does my dataclass or custom class not validate requests?</strong></summary>

Only Pydantic models are used for request validation. Dataclasses and custom classes are supported for schema generation and response serialization, but not for request validation.
</details>

<details>
<summary><strong>Can I use Marshmallow schemas for request validation?</strong></summary>

No, Marshmallow schemas are only supported for response serialization, not for request validation or OpenAPI schema generation.
</details>

<details>
<summary><strong>How do I customize the Swagger UI or OpenAPI output?</strong></summary>

You can extend FlaskNova or open an issue/feature request on [GitHub](https://github.com/treasureman/flasknova/issues) for advanced customization needs.
</details>

<details>
<summary><strong>My schema is empty or missing fields!</strong></summary>

Make sure your class is fully imported and all fields have type hints at the class level. If you still have issues, check the logs for warnings.
</details>

<details>
<summary><strong>How do I contribute a new feature or fix a bug?</strong></summary>

1. <strong>Fork</strong> the repository and create a new branch from <code>main</code> for your feature or fix.
2. <strong>Write clear, well-tested code</strong> that follows the existing style. Add or update tests and documentation as needed.
3. <strong>Commit</strong> your changes with descriptive messages.
4. <strong>Push</strong> your branch to your fork and open a <strong>pull request</strong> (PR) against the main repository.
5. In your PR, describe your changes, reference any related issues, and explain any design decisions.
6. Participate in code review and update your PR as needed.

For questions or suggestions, open an issue on <a href="https://github.com/treasureman/flasknova/issues">GitHub</a>.

</details>

<details>
<summary><strong>Showcase: Real-world usage or integrations</strong></summary>

FlaskNova is designed to be flexible and production-ready. Here are some ways you can use it in real projects:

- <strong>Internal APIs:</strong> Build robust internal tools or microservices with automatic docs and validation.
- <strong>Public APIs:</strong> Ship developer-friendly APIs with interactive Swagger UI and clear error handling.
- <strong>Integrations:</strong> Use FlaskNova with Flask extensions (e.g., Flask-JWT-Extended for auth, Flask-CORS for cross-origin support).
- <strong>Recipes:</strong>
    - <em>Authentication:</em> Use dependency injection to inject user/session objects into your routes.
    - <em>Custom serialization:</em> Return dataclasses, custom classes, or Pydantic models for flexible responses.
    - <em>Advanced OpenAPI:</em> Add tags, descriptions, and examples to your endpoints for richer docs.

If you use FlaskNova in your project, consider sharing your experience or opening a PR to add your project to this showcase!

</details>
