from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cosmos_helper import CosmosDBHelper
from azure.cosmos.exceptions import CosmosHttpResponseError
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

# Handlers directos para citas (contenedor citas_ida exclusivamente)
from cosmos_helper import get_citas_container, get_citas_pk_path, upsert_cita
from pydantic import BaseModel
from typing import Optional
import uuid

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
    edad: Optional[int] = 0
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
    # DRY-RUN: Log de entrada
    print(f"[DRY-RUN] Entrada: raw_id={id}")
    
    # Normalizar id: si no empieza con carnet:, agregar prefijo
    normalized_id = id if id.startswith("carnet:") else f"carnet:{id}"
    print(f"[DRY-RUN] normalized_id={normalized_id}, ruta=/carnet/{id}, contenedor=carnets")
    
    # Intento A: lectura directa por id normalizado
    try:
        print(f"[DRY-RUN] Intento A: read_item(item={normalized_id}, partition_key={normalized_id})")
        data = carnets.get_by_id(normalized_id)
        print(f"[DRY-RUN] Decisión: devolviendo carnet (encontrado por ID)")
        return data
    except CosmosHttpResponseError as e:
        # Intento B: Si NotFound → query por matricula excluyendo citas
        if e.status_code == 404:
            try:
                print(f"[DRY-RUN] Intento B: query por matrícula={id} excluyendo citas")
                results = carnets.query_items(
                    """SELECT TOP 1 * FROM c 
                       WHERE c.matricula = @m 
                         AND NOT STARTSWITH(c.id, 'cita:')
                         AND NOT IS_DEFINED(c.inicio)
                         AND NOT IS_DEFINED(c.fin)
                       ORDER BY c._ts DESC""",
                    params=[{"name": "@m", "value": id}]
                )
                
                print(f"[DRY-RUN] Query resultados: {len(results) if results else 0}")
                if results:
                    print(f"[DRY-RUN] Decisión: devolviendo carnet (encontrado por matrícula)")
                    return results[0]
                else:
                    print(f"[DRY-RUN] Decisión: 404 no encontrado")
                    raise HTTPException(status_code=404, detail={"code": 404, "message": "Carnet no encontrado"})
                    
            except CosmosHttpResponseError as fallback_error:
                print(f"[DRY-RUN] Decisión: 404 no encontrado (error en query)")
                raise HTTPException(status_code=fallback_error.status_code, detail={"code": fallback_error.status_code, "message": fallback_error.message})
        else:
            raise HTTPException(status_code=e.status_code, detail={"code": e.status_code, "message": e.message})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})

@app.get("/notas/{matricula}")
def get_notas(matricula: str):
    try:
        result = notas.query_items(
            "SELECT * FROM c WHERE c.matricula=@m ORDER BY c.createdAt DESC",
            params=[{"name": "@m", "value": matricula}]
        )
        return result
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.status_code, "message": e.message})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})

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
        
        # Cosmos: PK = /matricula
        res = notas.upsert_item(nota_dict, partition_value=nota.matricula)
        
        return {"status": "created", "data": res, "id": nota_dict["id"]}
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.status_code, "message": e.message})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})

# Endpoint para crear carnets (con rutas alternativas)
@app.post("/carnet/")
@app.post("/carnet")  # Alias sin slash final
def create_carnet(carnet: CarnetModel = Body(...)):
    try:
        # Auto-generar ID si no se proporciona
        carnet_dict = carnet.dict()
        if not carnet_dict.get("id"):
            carnet_dict["id"] = f"carnet:{uuid.uuid4()}"
        
        # Cosmos: PK = /id
        res = carnets.upsert_item(carnet_dict, partition_value=carnet_dict["id"])
        
        return {"status": "created", "data": res, "id": carnet_dict["id"]}
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.status_code, "message": e.message})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})

# Alias de expediente para compatibilidad con Flutter
@app.get("/expediente/matricula/{matricula}")
def get_expediente_by_matricula(matricula: str):
    """Alias para búsqueda de carnet por matrícula"""
    return get_carnet(matricula)

@app.get("/expediente/{id}")
def get_expediente_by_id(id: str):
    """Alias para búsqueda de carnet por ID"""
    return get_carnet(id)

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


# === RUTAS DE CITAS (contenedor citas_ida exclusivamente) ===

class CitaModel(BaseModel):
    id: Optional[str] = None
    matricula: str
    inicio: str  # ISO datetime
    fin: str     # ISO datetime
    motivo: str
    departamento: Optional[str] = ""
    estado: Optional[str] = "programada"
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

@app.post("/citas")
def create_cita(cita: CitaModel):
    try:
        # DRY-RUN: Al entrar
        container = get_citas_container()
        pk_path = get_citas_pk_path()
        cita_dict = cita.dict()
        
        print(f"[DRY-RUN] POST /citas - db: DakuSasu, container: citas_ida, pk_path: {pk_path}")
        print(f"[DRY-RUN] payload keys: {list(cita_dict.keys())}")
        
        # Validar mínimos
        if not all([cita_dict.get("matricula"), cita_dict.get("inicio"), 
                   cita_dict.get("fin"), cita_dict.get("motivo")]):
            raise HTTPException(status_code=400, detail="Campos requeridos: matricula, inicio, fin, motivo")
        
        # Usar helper exclusivo para citas
        result = upsert_cita(cita_dict)
        
        return {"status": "created", "data": result}
        
    except CosmosHttpResponseError as e:
        print(f"[DRY-RUN] Error Cosmos: {e.status_code}")
        raise HTTPException(status_code=e.status_code or 500, detail={"code": e.status_code or 500, "message": str(e)})
    except Exception as e:
        print(f"[DRY-RUN] Error general: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})

@app.get("/citas/{cita_id}")
def get_cita_by_id(cita_id: str):
    try:
        container = get_citas_container()
        pk_path = get_citas_pk_path()
        
        print(f"[DRY-RUN] GET /citas/{cita_id} - leyendo desde citas_ida, pk_path: {pk_path}")
        
        if pk_path == "/id":
            # Leer directo por partition key
            result = container.read_item(item=cita_id, partition_key=cita_id)
        else:
            # Query cross-partition
            query = "SELECT * FROM c WHERE c.id = @id"
            params = [{"name": "@id", "value": cita_id}]
            results = list(container.query_items(
                query=query, 
                parameters=params, 
                enable_cross_partition_query=True
            ))
            if not results:
                raise HTTPException(status_code=404, detail={"code": 404, "message": "Cita no encontrada"})
            result = results[0]
        
        print(f"[DRY-RUN] Cita encontrada en citas_ida: {result.get('id')}")
        return result
        
    except CosmosHttpResponseError as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail={"code": 404, "message": "Cita no encontrada"})
        raise HTTPException(status_code=e.status_code or 500, detail={"code": e.status_code or 500, "message": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})

@app.get("/citas/por-matricula/{matricula}")
def get_citas_by_matricula(matricula: str):
    try:
        container = get_citas_container()
        
        print(f"[DRY-RUN] GET /citas/por-matricula/{matricula} - leyendo desde citas_ida")
        
        # Query siempre en citas_ida
        query = "SELECT * FROM c WHERE c.matricula = @m ORDER BY c._ts DESC"
        params = [{"name": "@m", "value": matricula}]
        
        results = list(container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        ))
        
        print(f"[DRY-RUN] Citas encontradas en citas_ida: {len(results)}")
        return results
        
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=e.status_code or 500, detail={"code": e.status_code or 500, "message": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})