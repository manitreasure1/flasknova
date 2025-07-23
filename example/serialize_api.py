from typing import List
from src.flask_nova import FlaskNova, NovaBlueprint, status, get_flasknova_logger
from pydantic import BaseModel
import dataclasses

log =get_flasknova_logger()
# Pydantic model
class PydUser(BaseModel):
    id: int
    name: str
    email: str

# Custom model
class CustomUser:
    id: int
    name: str
    email: str

    # def __init__(self, id: int, name: str, email: str):
    #     self.id = id
    #     self.name = name
    #     self.email = email

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email}

# Dataclass model
@dataclasses.dataclass
class DCUser:
    id: int
    name: str
    email: str

users = {
    "pydantic": {},
    "custom": {},
    "dataclass": {},
}

bp = NovaBlueprint('serialize_api', __name__)
app = FlaskNova(__name__)

# Pydantic CRUD
@bp.route('/pyduser', methods=['POST'], response_model=PydUser, tags=["Pydantic"])
def create_pyduser(data: PydUser):
    users["pydantic"][data.id] = data
    log.info("Pydantic Create")
    return data, status.CREATED

@bp.route('/pyduser/<int:user_id>', methods=['GET'], response_model=PydUser, tags=["Pydantic"])
def get_pyduser(user_id: int):
    log.info("Pydantic Get")

    return users["pydantic"].get(user_id)

@bp.route('/pyduser', methods=['GET'], response_model=List[PydUser], tags=["Pydantic"])
def list_pydusers():
    log.info("Pydantic Get")

    return users["pydantic"].values()

# Custom model CRUD
@bp.route('/customuser', methods=['POST'], tags=["Custom"])
def create_customuser(custome_user: CustomUser):
    users["custom"][custome_user.id] = custome_user
    log.info("Custom Model Create")

    return custome_user, status.CREATED

@bp.route('/customuser/<int:user_id>', methods=['GET'], tags=["Custom"])
def get_customuser(user_id: int):
    log.info("Custom Model Get")

    return users["custom"].get(user_id)

@bp.route('/customuser', methods=['GET'],response_model=List[CustomUser], tags=["Custom"])
def list_customusers():
    log.info("Custom Model Get")

    return users["custom"].values()


# Dataclass CRUD
@bp.route('/dcuser', methods=['POST'], tags=["Dataclass"])
def create_dcuser(user: DCUser):
    users["dataclass"][user.id] = user
    log.info("Dataclass Model Create")

    return user, status.CREATED

@bp.route('/dcuser/<int:user_id>', methods=['GET'], tags=["Dataclass"])
def get_dcuser(user_id: int):
    log.info("Dataclass Model Get")

    return users["dataclass"].get(user_id)

@bp.route('/dcuser', methods=['GET'], response_model=List[DCUser], tags=["Dataclass"])
def list_dcusers():
    log.info("Dataclass Model Get")

    return users["dataclass"].values()


app.register_blueprint(bp, url_prefix="/api")

if __name__=='__main__':
    app.run(debug=True)