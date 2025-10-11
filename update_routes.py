# temp_backend/update_routes.py
"""
Rutas y lógica para el sistema de actualizaciones automáticas.
Endpoints para verificar versiones, descargar actualizaciones y obtener changelog.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List
from update_models import (
    VersionInfo,
    UpdateCheckRequest,
    UpdateCheckResponse,
    ChangelogEntry,
    ChangelogResponse
)

router = APIRouter(prefix="/updates", tags=["updates"])

# =====================================================================
# CONFIGURACIÓN DE VERSIONES
# =====================================================================
# En producción, esto debería venir de una base de datos o archivo config
# Por ahora, usamos una estructura en memoria que se puede actualizar

# Versión actual del sistema (la más reciente disponible)
LATEST_VERSION = VersionInfo(
    version="2.4.0",
    build_number=1,
    release_date="2025-10-11",
    channel="stable",
    download_url="https://github.com/edukshare-max/UPDATE_CRES_CARNET_/releases/download/v2.4.0/CRES_Carnets_Windows_v2.4.0.zip",
    file_size=88000000,  # ~88 MB (aproximado)
    checksum="",  # Se calculará después
    minimum_version="2.0.0",
    is_mandatory=False,
    changelog=[
        "Odontograma Profesional dual: infantil (20 dientes) y adulto (32 dientes)",
        "5 superficies por diente con click directo",
        "14 condiciones dentales con colores profesionales",
        "PDF A4 horizontal optimizado y centrado",
        "5 Tests de Psicología: Hamilton, Beck, DASS-21, Plutchik, MBI",
        "Mejoras UX: paneles optimizados, feedback inmediato, card discreta"
    ]
)

# Historial completo de versiones
VERSION_HISTORY: List[ChangelogEntry] = [
    ChangelogEntry(
        version="2.3.2",
        date="2025-10-10",
        changes=[
            "Sistema de distribución con instalador profesional",
            "Versionamiento automático con VersionService",
            "Pantalla 'Acerca de' con changelog completo",
            "88 instituciones UAGro integradas",
            "Dropdown de login con todas las instituciones",
            "Colores institucionales UAGro aplicados"
        ]
    ),
    ChangelogEntry(
        version="2.3.1",
        date="2025-10-09",
        changes=[
            "Sistema de autenticación JWT mejorado",
            "88 instituciones UAGro en el backend",
            "Panel de administración con autocompletado inteligente",
            "Sistema de permisos granular por rol",
            "Auditoría completa de acciones de usuarios"
        ]
    ),
    ChangelogEntry(
        version="2.0.0",
        date="2025-10-08",
        changes=[
            "Sistema de autenticación JWT completo",
            "Modo híbrido online/offline",
            "Sincronización automática de datos",
            "Cache local con SQLite",
            "Gestión de sesiones segura"
        ]
    )
]

# =====================================================================
# UTILIDADES
# =====================================================================

def parse_version(version_str: str) -> tuple:
    """Convierte string de versión a tupla para comparación"""
    try:
        parts = version_str.split('.')
        return tuple(int(p) for p in parts[:3])  # Solo major.minor.patch
    except Exception:
        return (0, 0, 0)

def compare_versions(v1: str, v2: str) -> int:
    """
    Compara dos versiones.
    Retorna: 1 si v1 > v2, -1 si v1 < v2, 0 si son iguales
    """
    v1_tuple = parse_version(v1)
    v2_tuple = parse_version(v2)
    
    if v1_tuple > v2_tuple:
        return 1
    elif v1_tuple < v2_tuple:
        return -1
    else:
        return 0

# =====================================================================
# ENDPOINTS
# =====================================================================

@router.post("/check", response_model=UpdateCheckResponse)
async def check_for_updates(request: UpdateCheckRequest):
    """
    Verifica si hay actualizaciones disponibles para el cliente.
    
    - Compara la versión actual del cliente con la última disponible
    - Retorna información de la actualización si está disponible
    - Indica si la actualización es obligatoria
    """
    try:
        # Comparar versiones
        comparison = compare_versions(LATEST_VERSION.version, request.current_version)
        
        if comparison > 0:
            # Hay una versión más nueva disponible
            return UpdateCheckResponse(
                update_available=True,
                current_version=request.current_version,
                latest_version=LATEST_VERSION,
                message=f"Nueva versión {LATEST_VERSION.version} disponible. "
                        f"{'Actualización obligatoria.' if LATEST_VERSION.is_mandatory else 'Se recomienda actualizar.'}"
            )
        else:
            # El cliente está actualizado
            return UpdateCheckResponse(
                update_available=False,
                current_version=request.current_version,
                latest_version=None,
                message="Tu aplicación está actualizada."
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al verificar actualizaciones: {str(e)}"
        )

@router.get("/latest", response_model=VersionInfo)
async def get_latest_version():
    """
    Obtiene información de la última versión disponible.
    
    - No requiere información del cliente
    - Útil para mostrar info sin comparar versiones
    - Retorna toda la información de la versión más reciente
    """
    return LATEST_VERSION

@router.get("/changelog", response_model=ChangelogResponse)
async def get_changelog(
    version: Optional[str] = None,
    limit: Optional[int] = None
):
    """
    Obtiene el historial de versiones (changelog).
    
    Parámetros:
    - version: Si se especifica, retorna solo esa versión
    - limit: Limita el número de versiones a retornar (más recientes primero)
    
    Si no se especifica ningún parámetro, retorna todas las versiones.
    """
    try:
        if version:
            # Buscar versión específica
            matching = [v for v in VERSION_HISTORY if v.version == version]
            if not matching:
                raise HTTPException(
                    status_code=404,
                    detail=f"Versión {version} no encontrada en el historial"
                )
            return ChangelogResponse(
                total_versions=1,
                versions=matching
            )
        
        # Retornar todas o limitadas
        versions_to_return = VERSION_HISTORY
        if limit and limit > 0:
            versions_to_return = VERSION_HISTORY[:limit]
        
        return ChangelogResponse(
            total_versions=len(versions_to_return),
            versions=versions_to_return
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener changelog: {str(e)}"
        )

@router.get("/health")
async def update_service_health():
    """
    Endpoint de salud para el servicio de actualizaciones.
    Útil para monitoreo y diagnóstico.
    """
    return {
        "status": "healthy",
        "service": "updates",
        "latest_version": LATEST_VERSION.version,
        "total_versions": len(VERSION_HISTORY)
    }
