from flasknova import FlaskNova, NovaBlueprint
from pydantic import BaseModel
from flasknova.status import status
from flasknova.d_injection import Depend
import asyncio


app = FlaskNova(__name__)
api = NovaBlueprint("api", __name__)


class UserIn(BaseModel):
    username: str
    password: str


from pydantic import BaseModel

class UserOut(BaseModel):
    id: int
    username: str

async def async_dep():
    await asyncio.sleep(0.1)
    return {"user_id": 123, "name": "async_user"}


def get_current_user():
    return {"id": 1, "username": "testuser"}


@api.route("/register", methods=["POST"])
def register(data: UserIn):
    return {"msg": f"Welcome {data.username}"}, status.CREATED



@api.route("/user", response_model=UserOut)
def get_user():
    return {"id": 1, "username": "testuser"}


@api.route("/me")
def me(user=Depend(get_current_user)):
    return user



@api.route("/async-user")
async def async_user(user=Depend(async_dep)):
    return user

app.register_blueprint(api, url_prefix="/api")

# if __name__ =='__main__':
#     app.run(debug=True)

