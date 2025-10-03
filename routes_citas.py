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

# Contenedor para citas
citas = CosmosDBHelper(
    os.environ.get("COSMOS_CONTAINER_CITAS", "citas"), "/matricula"
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
        
        # Cosmos: PK = /matricula
        res = citas.upsert_item(cita_dict, partition_value=cita.matricula)
        
        print(f"[POST /citas] Container: citas, PK: {cita.matricula}, ID: {cita_dict['id']}, Status: created")
        return {"status": "created", "data": res, "id": cita_dict["id"]}
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.status_code, "message": e.message})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})

@router.get("/citas/{matricula}")
def get_citas(matricula: str):
    try:
        result = citas.query_items(
            "SELECT * FROM c WHERE c.matricula=@m ORDER BY c._ts DESC",
            params=[{"name": "@m", "value": matricula}]
        )
        print(f"[GET /citas/{matricula}] Container: citas, Results: {len(result)}")
        return result
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.status_code, "message": e.message})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})