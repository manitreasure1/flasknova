from dataclasses import dataclass, field
from typing import Any, Annotated, Literal, NoReturn
from uuid import UUID
from pydantic import BaseModel, Field

from flask_nova import (
    FlaskNova,
    NovaBlueprint,
    HTTPException,
    status,
    Form,
    File,
    Depend,
    FileStorage,
)


async def jwt_async() -> dict[str, str]:
    return {"msg": "Hello User"}


def jwt() -> dict[str, str]:
    return {"msg": "Hello User"}


class BMUser(BaseModel):
    name: str = Field(..., description="User name field")
    age: str = Field(..., max_length=2, description="User age field")


class BMStudent(BaseModel):
    """Student Binder class"""

    name: str | int
    gender: Literal["male", "female"]
    age: str | None


@dataclass
class DCAuthor:
    """Author Binder class"""

    name: str = field(
        metadata={"description": "User name field", "max_digit": 5}
    )  # using `metadata` in dataclasses field you can add any useful field that is available in the openapi specs
    age: int


class CCUser:
    "User 2 binder"

    age: int | None
    name: str

    def to_dict(self): ...


class Home(BaseModel):
    address: str


class AuthUser(BaseModel):
    id: UUID
    username: str


app = FlaskNova()

api = NovaBlueprint("api", url_prefix="/api")

auth_api = NovaBlueprint("auth", url_prefix="/auth")

app.config["ANSI_COLOR_JSON_LOG"] = (
    True  # this modifies app.logger to log colored json object
)


@app.route(
    "/address",
    tags=["Address"],
    summary="get user address",
    description="#User address route \n return object required field as a key with 5 max digit ",
    responses={"200": {}},
    response_model=Home,
)
def getuser_address() -> dict[str, str]:
    # Note the model `Home` will serialize the object if extra it will ignore and if the field address is not found an error will be thrown
    return {"address": "12-222-89"}


@app.post(
    "/",
    tags=["User", "Admin"],
    summary="user home page",
    description="This uses Native Response dispatcher `tuple[BMUser, int]` the user object will be serialize using the return type provided",
)
def home(user: BMUser) -> tuple[BMUser, int]:
    return user, 200


@app.post(
    "/upload-profile",
    tags=["User"],
    summary="User profile Upload",
    description="Upload File using File() object",
)
def upload_profile(
    profile: FileStorage = File("profile", description="My Profile Picture")
) -> dict[str, str]:
    profile.save("images")
    return {"message": "Welcome Home!"}


@app.post(
    "/upload-profiles",
    tags=["User"],
    summary="User profile Upload",
    description="Upload File using File() object",
)
def upload_profiles(
    profile: list[FileStorage] = File(
        "profile", description="Users Profile Picture", multiple=True
    )
) -> dict[str, str]:
    # Mutiple file upload `argument multiple= True is expected in the File() object`
    for f in profile:
        f.save("images")
    return {"message": "Welcome Home!"}


@app.post(
    "/empyty-form",
    tags=["Form", "Multiparts"],
    summary="Multipart Request",
    description="Form data request",
)
def empty_form(user=Form()) -> dict[str, Any]:
    return {"message": "Welcome Home!"}


@app.post(
    "/form-body",
    tags=["User", "Admin", "Hommie"],
    summary="Something Nice",
    description="Nothing much to say",
)
def form_req_body(user: CCUser = Form()) -> dict[str, Any]:
    return {"message": "Welcome Home!"}


@app.post(
    "/form-string",
    tags=["User", "Admin", "Form"],
    summary="Upload",
    description="Form data request",
)
def form_str(user: Annotated[str, Form()]) -> dict[str, Any]:
    return {"message": "Welcome Home!"}


@app.post(
    "/annotation-file",
    tags=["User", "Admin", "Dean"],
    summary="Upload File",
    description="Using Annotation with file object",
    response_model=Home,
)
def anno_file(user: Annotated[FileStorage, File("")]) -> dict[str, Any]:
    return {"message": "Welcome Home!"}


@app.post(
    "/secure",
    tags=["User", "Admin"],
    summary="Dependency Injection",
    description="Scope dependency via Depend",
)
def secure_(user=Depend(jwt)):
    return {"message": user["msg"]}


@app.post(
    "/secure-async",
    tags=["User", "Admin"],
    summary="Dependency Injection",
    description="Scope dependency via Depend",
)
async def secure_async(user=Depend(jwt_async)):
    u = await user  # type: ignore
    #  if the dependency is awaitable use await before you can access its values
    return {"message": u["msg"]}


@api.get(
    "/query-req",
    tags=["User", "Admin"],
    summary="User Query",
    description="expect id, name and age from request query obj",
)
def queryreq(id: int, name: str, age: int) -> dict[str, str]:
    return {"message": f"Welcome Home! {id}-{name}-{age}"}


@api.get(
    "/query-user",
    tags=["User", "Query"],
    summary="User Query",
    description="expect id, name and age from request query obj",
)
def queryuser(id: int, name: str, age: int) -> dict[str, str]:
    return {"message": f"{id}-{name}-{age}"}


@app.get("/author/<int:author_id>/books/<string:genre>/", tags=["author"])
def author(
    author: DCAuthor, author_id: int, genre: str, year: int, month
) -> tuple[DCAuthor, int]:  # alternative use `Literal["201"]`` instead of `int`
    """
    The Author Counter
    Author Json and and path param request
    """
    return author, 201


@app.post(
    "/student",
    tags=["author"],
    summary="Literal status code",
    description="Build openapi spec using the specified Literal value",
    responses={"200": {"Description": "YE"}},
)
def create_student(
    user: BMStudent,
) -> tuple[
    dict[str, str], Literal[201]
]:  # Literal 201 will be used as the valid response status code unlike int which has no value
    return {"msg": "Student account created"}, 201


@app.get(
    "/student",
    tags=["author"],
    summary="Native Response Dispatcher",
    description="Using response object to serialize response type",
)
def get_student() -> BMStudent:
    author = BMStudent(name="Mani", gender="male", age="12")
    return author


@app.post(
    "/create-user",
    tags=["author"],
    summary="Something Nice",
    description="Nothing much to say",
)
def create_user(user: BMUser) -> dict[str, Any]:
    return user.model_dump()  # this is already in dict form


@auth_api.put("/login")
def login() -> NoReturn:
    raise HTTPException(status.BAD_REQUEST, "An error occured", "Bad Request")


@auth_api.post("/signup")
def signup(user: AuthUser):
    return {"meg": "Welcome User"}


@app.post("/log")
def register() -> dict[str, str]:
    app.logger.debug("/register")
    app.logger.info("/register")
    app.logger.error("/register", exc_info=True)
    app.logger.critical("/register")
    app.logger.warning("/register")
    return {"msg": "m"}


app.register_blueprint(blueprint=api)
app.register_blueprint(auth_api)


if __name__ == "__main__":

    app.run(debug=True)
