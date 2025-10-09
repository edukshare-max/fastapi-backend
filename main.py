from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
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

# Startup configuration check (only for DEBUG_CITAS)
if os.environ.get("DEBUG_CITAS", "false").lower() == "true":
    import subprocess
    try:
        commit_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], 
                                            cwd=os.path.dirname(__file__)).decode().strip()
    except:
        commit_hash = "unknown"

    print(f"APP_BOOT db={os.environ.get('COSMOS_DB', 'NOT_SET')} "
          f"container_citas={os.environ.get('COSMOS_CONTAINER_CITAS', 'NOT_SET')} "
          f"pk={os.environ.get('COSMOS_PK_CITAS', 'NOT_SET')}")

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
promociones_salud = CosmosDBHelper(
    os.environ.get("COSMOS_CONTAINER_PROMOCIONES_SALUD", "promociones_salud"), "/id"
)

# Handlers directos para citas (contenedor citas_ida exclusivamente)
from cosmos_helper import get_citas_container, get_citas_pk_path, upsert_cita

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

# Modelo para promociones de salud
class PromocionSaludModel(BaseModel):
    id: Optional[str] = None
    link: str
    departamento: str
    categoria: str
    programa: str
    matricula: Optional[str] = ""  # Matrícula del alumno (opcional)
    destinatario: str  # "alumno" o "general"
    autorizado: Optional[bool] = False
    createdAt: Optional[str] = None
    createdBy: Optional[str] = ""  # Usuario que creó la promoción
    
    class Config:
        populate_by_name = True

@app.get("/carnet/{id}")
def get_carnet(id: str):
    # Normalizar id: si no empieza con carnet:, agregar prefijo
    normalized_id = id if id.startswith("carnet:") else f"carnet:{id}"
    
    # Intento A: lectura directa por id normalizado
    try:
        data = carnets.get_by_id(normalized_id)
        return data
    except CosmosHttpResponseError as e:
        # Intento B: Si NotFound → query por matricula excluyendo citas
        if e.status_code == 404:
            try:
                results = carnets.query_items(
                    """SELECT TOP 1 * FROM c 
                       WHERE c.matricula = @m 
                         AND NOT STARTSWITH(c.id, 'cita:')
                         AND NOT IS_DEFINED(c.inicio)
                         AND NOT IS_DEFINED(c.fin)
                       ORDER BY c._ts DESC""",
                    params=[{"name": "@m", "value": id}]
                )
                
                if results:
                    return results[0]
                else:
                    raise HTTPException(status_code=404, detail={"code": 404, "message": "Carnet no encontrado"})
                    
            except CosmosHttpResponseError as fallback_error:
                raise HTTPException(status_code=fallback_error.status_code or 500, detail={"code": fallback_error.status_code or 500, "message": fallback_error.message or "Error en query"})
        else:
            raise HTTPException(status_code=e.status_code or 500, detail={"code": e.status_code or 500, "message": e.message or "Error en cosmos"})
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


@app.get("/_diag/citas")
def diagnose_citas():
    """Endpoint de diagnóstico para verificar configuración de citas (solo con DEBUG_CITAS)"""
    # Solo permitir acceso si DEBUG_CITAS está activado
    if os.environ.get("DEBUG_CITAS", "false").lower() != "true":
        raise HTTPException(status_code=404, detail={"code": 404, "message": "Endpoint no encontrado"})
    
    try:
        from cosmos_helper import get_citas_container, get_citas_pk_path
        
        # Obtener configuración
        db_name = os.environ.get("COSMOS_DB", "NOT_SET")
        container_name = os.environ.get("COSMOS_CONTAINER_CITAS", "NOT_SET")
        pk_path = os.environ.get("COSMOS_PK_CITAS", "NOT_SET")
        
        # Probar conectividad
        can_read = False
        try:
            container = get_citas_container()
            # Test con query simple
            list(container.query_items("SELECT TOP 1 * FROM c", enable_cross_partition_query=True))
            can_read = True
        except Exception as e:
            if os.environ.get("DEBUG_CITAS", "false").lower() == "true":
                print(f"[DIAG] Error testing citas container: {e}")
        
        return {
            "db": db_name,
            "container": container_name,
            "pk_path": pk_path,
            "can_read": can_read
        }
    except Exception as e:
        return {
            "error": str(e),
            "db": os.environ.get("COSMOS_DB", "NOT_SET"),
            "container": os.environ.get("COSMOS_CONTAINER_CITAS", "NOT_SET"),
            "pk_path": os.environ.get("COSMOS_PK_CITAS", "NOT_SET"),
            "can_read": False
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
        # Lazy init: obtener contenedor dentro del handler
        container = get_citas_container()
        
        cita_dict = cita.dict()
        
        # Validar mínimos
        if not all([cita_dict.get("matricula"), cita_dict.get("inicio"), 
                   cita_dict.get("fin"), cita_dict.get("motivo")]):
            raise HTTPException(status_code=400, detail="Campos requeridos: matricula, inicio, fin, motivo")
        
        # Usar helper exclusivo para citas
        result = upsert_cita(cita_dict)
        
        return {"status": "created", "data": result}
        
    except Exception as cosmos_error:
        if "Error connecting to citas container" in str(cosmos_error):
            # Error de configuración/credenciales: devolver 503
            return JSONResponse(
                status_code=503,
                content={"error": "citas_unavailable", "detail": str(cosmos_error)}
            )
        # Otros errores
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(cosmos_error)})

