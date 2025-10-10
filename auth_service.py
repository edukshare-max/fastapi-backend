# temp_backend/auth_service.py
"""
Servicio de autenticación y autorización.
Maneja JWT, hash de contraseñas, y validación de usuarios.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
import os
import secrets

from auth_models import UserInDB, TokenData, UserRole, Campus

# Configuración de seguridad
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 horas

# Contexto para hash de contraseñas (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme para obtener el token del header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class AuthService:
    """Servicio centralizado de autenticación."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hashea una contraseña con bcrypt."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifica una contraseña contra su hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Crea un token JWT con los datos del usuario."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> TokenData:
        """Decodifica y valida un token JWT."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            rol: str = payload.get("rol")
            campus: str = payload.get("campus")
            
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido: falta username",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return TokenData(
                username=username,
                rol=UserRole(rol),
                campus=Campus(campus)
            )
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token inválido: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def generate_user_id(username: str, campus: Campus) -> str:
        """Genera un ID único para el usuario."""
        return f"user:{username}@{campus.value}"
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """
        Valida la fortaleza de una contraseña.
        Retorna (es_válida, mensaje)
        """
        if len(password) < 8:
            return False, "La contraseña debe tener al menos 8 caracteres"
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        if not (has_upper and has_lower and has_digit):
            return False, "La contraseña debe contener mayúsculas, minúsculas y números"
        
        return True, "Contraseña válida"

# Función de dependencia para obtener el usuario actual
async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    Dependencia de FastAPI para obtener el usuario actual desde el token JWT.
    Uso: @app.get("/protected") async def protected(user: TokenData = Depends(get_current_user))
    """
    return AuthService.decode_token(token)

# Función de dependencia para verificar roles
def require_role(*allowed_roles: UserRole):
    """
    Decorator de dependencia para verificar que el usuario tenga un rol permitido.
    
    Uso:
    @app.get("/admin-only", dependencies=[Depends(require_role(UserRole.ADMIN))])
    async def admin_only():
        return {"message": "Solo admins"}
    """
    async def role_checker(current_user: TokenData = Depends(get_current_user)):
        if current_user.rol not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes permisos. Se requiere rol: {[r.value for r in allowed_roles]}"
            )
        return current_user
    
    return role_checker

# Función de dependencia para verificar permisos específicos
def require_permission(permission: str):
    """
    Decorator de dependencia para verificar que el usuario tenga un permiso específico.
    
    Uso:
    @app.post("/carnets", dependencies=[Depends(require_permission("carnets:create"))])
    async def create_carnet():
        return {"message": "Carnet creado"}
    """
    from auth_models import has_permission
    
    async def permission_checker(current_user: TokenData = Depends(get_current_user)):
        if not has_permission(current_user.rol, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes el permiso: {permission}"
            )
        return current_user
    
    return permission_checker

# Constantes de configuración
MAX_LOGIN_ATTEMPTS = 5  # Máximo de intentos fallidos antes de bloquear
LOCKOUT_DURATION_MINUTES = 30  # Duración del bloqueo en minutos

def is_user_locked(user: UserInDB) -> bool:
    """Verifica si un usuario está bloqueado por intentos fallidos."""
    if user.bloqueado_hasta is None:
        return False
    
    try:
        lockout_time = datetime.fromisoformat(user.bloqueado_hasta)
        return datetime.utcnow() < lockout_time
    except (ValueError, TypeError):
        return False

def should_lock_user(user: UserInDB) -> bool:
    """Determina si un usuario debe ser bloqueado por intentos fallidos."""
    return user.intentos_fallidos >= MAX_LOGIN_ATTEMPTS

def calculate_lockout_time() -> str:
    """Calcula el tiempo hasta el cual el usuario estará bloqueado."""
    lockout_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    return lockout_until.isoformat()

print("✅ AuthService inicializado correctamente")
print(f"🔐 Algoritmo: {ALGORITHM}, Expiración: {ACCESS_TOKEN_EXPIRE_MINUTES} minutos")
