# FlaskNova

FlaskNova is a Flask extension that brings modern API development features to Flask, including:

- **Schema validation** using [Pydantic](https://pydantic-docs.helpmanual.io/) for request and response data
- **Dependency injection** for clean, testable route logic
- **Custom status codes** via a `status` module
- **Custom HTTP exceptions** for robust error handling
- **Unified logging**

## Features

- **Pydantic Validation**: Validate incoming request data and serialize responses using Pydantic models.
- **Dependency Injection**: Use the `Depend` helper to inject dependencies into your route handlers.
- **Status Codes**: Use the `status` module for readable HTTP status codes (e.g., `status.OK`, `status.UNPROCESSABLE_ENTITY`).
- **Custom HTTP Exceptions**: Raise `HTTPException` or `ResponseValidationError` for consistent error responses.
- **Blueprint Support**: Use `NovaBlueprint` for modular route organization.

## Installation

```bash
pip install flasknova 
```

## Quick Example

```python
from flasknova import FlaskNova, NovaBlueprint, Depend, status
from pydantic import BaseModel

app = FlaskNova(__name__)
api = NovaBlueprint('api', __name__)

class UserSchema(BaseModel):
    username: str
    age: int

def get_current_user():
    return {"username": "alice", "age": 30}

@api.route('/hello', methods=["POST"], response_model=UserSchema)
def hello(user: UserSchema, current=Depend(get_current_user)):
    # user is validated, current is injected
    return {"username": user.username, "age": user.age}

app.register_blueprint(api)

if __name__ == "__main__":
    app.run(debug=True)
```

## Status Codes

Use the `status` module for readable status codes:

```python
from flasknova import status

print(status.OK)  # 200
print(status.UNPROCESSABLE_ENTITY)  # 422
```

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

## Logging

Access the unified logger:

```python
from flasknova import logger
logger.info("FlaskNova app started!")
```

## Learn More

If you are new to Flask or want to learn more about the core framework, visit the official Flask documentation: [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)

## Roadmap

- File uploads (coming soon)
- Form handling (coming soon)
- UI helpers and integrations (coming soon)

Stay tuned for more features!

## License

MIT License