@app.get("/citas/{cita_id}")
def get_cita_by_id(cita_id: str):
    try:
        # Lazy init: obtener contenedor dentro del handler
        container = get_citas_container()
        pk_path = get_citas_pk_path()
        
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
        
        return result
        
    except Exception as cosmos_error:
        if "Error connecting to citas container" in str(cosmos_error):
            # Error de configuración/credenciales: devolver 503
            return JSONResponse(
                status_code=503,
                content={"error": "citas_unavailable", "detail": str(cosmos_error)}
            )
        elif "404" in str(cosmos_error) or "not found" in str(cosmos_error).lower():
            raise HTTPException(status_code=404, detail={"code": 404, "message": "Cita no encontrada"})
        # Otros errores
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(cosmos_error)})

@app.get("/citas/por-matricula/{matricula}")
def get_citas_by_matricula(matricula: str):
    try:
        # Lazy init: obtener contenedor dentro del handler
        container = get_citas_container()
        
        # Query siempre en cita_id
        query = "SELECT * FROM c WHERE c.matricula = @m ORDER BY c._ts DESC"
        params = [{"name": "@m", "value": matricula}]
        
        results = list(container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        ))
        
        return results
        
    except Exception as cosmos_error:
        if "Error connecting to citas container" in str(cosmos_error):
            # Error de configuración/credenciales: devolver 503
            return JSONResponse(
                status_code=503,
                content={"error": "citas_unavailable", "detail": str(cosmos_error)}
            )
        # Otros errores
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(cosmos_error)})

# Endpoints para promociones de salud
@app.post("/promociones-salud/")
@app.post("/promociones-salud")
def create_promocion_salud(promocion: PromocionSaludModel = Body(...)):
    """Crear una nueva promoción de salud"""
    try:
        # Auto-generar campos si no se proporcionan
        promocion_dict = promocion.dict()
        if not promocion_dict.get("id"):
            promocion_dict["id"] = f"promocion:{uuid.uuid4()}"
        if not promocion_dict.get("createdAt"):
            promocion_dict["createdAt"] = datetime.utcnow().isoformat() + "Z"
        
        # Cosmos: PK = /id
        res = promociones_salud.upsert_item(promocion_dict, partition_value=promocion_dict["id"])
        return res
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=e.status_code or 500, detail={"code": e.status_code or 500, "message": e.message or "Error en cosmos"})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})

@app.get("/promociones-salud/")
def get_promociones_salud():
    """Obtener todas las promociones de salud"""
    try:
        result = promociones_salud.query_items(
            "SELECT * FROM c ORDER BY c.createdAt DESC"
        )
        return result
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=e.status_code or 500, detail={"code": e.status_code or 500, "message": e.message or "Error en cosmos"})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})

@app.post("/promociones-salud/validate-supervisor")
def validate_supervisor_key(key_data: dict = Body(...)):
    """Validar clave de supervisor"""
    supervisor_key = key_data.get("key", "")
    valid_key = "UAGROcres2025"
    
    if supervisor_key == valid_key:
        return {"valid": True, "message": "Clave válida"}
    else:
        return {"valid": False, "message": "Clave incorrecta"}