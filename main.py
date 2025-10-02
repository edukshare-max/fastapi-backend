from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from cosmos_helper import CosmosDBHelper
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

carnets = CosmosDBHelper(
    os.environ["COSMOS_CONTAINER_CARNETS"], "/id"
)
notas = CosmosDBHelper(
    os.environ["COSMOS_CONTAINER_NOTAS"], "/matricula"
)

# Modelo para las notas
class NotaModel(BaseModel):
    id: str
    matricula: str
    departamento: str
    cuerpo: str
    tratante: str
    createdAt: str

# Modelo para los carnets (nuevo)
class CarnetModel(BaseModel):
    id: str
    matricula: str
    nombreCompleto: str
    correo: str
    edad: str
    sexo: str
    categoria: str
    programa: str
    tipoSangre: str
    enfermedadCronica: str
    unidadMedica: str
    numeroAfiliacion: str
    usoSeguroUniversitario: str
    donante: str
    emergenciaContacto: str
    # Puedes agregar más campos si lo necesitas

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
def create_nota(nota: NotaModel = Body(...)):
    try:
        res = notas.upsert_item(nota.dict(), partition_value=nota.matricula)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al guardar la nota: {e}")

# Nuevo endpoint para crear carnets
@app.post("/carnet/")
def create_carnet(carnet: CarnetModel = Body(...)):
    try:
        res = carnets.upsert_item(carnet.dict(), partition_value=carnet.id)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al guardar el carnet: {e}")