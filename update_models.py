# temp_backend/update_models.py
"""
Modelos de datos para el sistema de actualizaciones automáticas.
Gestiona versiones, changelog y distribución de actualizaciones.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class VersionInfo(BaseModel):
    """Información de una versión específica de la aplicación"""
    version: str = Field(..., description="Número de versión semántico (ej: 2.3.2)")
    build_number: int = Field(..., description="Número de build incremental")
    release_date: str = Field(..., description="Fecha de lanzamiento (YYYY-MM-DD)")
    channel: str = Field(default="stable", description="Canal de distribución (stable, beta, dev)")
    download_url: str = Field(..., description="URL para descargar el instalador")
    file_size: Optional[int] = Field(None, description="Tamaño del archivo en bytes")
    checksum: Optional[str] = Field(None, description="SHA256 checksum del instalador")
    minimum_version: Optional[str] = Field(None, description="Versión mínima requerida para actualizar")
    is_mandatory: bool = Field(default=False, description="¿Es obligatoria esta actualización?")
    changelog: List[str] = Field(default_factory=list, description="Lista de cambios en esta versión")

class UpdateCheckRequest(BaseModel):
    """Request para verificar si hay actualizaciones disponibles"""
    current_version: str = Field(..., description="Versión actual del cliente")
    current_build: Optional[int] = Field(None, description="Build number actual del cliente")
    platform: str = Field(default="windows", description="Plataforma del cliente (windows, android, etc)")

class UpdateCheckResponse(BaseModel):
    """Response con información de actualización disponible"""
    update_available: bool = Field(..., description="¿Hay actualización disponible?")
    current_version: str = Field(..., description="Versión actual del cliente")
    latest_version: Optional[VersionInfo] = Field(None, description="Info de la última versión disponible")
    message: str = Field(..., description="Mensaje informativo")

class ChangelogEntry(BaseModel):
    """Entrada individual del changelog"""
    version: str
    date: str
    changes: List[str]

class ChangelogResponse(BaseModel):
    """Response con historial de versiones"""
    total_versions: int = Field(..., description="Total de versiones en el historial")
    versions: List[ChangelogEntry] = Field(..., description="Lista de versiones con sus cambios")
