# Examples for FlaskNova

This file shows practical examples of how to use FlaskNova in real-world scenarios.

---

## Basic Example

```python
from flasknova import FlaskNova, NovaBlueprint, status

app = FlaskNova(__name__)

@app.route("/ping")
def ping():
    return {"message": "pong"}, status.OK

if __name__ == "__main__":
    app.run(debug=True)
```
Visit [http://localhost:5000/docs](http://localhost:5000/docs)` for Swagger UI or [http://localhost:5000/redoc](http://localhost:5000/redoc) for Redoc UI.

---

## Pydantic Model Example

```python
from flasknova import FlaskNova, NovaBlueprint, status
from pydantic import BaseModel

app = FlaskNova(__name__)

class User(BaseModel):
    username: str
    email: str

@app.route("/users", methods=["POST"], response_model=User)
def create_user(data: User):
    return data, status.CREATED
```

---

## Dataclass Example

```python
import dataclasses
from flasknova import FlaskNova, NovaBlueprint, status

app = FlaskNova(__name__)

@dataclasses.dataclass
class DCUser:
    id: int
    name: str

@app.post("/dcuser", response_model=DCUser)
def create_dcuser(data: DCUser):
    return data, status.CREATED
```
---

## Custom Class Example

```python
from flasknova import FlaskNova, NovaBlueprint, status, HTTPException

app = FlaskNova(__name__)

class CustomUser:
    id: int
    name: str

    def to_dict():... # attr to identify custom class

@app.route("/customuser", methods=["POST"], response_model=CustomUser)
def create_customuser(data: CustomUser):
    return data, status.CREATED

@app.route("/customuser/<int:user_id>", methods=["GET"])
def get_customuser(user_id: int):
    user = users.get(user_id)
    if not user:
        raise HTTPException(status_code=status.NOT_FOUND, detail="User not found")
    return user
```

---

## Using Form Data

```python
from flasknova import FlaskNova, NovaBlueprint, status, Form
from pydantic import BaseModel
from typing import Annotated

app = FlaskNova(__name__)

class UserForm(BaseModel):
    id: int
    name: str

@app.route("/default/form", methods=["POST"])
def default_form(user_data: UserForm = Form()):
    return {"id": user_data.id, "name": user_data.name}, status.CREATED

@app.post("/annotated/form")
def annotated_form(user_data: Annotated[UserForm, Form()])
    return user_data.id

```
---

## Using `guard` Decorator

```python
from flasknova import FlaskNova, NovaBlueprint, guard, status
from flask_jwt_extended import jwt_required

app = FlaskNova(__name__)


@app.route("/secure", methods=["GET"])
@guard(jwt_required)
def secure_endpoint():
    return {"msg": "This is a protected endpoint"}, status.OK
```

---

## Typed URL Parameters

```python
@api.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id: int):
    return {"id": item_id}, status.OK
```

---

## Error Handling Example

```python
from flasknova import HTTPException, status

@api.route("/fail")
def fail():
    raise HTTPException(
        status_code=status.BAD_REQUEST,
        detail="Invalid request",
        title="Bad Request"
    )
```
