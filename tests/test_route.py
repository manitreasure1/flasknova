import unittest
from typing import cast
from flask import request
from flask_nova import FlaskNova, NovaBlueprint, status, Depend, HTTPException
import asyncio

bp = NovaBlueprint("test", __name__)



# === Dependencies ===
def get_user():
    return {"name": "Treasure"}

def get_json_data():
    return request.get_json(force=True)

async def get_async_user():
    await asyncio.sleep(0.01)
    return {"name": "AsyncTreasure"}


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
        self.app = FlaskNova(__name__)
        self.app.register_blueprint(bp)
        self.app.setup_swagger()  # enable Swagger UI
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
        self.assertEqual(response.status_code, 400)

    def test_echo_invalid_json(self):
        response = self.client.post("/echo", data="not json", content_type="application/json")
        self.assertEqual(response.status_code, 400)

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


if __name__ == "__main__":
    unittest.main()
