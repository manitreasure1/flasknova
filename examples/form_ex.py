from typing import cast
from flask_nova import FlaskNova, NovaBlueprint, Form, status, Depend
from pydantic import BaseModel



class TryForm(BaseModel):
    id: int
    name: str

app = FlaskNova(__name__)

bp = NovaBlueprint("form", __name__)

def get_user():
    return {"name": "Treasure"}


@bp.route("/", methods=["POST"])
def try_form(try_data: TryForm = Form(TryForm)):
    return {"id": try_data.id, "name": try_data.name}, status.CREATED

@bp.route("/hello", methods=["GET"], tags=["Greeting"], summary="Say Hello", description="Returns a hello message", response_model=dict)
def hello(user=cast(dict, Depend(get_user))):
    return {"message": f"Hello {user['name']}"}, status.OK



app.register_blueprint(bp)

if __name__=="__main__":
    app.run(debug=True)