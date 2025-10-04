from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from azure.cosmos.exceptions import CosmosHttpResponseError
from cosmos_helper import CosmosDBHelper
from datetime import datetime
from typing import Optional
import uuid
import os
import json

# Google Calendar imports (optional)
try:
    from googleapiclient.discovery import build
    from google.oauth2.service_account import Credentials
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# Router para citas
router = APIRouter()

# Contenedor para citas - usar contenedor cita_id con PK /cita
citas = CosmosDBHelper(
    os.environ.get("COSMOS_CONTAINER_CITAS", "cita_id"), "/cita"
)

def create_google_event(cita_data):
    """Crear evento en Google Calendar si está habilitado"""
    if not os.environ.get("GCAL_ENABLED", "false").lower() == "true":
        return None, None
    
    if not GOOGLE_AVAILABLE:
        print("[GCAL] Google libraries not available")
        return None, None
    
    try:
        # Configurar credenciales
        sa_json = os.environ.get("GCAL_SA_JSON")
        if not sa_json:
            print("[GCAL] No service account JSON configured")
            return None, None
        
        # Parse JSON de credenciales
        if sa_json.startswith('{'):
            credentials_info = json.loads(sa_json)
        else:
            # Asumir que es una ruta de archivo
            with open(sa_json) as f:
                credentials_info = json.load(f)
        
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        service = build('calendar', 'v3', credentials=credentials)
        calendar_id = os.environ.get("GCAL_CALENDAR_ID", "primary")
        app_tz = os.environ.get("APP_TZ", "UTC")
        
        # Crear evento
        event = {
            'summary': cita_data['motivo'],
            'description': f"Paciente: {cita_data['matricula']}\nDepartamento: {cita_data.get('departamento', 'N/A')}",
            'start': {
                'dateTime': cita_data['inicio'],
                'timeZone': app_tz,
            },
            'end': {
                'dateTime': cita_data['fin'],
                'timeZone': app_tz,
            },
        }
        
        # Insertar evento
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        
        event_id = created_event.get('id')
        html_link = created_event.get('htmlLink')
        
        print(f"[GCAL] Event created: {event_id}")
        return event_id, html_link
        
    except Exception as e:
        print(f"[GCAL] Error creating event: {type(e).__name__}: {str(e)}")
        return None, None

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
    cita: Optional[str] = None  # PK para contenedor cita_ida
    inicio: str  # ISO datetime
    fin: str     # ISO datetime
    motivo: str
    departamento: Optional[str] = ""
    estado: Optional[str] = "programada"
    googleEventId: Optional[str] = ""
    htmlLink: Optional[str] = ""
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    
    class Config:
        populate_by_name = True

@router.post("/citas")
def create_cita(cita: CitaModel = Body(...)):
    try:
        # DRY-RUN: Log al entrar
        print(f"[DRY-RUN POST /citas] container_target=cita_id, pk_path=/cita, Payload keys: {list(cita.dict().keys())}")
        
        # Auto-generar campos si no se proporcionan
        cita_dict = cita.dict()
        if not cita_dict.get("id"):
            cita_dict["id"] = f"cita:{uuid.uuid4()}"
            print(f"[DRY-RUN POST /citas] Autocomplete id: {cita_dict['id']}")
        if not cita_dict.get("cita"):
            cita_dict["cita"] = cita.matricula  # cita = matricula como fallback
            print(f"[DRY-RUN POST /citas] Autocomplete cita: {cita_dict['cita']} (from matricula)")
        if not cita_dict.get("createdAt"):
            cita_dict["createdAt"] = datetime.utcnow().isoformat() + "Z"
        cita_dict["updatedAt"] = datetime.utcnow().isoformat() + "Z"
        
        # Intentar crear evento en Google Calendar
        google_event_id, html_link = create_google_event(cita_dict)
        if google_event_id:
            cita_dict["googleEventId"] = google_event_id
            cita_dict["htmlLink"] = html_link
        
        # Cosmos: upsert en cita_id con PK = /cita
        res = citas.upsert_item(cita_dict, partition_value=cita_dict["cita"])
        
        gcal_status = "✅" if google_event_id else "⚠️"
        print(f"[DRY-RUN POST /citas] container_cita_id.upsert_item(doc, partition_key={cita_dict['cita']})")
        print(f"[POST /citas] Status: 201, ID: {res.get('id')}, _etag: {res.get('_etag', 'N/A')}, GCAL: {gcal_status}")
        print("[DRY-RUN POST /citas] SUCCESS: Documento guardado en cita_id (NO en carnets_id)")
        
        return {"status": "created", "data": res, "id": cita_dict["id"]}
    except CosmosHttpResponseError as e:
        print(f"[POST /citas] Cosmos Error: {e.status_code} - {e.message}")
        raise HTTPException(status_code=e.status_code, detail={"code": e.status_code, "message": e.message})
    except Exception as e:
        print(f"[POST /citas] Error: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})

@router.get("/citas/{matricula}")
def get_citas(matricula: str):
    try:
        result = citas.query_items(
            "SELECT * FROM c WHERE c.matricula=@m AND STARTSWITH(c.id, 'cita:') ORDER BY c._ts DESC",
            params=[{"name": "@m", "value": matricula}]
        )
        print(f"[GET /citas/{matricula}] Container: cita_id, Filter: cita:*, Results: {len(result)}")
        return result
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.status_code, "message": e.message})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})