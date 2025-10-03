from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cosmos_helper import CosmosDBHelper
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional
import uuid
import json

load_dotenv()

app = FastAPI()

# CORS para permitir requests del frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

carnets = CosmosDBHelper(
    os.environ["COSMOS_CONTAINER_CARNETS"], "/id"
)
notas = CosmosDBHelper(
    os.environ["COSMOS_CONTAINER_NOTAS"], "/matricula"
)

# Modelo para las notas (campos opcionales con alias)
class NotaModel(BaseModel):
    id: Optional[str] = None
    matricula: str
    departamento: str
    cuerpo: str
    tratante: Optional[str] = ""
    createdAt: Optional[str] = None
    
    class Config:
        populate_by_name = True

# Modelo para los carnets (campos opcionales con alias)
class CarnetModel(BaseModel):
    id: Optional[str] = None
    matricula: str
    nombreCompleto: Optional[str] = ""
    correo: Optional[str] = ""
    edad: Optional[str] = ""
    sexo: Optional[str] = ""
    categoria: Optional[str] = ""
    programa: Optional[str] = ""
    tipoSangre: Optional[str] = ""
    enfermedadCronica: Optional[str] = ""
    unidadMedica: Optional[str] = ""
    numeroAfiliacion: Optional[str] = ""
    usoSeguroUniversitario: Optional[str] = ""
    donante: Optional[str] = ""
    emergenciaContacto: Optional[str] = ""
    # Campos adicionales del formulario Flutter
    discapacidad: Optional[str] = ""
    tipoDiscapacidad: Optional[str] = ""
    alergias: Optional[str] = ""
    emergenciaTelefono: Optional[str] = ""
    expedienteNotas: Optional[str] = ""
    expedienteAdjuntos: Optional[str] = "[]"
    
    class Config:
        populate_by_name = True

@app.get("/carnet/{id}")
def get_carnet(id: str):
    try:
        data = carnets.get_by_id(id)
        return data
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"No encontrado: {e}")

@app.get("/notas/{matricula}")
def get_notas(matricula: str):
    try:
        result = notas.query_items(
            "SELECT * FROM c WHERE c.matricula=@m ORDER BY c.createdAt DESC",
            params=[{"name": "@m", "value": matricula}]
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"No encontrado: {e}")

@app.post("/notas/")
@app.post("/notas")  # Alias sin slash final
def create_nota(nota: NotaModel = Body(...)):
    try:
        # Auto-generar campos si no se proporcionan
        nota_dict = nota.dict()
        if not nota_dict.get("id"):
            nota_dict["id"] = f"nota:{uuid.uuid4()}"
        if not nota_dict.get("createdAt"):
            nota_dict["createdAt"] = datetime.utcnow().isoformat() + "Z"
        
        print(f"[POST /notas] Request: {json.dumps(nota_dict, indent=2)}")
        
        # Cosmos: PK = /matricula
        res = notas.upsert_item(nota_dict, partition_value=nota.matricula)
        
        print(f"[POST /notas] Cosmos Success: {res}")
        return {"status": "created", "data": res, "id": nota_dict["id"]}
    except Exception as e:
        error_msg = f"Error al guardar la nota: {str(e)}"
        print(f"[POST /notas] Error: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)

# Endpoint para crear carnets (con rutas alternativas)
@app.post("/carnet/")
@app.post("/carnet")  # Alias sin slash final
def create_carnet(carnet: CarnetModel = Body(...)):
    try:
        # Auto-generar ID si no se proporciona
        carnet_dict = carnet.dict()
        if not carnet_dict.get("id"):
            carnet_dict["id"] = f"carnet:{uuid.uuid4()}"
        
        print(f"[POST /carnet] Container: carnets, PK: {carnet_dict['id']}")
        print(f"[POST /carnet] Matricula: {carnet.matricula}")
        
        # Cosmos: PK = /id
        res = carnets.upsert_item(carnet_dict, partition_value=carnet_dict["id"])
        
        print(f"[POST /carnet] SUCCESS: Document {res.get('id')} saved to carnets container")
        return {"status": "created", "data": res, "id": carnet_dict["id"]}
    except Exception as e:
        error_msg = f"Error al guardar el carnet: {str(e)}"
        print(f"[POST /carnet] Error: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)

# Endpoint adicional para compatibilidad con Flutter (rutas originales)
@app.options("/notas")
@app.options("/notas/")
@app.options("/carnet")
@app.options("/carnet/")
def handle_options():
    return {"message": "OK"}

# Health check para verificar conectividad
@app.get("/health")
def health_check():
    try:
        # Test básico de conectividad a Cosmos
        test_query = notas.query_items("SELECT TOP 1 * FROM c")
        return {
            "status": "healthy",
            "cosmos_connected": True,
            "containers": {
                "carnets": os.environ.get("COSMOS_CONTAINER_CARNETS", "unknown"),
                "notas": os.environ.get("COSMOS_CONTAINER_NOTAS", "unknown")
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error": str(e),
            "cosmos_connected": False
        }