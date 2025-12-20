# Examples for FlaskNova

This file shows practical examples of how to use FlaskNova in real-world scenarios.

---

## 🚀 Basic Example

```python
from flasknova import FlaskNova, NovaBlueprint, status

app = FlaskNova(__name__)
api = NovaBlueprint("api", __name__)

@api.route("/ping")
def ping():
    return {"message": "pong"}, status.OK

app.register_blueprint(api)

if __name__ == "__main__":
    app.setup_swagger()
    app.run(debug=True)
```

Visit `http://localhost:5000/docs` for Swagger UI or `http://localhost:5000/redoc` for Redoc UI.

---

## 📦 Pydantic Model Example

```python
from flasknova import FlaskNova, NovaBlueprint, status
from pydantic import BaseModel

app = FlaskNova(__name__)
api = NovaBlueprint("api", __name__)

class User(BaseModel):
    username: str
    email: str

@api.route("/users", methods=["POST"], response_model=User)
def create_user(data: User):
    return data, status.CREATED

app.register_blueprint(api)
```

---

## 🧑‍💻 Dataclass Example

```python
import dataclasses
from flasknova import FlaskNova, NovaBlueprint, status

app = FlaskNova(__name__)
api = NovaBlueprint("api", __name__)

@dataclasses.dataclass
class DCUser:
    id: int
    name: str

@api.route("/dcuser", methods=["POST"], response_model=DCUser)
def create_dcuser(data: DCUser):
    return data, status.CREATED

app.register_blueprint(api)
```

---

## 🛠️ Custom Class Example

```python
from flasknova import FlaskNova, NovaBlueprint, status, HTTPException

app = FlaskNova(__name__)
api = NovaBlueprint("api", __name__)

class CustomUser:
    id: int
    name: str

    def to_dict(self):
        return {"id": self.id, "name": self.name}

users = {}

@api.route("/customuser", methods=["POST"], response_model=CustomUser)
def create_customuser(data: CustomUser):
    users[data.id] = data
    return data, status.CREATED

@api.route("/customuser/<int:user_id>", methods=["GET"])
def get_customuser(user_id: int):
    user = users.get(user_id)
    if not user:
        raise HTTPException(status_code=status.NOT_FOUND, detail="User not found")
    return user

app.register_blueprint(api)
```

---

## 📝 Using Form Data

```python
from flasknova import FlaskNova, NovaBlueprint, status, Form
from pydantic import BaseModel

app = FlaskNova(__name__)
api = NovaBlueprint("api", __name__)

class TryForm(BaseModel):
    id: int
    name: str

@api.route("/form", methods=["POST"])
def try_form(try_data: TryForm = Form(TryForm)):
    return {"id": try_data.id, "name": try_data.name}, status.CREATED

app.register_blueprint(api)
```

---

## 🔐 Using `guard` Decorator

```python
from flasknova import FlaskNova, NovaBlueprint, guard, status
from flask_jwt_extended import jwt_required

app = FlaskNova(__name__)
api = NovaBlueprint("api", __name__)

@api.route("/secure", methods=["GET"])
@guard(jwt_required)
def secure_endpoint():
    return {"msg": "This is a protected endpoint"}, status.OK

app.register_blueprint(api)
```

---

## ✅ Typed URL Parameters

```python
@api.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id: int):
    return {"id": item_id, "name": "Item"}, status.OK
```

---

## 📚 Error Handling Example

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


