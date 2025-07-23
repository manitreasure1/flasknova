from src.flask_nova import FlaskNova, NovaBlueprint, status, logger
from pydantic import BaseModel
import time
from example.security_auth import encode_jwt, jwt_required

# Dummy user store
users = {}

app = FlaskNova(__name__)
bp = NovaBlueprint("Auth", __name__)

# Request schema
class AuthRequest(BaseModel):
    username: str
    password: str

# Response schema
class TokenResponse(BaseModel):
    token: str

@bp.route(
    "/register",
    tags=["Auth"],
    methods=["POST"],
    summary="Register a new user",
    description="Creates a new user account with a username and password."
)
def register(data: AuthRequest):
    if data.username in users:
        return {"msg": "User already exists"}, status.CONFLICT
    users[data.username] = data.password
    logger.info("Created")
    return {"msg": "Registration successful"}, status.CREATED


@bp.route(
    "/login",
    tags=["Auth"],
    methods=["POST"],
    response_model=TokenResponse,
    summary="Login a user",
    description="Authenticates a user and returns a JWT access token if credentials are valid."
)
def login(data: AuthRequest):
    password = users.get(data.username)
    if not password or password != data.password:
        return {"msg": "Invalid credentials"}, status.UNAUTHORIZED

    payload = {
        "sub": data.username,
        "exp": int(time.time()) + 3600 
    }
    token = encode_jwt(payload)
    return {"token": token}, status.OK


@bp.route(
    "/me",
    tags=["Auth"],
    methods=["GET"],
    summary="Get current user info",
    description="Returns information about the currently authenticated user."
)
@jwt_required
def get_me():
    return {"user": ""}, status.OK

app.register_blueprint(bp, prefix="auth")

if __name__ == "__main__":
    app.setup_swagger()
    app.run(debug=True)
