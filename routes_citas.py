from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from azure.cosmos.exceptions import CosmosHttpResponseError
from cosmos_helper import CosmosDBHelper
from datetime import datetime
from typing import Optional
import uuid
import os

# Router para citas
router = APIRouter()

# Contenedor para citas - usar mismo contenedor que carnets por simplicidad
citas = CosmosDBHelper(
    os.environ["COSMOS_CONTAINER_CARNETS"], "/id"
)

# Modelo para las citas
class CitaModel(BaseModel):
    id: Optional[str] = None
    matricula: str
    inicio: str  # ISO datetime
    fin: str     # ISO datetime
    motivo: str
    departamento: Optional[str] = ""
    estado: Optional[str] = "programada"
    googleEventId: Optional[str] = ""
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    
    class Config:
        populate_by_name = True

@router.post("/citas")
def create_cita(cita: CitaModel = Body(...)):
    try:
        # Auto-generar campos si no se proporcionan
        cita_dict = cita.dict()
        if not cita_dict.get("id"):
            cita_dict["id"] = f"cita:{uuid.uuid4()}"
        if not cita_dict.get("createdAt"):
            cita_dict["createdAt"] = datetime.utcnow().isoformat() + "Z"
        cita_dict["updatedAt"] = datetime.utcnow().isoformat() + "Z"
        
        # Cosmos: PK = /id (mismo patrón que carnets)
        res = citas.upsert_item(cita_dict, partition_value=cita_dict["id"])
        
        print(f"[POST /citas] Container: carnets, PK: {cita_dict['id']}, Matricula: {cita.matricula}, Status: created")
        return {"status": "created", "data": res, "id": cita_dict["id"]}
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.status_code, "message": e.message})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})

@router.get("/citas/{matricula}")
def get_citas(matricula: str):
    try:
        result = citas.query_items(
            "SELECT * FROM c WHERE c.matricula=@m AND STARTSWITH(c.id, 'cita:') ORDER BY c._ts DESC",
            params=[{"name": "@m", "value": matricula}]
        )
        print(f"[GET /citas/{matricula}] Container: carnets, Filter: cita:*, Results: {len(result)}")
        return result
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.status_code, "message": e.message})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})