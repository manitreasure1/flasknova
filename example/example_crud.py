from typing import List
from flask import jsonify, make_response
from src.flask_nova import FlaskNova, NovaBlueprint, status, HTTPException, get_flasknova_logger
from pydantic import BaseModel

log = get_flasknova_logger()

class EngineerIn(BaseModel):
    name: str
    language: str
    experience: int

class EngineerOut(BaseModel):
    id: int
    name: str
    language: str
    experience: int

engineers = {}
engineer_id_counter = 1

app = FlaskNova(__name__)
bp = NovaBlueprint('engineers', __name__)


@bp.route('/engineers', methods=['GET'],response_model=List[EngineerOut], tags=["Engineers"])
def list_engineers():
    engineers_list = [e.model_dump() for e in engineers.values()]
    response = make_response(jsonify(engineers_list), status.OK)
    return response

@bp.route('/engineers', methods=['POST'], response_model=EngineerOut, tags=["Engineers"])
def create_engineer(data: EngineerIn):
    global engineer_id_counter
    engineer = EngineerOut(id=engineer_id_counter, **data.model_dump())
    engineers[engineer_id_counter] = engineer
    engineer_id_counter += 1
    response = make_response(jsonify(engineer.model_dump()), status.CREATED)
    return response



@bp.route('/engineers/<int:engineer_id>', methods=['GET'],response_model=EngineerOut, tags=["Engineers"])
def get_engineer(engineer_id: int):
    
    engineer = engineers.get(engineer_id)

    if not engineer:
        raise HTTPException(status_code=status.NOT_FOUND, detail="Engineer not found", title="Not Found")
    response = make_response(jsonify(engineer.model_dump()), status.OK)
    return response

@bp.route('/engineers/<int:engineer_id>', methods=['PUT'], response_model=EngineerOut, tags=["Engineers"])
def update_engineer(engineer_id: int, data: EngineerIn):
    log.debug(f"engineer_id: {engineer_id}")
    engineer = engineers.get(engineer_id)
    if not engineer:
        raise HTTPException(status_code=status.NOT_FOUND, detail="Engineer not found", title="Not Found")
    updated_engineer = EngineerOut(id=engineer_id, **data.model_dump())
    engineers[engineer_id] = updated_engineer
    response = make_response(jsonify(updated_engineer.model_dump()), status.NO_CONTENT)
    return response


@bp.route('/engineers/<int:engineer_id>', methods=['DELETE'], tags=["Engineers"])
def delete_engineer(engineer_id: int):
    if engineer_id not in engineers:
        raise HTTPException(status_code=status.NOT_FOUND, detail="Engineer not found", title="Not Found")
    del engineers[engineer_id]
    response = make_response('', status.NO_CONTENT)
    return response



app.register_blueprint(bp, url_prefix="/api")

if __name__=='__main__':
    app.setup_swagger()
    app.run(debug=True)
