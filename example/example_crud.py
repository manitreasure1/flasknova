from flask import request
from flasknova import FlaskNova, NovaBlueprint, status, HTTPException
from pydantic import BaseModel

# Define Pydantic models for request and response
class EngineerIn(BaseModel):
    name: str
    language: str
    experience: int

class EngineerOut(BaseModel):
    id: int
    name: str
    language: str
    experience: int

# In-memory storage for demonstration
engineers = {}
engineer_id_counter = 1

app = FlaskNova(__name__)
bp = NovaBlueprint('engineers', __name__)

@bp.route('/engineers', methods=['POST'], response_model=EngineerOut, tags=["Engineers"], status=status.CREATED)
def create_engineer(data: EngineerIn):
    global engineer_id_counter
    engineer = EngineerOut(id=engineer_id_counter, **data.model_dump())
    engineers[engineer_id_counter] = engineer
    engineer_id_counter += 1
    print(engineer)

    return engineer, status.CREATED

@bp.route('/engineers/<int:engineer_id>', methods=['GET'], response_model=EngineerOut, tags=["Engineers"], status=status.OK)
def get_engineer(engineer_id: int):
    engineer = engineers.get(engineer_id)
    if not engineer:
        raise HTTPException(status_code=status.NOT_FOUND, detail="Engineer not found", title="Not Found")
    return engineer

@bp.route('/engineers/<int:engineer_id>', methods=['PUT'], response_model=EngineerOut, tags=["Engineers"], status=status.OK)
def update_engineer(engineer_id, data: EngineerIn):
    engineer = engineers.get(engineer_id)
    if not engineer:
        raise HTTPException(status_code=status.NOT_FOUND, detail="Engineer not found", title="Not Found")
    updated_engineer = EngineerOut(id=engineer_id, **data.model_dump())
    engineers[engineer_id] = updated_engineer
    return updated_engineer, status.OK


@bp.route('/engineers/<int:engineer_id>', methods=['DELETE'], tags=["Engineers"], status=status.NO_CONTENT)
def delete_engineer(engineer_id: int):
    if engineer_id not in engineers:
        raise HTTPException(status_code=status.NOT_FOUND, detail="Engineer not found", title="Not Found")
    del engineers[engineer_id]
    return '', status.NO_CONTENT


app.register_blueprint(bp, url_prefix="/api")

if __name__=='__main__':
    app.run(debug=True)
