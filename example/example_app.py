from flasknova import FlaskNova, NovaBlueprint, status, Depend
from pydantic import BaseModel
import asyncio


app = FlaskNova(__name__)
api = NovaBlueprint("api", __name__)


class UserIn(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str

class RegisterResponse(BaseModel):
    msg: str



async def async_dep():
    await asyncio.sleep(0.1)
    return {"id": 123, "username": "async_user"}


def get_current_user():
    return {"id": 1, "username": "testuser"}


@api.route("/register", methods=["POST"], response_model=RegisterResponse, tags=["Users"])
def register(data: UserIn):
    return {"msg": f"Welcome {data.username}"}, status.CREATED



@api.route("/user", response_model=UserOut, tags=["Users"], methods=["GET"])
def get_user():
    return {"id": 1, "username": "testuser"}


@api.route("/me", response_model=UserOut, tags=["Users"], methods=["GET"])
def me(user=Depend(get_current_user)):
    return user



@api.route("/async-user", response_model=UserOut, tags=["Users"], methods=["GET"])
async def async_user(user=Depend(async_dep)):
    return user

app.register_blueprint(api, url_prefix="/api")




if __name__=='__main__':
    app.setup_swagger()
    app.run(debug=True)
