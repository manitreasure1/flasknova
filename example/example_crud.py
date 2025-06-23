from typing import List
from flask import jsonify
from flasknova import FlaskNova, NovaBlueprint, status, HTTPException, get_flasknova_logger
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
    log.debug(engineers_list)
    return engineers_list, status.OK

@bp.route('/engineers', methods=['POST'], response_model=EngineerOut, tags=["Engineers"], status=status.CREATED)
def create_engineer(data: EngineerIn):
    global engineer_id_counter
    engineer = EngineerOut(id=engineer_id_counter, **data.model_dump())
    engineers[engineer_id_counter] = engineer
    engineer_id_counter += 1
    return engineer, status.CREATED



@bp.route('/engineers/<int:engineer_id>', methods=['GET'],response_model=EngineerOut, tags=["Engineers"])
def get_engineer(engineer_id: int):
    
    engineer = engineers.get(engineer_id)

    if not engineer:
        raise HTTPException(status_code=status.NOT_FOUND, detail="Engineer not found", title="Not Found")
    log.debug(engineer.model_dump())
    log.debug(f"---------id-------{engineer_id}")


    # for eng_id, engineer in engineers.items():

    #     print(f"{eng_id}----------{engineer}")
    #     print(f"{eng_id==2}----------")
    return engineer.model_dump(), status.OK

@bp.route('/engineers/<int:engineer_id>', methods=['PUT'], response_model=EngineerOut, tags=["Engineers"])
def update_engineer(engineer_id: int, data: EngineerIn):
    log.debug(f"engineer_id: {engineer_id}")
    engineer = engineers.get(engineer_id)
    log.debug(f"-------------------------------{engineer}")
    if not engineer:
        raise HTTPException(status_code=status.NOT_FOUND, detail="Engineer not found", title="Not Found")
    updated_engineer = EngineerOut(id=engineer_id, **data.model_dump())
    engineers[engineer_id] = updated_engineer
    return updated_engineer.model_dump(), status.OK


@bp.route('/engineers/<int:engineer_id>', methods=['DELETE'], tags=["Engineers"])
def delete_engineer(engineer_id: int):
    if engineer_id not in engineers:
        raise HTTPException(status_code=status.NOT_FOUND, detail="Engineer not found", title="Not Found")
    del engineers[engineer_id]
    return '', status.NO_CONTENT



app.register_blueprint(bp, url_prefix="/api")

if __name__=='__main__':
    app.run(debug=True)
