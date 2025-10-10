# temp_backend/auth_models.py
"""
Modelos de datos para el sistema de autenticación y autorización.
Incluye usuarios, roles, permisos y auditoría.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Definición de roles disponibles en el sistema
class UserRole(str, Enum):
    ADMIN = "admin"                    # Control total del sistema
    MEDICO = "medico"                  # Médicos generales
    NUTRICION = "nutricion"            # Nutriólogos
    PSICOLOGIA = "psicologia"          # Psicólogos
    ODONTOLOGIA = "odontologia"        # Odontólogos
    ENFERMERIA = "enfermeria"          # Personal de enfermería
    RECEPCION = "recepcion"            # Personal de recepción/citas
    LECTURA = "lectura"                # Solo lectura (reportes/estadísticas)

# Campus disponibles
class Campus(str, Enum):
    LLANO_LARGO = "llano-largo"
    ACAPULCO = "acapulco"
    CHILPANCINGO = "chilpancingo"
    TAXCO = "taxco"
    IGUALA = "iguala"
    ZIHUATANEJO = "zihuatanejo"

# Modelo para crear un nuevo usuario
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Nombre de usuario único")
    email: EmailStr = Field(..., description="Correo electrónico institucional")
    password: str = Field(..., min_length=8, description="Contraseña (mínimo 8 caracteres)")
    nombre_completo: str = Field(..., min_length=3, description="Nombre completo del usuario")
    rol: UserRole = Field(..., description="Rol del usuario en el sistema")
    campus: Campus = Field(..., description="Campus al que pertenece")
    departamento: str = Field(..., description="Departamento o área de trabajo")

# Modelo de usuario en la base de datos
class UserInDB(BaseModel):
    id: str = Field(..., description="ID único: user:{username}@{campus}")
    username: str
    email: str
    password_hash: str  # Contraseña hasheada con bcrypt
    nombre_completo: str
    rol: UserRole
    campus: Campus
    departamento: str
    activo: bool = True
    fecha_creacion: str  # ISO 8601 timestamp
    ultimo_acceso: Optional[str] = None
    intentos_fallidos: int = 0
    bloqueado_hasta: Optional[str] = None

# Modelo de respuesta (sin contraseña)
class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    nombre_completo: str
    rol: UserRole
    campus: Campus
    departamento: str
    activo: bool
    fecha_creacion: str
    ultimo_acceso: Optional[str] = None

# Modelo para login
class LoginRequest(BaseModel):
    username: str = Field(..., description="Usuario o email")
    password: str = Field(..., description="Contraseña")
    campus: Optional[Campus] = None  # Opcional, se puede inferir

# Modelo de token JWT
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Modelo de datos del token (payload)
class TokenData(BaseModel):
    username: str
    rol: UserRole
    campus: Campus
    exp: Optional[datetime] = None

# Modelo para actualizar usuario
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nombre_completo: Optional[str] = None
    rol: Optional[UserRole] = None
    departamento: Optional[str] = None
    activo: Optional[bool] = None

# Modelo para cambiar contraseña
class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)

# Modelo de auditoría
class AuditAction(str, Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    CREATE_CARNET = "CREATE_CARNET"
    UPDATE_CARNET = "UPDATE_CARNET"
    VIEW_CARNET = "VIEW_CARNET"
    CREATE_NOTA = "CREATE_NOTA"
    UPDATE_NOTA = "UPDATE_NOTA"
    VIEW_NOTA = "VIEW_NOTA"
    CREATE_CITA = "CREATE_CITA"
    UPDATE_CITA = "UPDATE_CITA"
    DELETE_CITA = "DELETE_CITA"
    CREATE_PROMOCION = "CREATE_PROMOCION"
    CREATE_VACCINATION = "CREATE_VACCINATION"
    CREATE_USER = "CREATE_USER"
    UPDATE_USER = "UPDATE_USER"
    DELETE_USER = "DELETE_USER"

class AuditLog(BaseModel):
    id: str  # audit:{timestamp}-{random}
    usuario: str  # username@campus
    accion: AuditAction
    recurso: Optional[str] = None  # ID del recurso afectado
    detalles: Optional[str] = None
    timestamp: str  # ISO 8601
    ip: Optional[str] = None
    user_agent: Optional[str] = None

# Permisos por rol (definición de políticas)
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        "users:create", "users:read", "users:update", "users:delete",
        "carnets:create", "carnets:read", "carnets:update", "carnets:delete",
        "notas:create", "notas:read", "notas:update", "notas:delete",
        "citas:create", "citas:read", "citas:update", "citas:delete",
        "promociones:create", "promociones:read",
        "vaccination:create", "vaccination:read", "vaccination:update",
        "audit:read", "reports:read"
    ],
    UserRole.MEDICO: [
        "carnets:create", "carnets:read", "carnets:update",
        "notas:create", "notas:read", "notas:update",
        "citas:create", "citas:read", "citas:update",
        "promociones:read",
        "vaccination:read"
    ],
    UserRole.NUTRICION: [
        "carnets:read",
        "notas:create", "notas:read", "notas:update",  # Solo de nutrición
        "citas:create", "citas:read",
        "promociones:read"
    ],
    UserRole.PSICOLOGIA: [
        "carnets:read",
        "notas:create", "notas:read", "notas:update",  # Solo de psicología
        "citas:create", "citas:read",
        "promociones:read"
    ],
    UserRole.ODONTOLOGIA: [
        "carnets:read",
        "notas:create", "notas:read", "notas:update",  # Solo de odontología
        "citas:create", "citas:read",
        "promociones:read"
    ],
    UserRole.ENFERMERIA: [
        "carnets:read",
        "notas:read",
        "citas:read",
        "vaccination:read"
    ],
    UserRole.RECEPCION: [
        "carnets:read",
        "citas:create", "citas:read", "citas:update"
    ],
    UserRole.LECTURA: [
        "carnets:read",
        "notas:read",
        "citas:read",
        "reports:read"
    ]
}

def has_permission(rol: UserRole, permission: str) -> bool:
    """Verifica si un rol tiene un permiso específico."""
    return permission in ROLE_PERMISSIONS.get(rol, [])
