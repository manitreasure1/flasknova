import unittest
from typing import cast, Annotated
from flask import request
from flask_nova import FlaskNova, NovaBlueprint, status, Depend, HTTPException, Form
import asyncio
from pydantic import BaseModel

bp = NovaBlueprint("test", __name__)



# === Dependencies ===
def get_user():
    return {"name": "Treasure"}

def get_json_data():
    return request.get_json(force=True)

async def get_async_user():
    await asyncio.sleep(0.01)
    return {"name": "AsyncTreasure"}

class UserForm(BaseModel):
    name: str
    age: int
    is_active: bool = True




@bp.route("/register-user", methods=["POST"], summary="Register User with Form", description="Accepts form data for user registration.")
def register_user(user_data: Annotated[UserForm, Form]):
    return user_data.model_dump(), status.CREATED



# === Routes ===
@bp.route("/hello", methods=["GET"], tags=["Greeting"], summary="Say Hello", description="Returns a hello message", response_model=dict)
def hello(user=cast(dict, Depend(get_user))):
    return {"message": f"Hello {user['name']}"}, status.OK

@bp.route("/error", methods=["GET"], summary="Trigger Error", description="Raises an error intentionally")
def error_route():
    raise HTTPException(detail="Something went wrong", status_code=400)

@bp.route("/echo", methods=["POST"], summary="Echo JSON", description="Echoes posted JSON data", response_model=dict)
def echo(data=cast(dict, Depend(get_json_data))):
    return {"echo": data}, status.OK


@bp.route("/async-hello", methods=["GET"], summary="Async Hello", response_model=dict)
async def async_hello(user=cast(dict, Depend(get_async_user))):
    return {"message": f"Hello {user['name']}"}, status.OK

# === Tests ===
class FlaskNovaTestCase(unittest.TestCase):
    def setUp(self):
        self.app = FlaskNova(import_name="mani", version="1.1.2")
        self.app.register_blueprint(bp)

        self.client = self.app.test_client()

    def test_hello_route(self):
        response = self.client.get("/hello")
        self.assertEqual(response.status_code, 200)
        
        self.assertIn("message", response.get_json())
        self.assertIn("Treasure", response.get_json()["message"])

    def test_error_route(self):
        response = self.client.get("/error")
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.get_json())

    def test_echo_route(self):
        data = {"foo": "bar"}
        response = self.client.post("/echo", json=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"echo": data})

    def test_echo_missing_json(self):
        response = self.client.post("/echo")
        self.assertEqual(response.status_code, 500)

    def test_echo_invalid_json(self):
        response = self.client.post("/echo", data="not json", content_type="application/json")
        self.assertEqual(response.status_code, 500)

    def test_openapi_schema(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("paths", data)
        self.assertIn("/hello", data["paths"])



    def test_swagger_ui_available(self):
        response = self.client.get("/docs")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Swagger", response.data)

    def test_hello_route_with_different_user(self):
        # Access the original dependency and replace it
        route_func = bp.view_functions.get("hello", "test.hello")

        if hasattr(route_func, "__wrapped__"):
            original_depend = route_func.__wrapped__.__defaults__[0]
            self.assertIsInstance(original_depend, Depend)

            # Patch dependency
            def fake_user():
                return {"name": "TestUser"}

            original_depend.dependency = fake_user

            response = self.client.get("/hello")
            self.assertEqual(response.status_code, 200)
            self.assertIn("TestUser", response.get_json()["message"])

    async def test_async_hello(self):
        response = self.client.get("/async-hello")
        self.assertEqual(response.status_code, 200)
        self.assertIn("AsyncTreasure", response.get_json()["message"])


    def test_successful_form_submission_multipart(self):
        """Test a valid multipart/form-data submission."""
        data = {
            'name': 'Alice',
            'age': '30',
            'is_active': 'true'
        }
        response = self.client.post("/register-user", data=data, content_type="application/x-www-form-urlencoded")

        self.assertEqual(response.status_code, status.CREATED)
        # response_data = json.loads(response.data)
        # self.assertEqual(response_data['name'], "Alice")
        # self.assertEqual(response_data['age'], 30)
        # self.assertEqual(response_data['is_active'], True)


if __name__ == "__main__":
    unittest.main()
