import unittest
from functools import wraps
from flask_nova import  FlaskNova,NovaBlueprint, status, Form, guard
import json
from pydantic import BaseModel
from typing import Annotated

bp = NovaBlueprint("test", __name__)

def check_jwt(): return True
def check_role(): return True
def check_perm(): return False


def require_jwt(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not check_jwt():
            raise PermissionError("JWT required")
        return f(*args, **kwargs)
    return wrapped

def require_role(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not check_role():
            raise PermissionError("Role required")
        return f(*args, **kwargs)
    return wrapped

def require_perm(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not check_perm():
            raise PermissionError("Permission required")
        return f(*args, **kwargs)
    return wrapped





class UserForm(BaseModel):
    name: str
    age: int
    is_active: bool = True




@bp.route("/register-user", methods=["POST"], summary="Register User with Form", description="Accepts form data for user registration.")
async def register_user(user_data: Annotated[UserForm, Form()]):
    return user_data.model_dump(), status.CREATED



class TestGuards(unittest.TestCase):
    def test_all_guards_pass(self):
        @guard(require_jwt, require_role)
        def view():
            return "OK"
        self.assertEqual(view(), "OK")

    def test_guard_fails(self):
        @guard(require_jwt, require_perm)
        def view():
            return "OK"
        with self.assertRaises(PermissionError) as cm:
            view()
        self.assertEqual(str(cm.exception), "Permission required")

    def test_no_guard(self):
        @guard()
        def view():
            return "OK"
        self.assertEqual(view(), "OK")


class TestFormDependency(unittest.TestCase):
    def setUp(self):
        self.app = FlaskNova(__name__)
        self.app.register_blueprint(bp)
        self.client = self.app.test_client()

    def test_successful_form_submission_multipart(self):
        """Test a valid multipart/form-data submission."""
        data = {
            'name': 'Alice',
            'age': '30',
            'is_active': 'true'
        }
        response = self.client.post("/register-user", data=data)

        self.assertEqual(response.status_code, status.CREATED)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['name'], "Alice")
        self.assertEqual(response_data['age'], 30)
        self.assertEqual(response_data['is_active'], True)

    def test_successful_form_submission_urlencoded(self):
        """Test a valid application/x-www-form-urlencoded submission."""
        data = {
            'name': 'Bob',
            'age': '25',
            'is_active': 'false'
        }
        response = self.client.post("/register-user", data=data, content_type="application/x-www-form-urlencoded")

        self.assertEqual(response.status_code, status.CREATED)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['name'], "Bob")
        self.assertEqual(response_data['age'], 25)
        self.assertEqual(response_data['is_active'], False)

    def test_invalid_form_data(self):
        """Test a form submission with invalid data."""
        data = {
            'name': 'Charlie',
            'age': 'thirty',
            'is_active': 'true'
        }
        response = self.client.post("/register-user", data=data)

        self.assertEqual(response.status_code, status.UNPROCESSABLE_ENTITY)
        response_data = json.loads(response.data)
        self.assertTrue(any("age" in err["loc"] for err in response_data['detail']))

    def test_missing_required_form_field(self):
        """Test a form submission with a missing required field."""
        data = {
            'age': '45',
            'is_active': 'false'
        }
        response = self.client.post("/register-user", data=data)

        self.assertEqual(response.status_code, status.UNPROCESSABLE_ENTITY)
        response_data = json.loads(response.data)
        self.assertTrue(any("name" in err["loc"] for err in response_data['detail']))

    def test_wrong_content_type_for_form(self):
        """Test sending JSON data to an endpoint expecting form data."""
        data = {
            'name': 'David',
            'age': 25,
            'is_active': True
        }
        response = self.client.post("/register-user", json=data)

        self.assertEqual(response.status_code, status.UNSUPPORTED_MEDIA_TYPE)
        response_data = json.loads(response.data)
        self.assertIn("The endpoint expects form data", response_data['detail'])


if __name__ == "__main__":
    unittest.main()
