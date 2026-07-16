from __future__ import annotations

import os
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from multitenancy_audit import InMemoryAuditLogger
from multitenancy_models import (
    ChangeTemporaryPasswordRequest,
    InstitutionalLoginRequest,
    MultitenantUser,
    RefreshTokenRequest,
    TenantContext,
    TokenResponse,
    effective_permissions_for_tenant,
)
from multitenancy_repositories import TenantRepository, UserRepository


SECRET_KEY = os.environ.get("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
GENERIC_LOGIN_ERROR = "Credenciales invalidas"
MULTITENANT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("MULTITENANT_ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "14"))
LOGIN_RATE_LIMIT = int(os.environ.get("LOGIN_RATE_LIMIT", "10"))
LOCKOUT_ATTEMPTS = int(os.environ.get("LOGIN_LOCKOUT_ATTEMPTS", "5"))
LOCKOUT_MINUTES = int(os.environ.get("LOGIN_LOCKOUT_MINUTES", "15"))
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__truncate_error=False)


def _truncate_bcrypt_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        return password_bytes[:72].decode("utf-8", errors="ignore")
    return password


def hash_password(password: str) -> str:
    return pwd_context.hash(_truncate_bcrypt_password(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_truncate_bcrypt_password(plain_password), hashed_password)


def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "La contrasena debe tener al menos 8 caracteres"
    if not any(char.isupper() for char in password):
        return False, "La contrasena debe contener al menos una mayuscula"
    if not any(char.islower() for char in password):
        return False, "La contrasena debe contener al menos una minuscula"
    if not any(char.isdigit() for char in password):
        return False, "La contrasena debe contener al menos un numero"
    return True, "Contrasena valida"


class InstitutionalAuthService:
    def __init__(
        self,
        tenants: TenantRepository,
        users: UserRepository,
        audit_logger: InMemoryAuditLogger,
    ):
        self.tenants = tenants
        self.users = users
        self.audit_logger = audit_logger
        self.refresh_tokens: dict[str, dict] = {}
        self.revoked_sessions: set[str] = set()
        self.login_attempts: dict[str, list[datetime]] = {}

    def login(
        self,
        payload: InstitutionalLoginRequest,
        *,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> TokenResponse:
        self._enforce_rate_limit(payload.institution_code, payload.username)
        tenant = self.tenants.get_by_code(payload.institution_code)
        user: Optional[MultitenantUser] = None
        if tenant and tenant.is_login_enabled():
            user = self.users.get_by_username(tenant.id, payload.username)

        if not tenant or not tenant.is_login_enabled() or not user:
            self._audit_failed_login(None, None, ip_address, user_agent, correlation_id)
            raise self._invalid_credentials()

        if self._is_user_locked(user):
            self._audit_failed_login(tenant.id, user.id, ip_address, user_agent, correlation_id)
            raise self._invalid_credentials()

        if not verify_password(payload.password, user.password_hash):
            self._register_failed_attempt(user)
            self._audit_failed_login(tenant.id, None, ip_address, user_agent, correlation_id)
            raise self._invalid_credentials()

        if not user.active:
            self._audit_failed_login(tenant.id, user.id, ip_address, user_agent, correlation_id)
            raise self._invalid_credentials()

        session_id = str(uuid.uuid4())
        permissions = effective_permissions_for_tenant(user.roles, user.permissions, tenant.enabled_modules)
        user.failed_login_attempts = 0
        user.locked_until = None
        self.users.save(user)
        token = self.create_token(
            user=user,
            roles=user.roles,
            permissions=permissions,
            modules=tenant.enabled_modules,
            session_id=session_id,
        )
        refresh_token = self.create_refresh_token(user=user, session_id=session_id)
        self.audit_logger.record(
            tenant_id=tenant.id,
            actor_user_id=user.id,
            session_id=session_id,
            action="login.success",
            result="success",
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
        )
        return TokenResponse(
            access_token=token,
            refresh_token=refresh_token,
            tenant_id=tenant.id,
            user_id=user.id,
            username=user.username,
            roles=user.roles,
            permissions=permissions,
            modules=tenant.enabled_modules,
            requires_password_change=user.temporary_password,
        )

    def create_token(
        self,
        *,
        user: MultitenantUser,
        roles: list[str],
        permissions: list[str],
        modules: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=MULTITENANT_ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        payload = {
            "sub": user.id,
            "tenant_id": user.tenant_id,
            "username": user.username,
            "roles": roles,
            "permissions": permissions,
            "modules": modules or [],
            "session_id": session_id or str(uuid.uuid4()),
            "session_version": user.session_version,
            "exp": expire,
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def create_refresh_token(self, *, user: MultitenantUser, session_id: str) -> str:
        raw_token = secrets.token_urlsafe(48)
        token_hash = self._hash_refresh_token(raw_token)
        self.refresh_tokens[token_hash] = {
            "tenant_id": user.tenant_id,
            "user_id": user.id,
            "session_id": session_id,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            "used": False,
        }
        return raw_token

    def refresh(self, payload: RefreshTokenRequest) -> TokenResponse:
        token_hash = self._hash_refresh_token(payload.refresh_token)
        record = self.refresh_tokens.get(token_hash)
        if not record or record.get("used"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalido")
        if record["expires_at"] <= datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expirado")
        if record["session_id"] in self.revoked_sessions:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesion revocada")

        user = self.users.get_by_id(record["tenant_id"], record["user_id"])
        tenant = self.tenants.get_by_id(record["tenant_id"])
        if not user or not user.active or not tenant or not tenant.is_login_enabled():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesion no autorizada")

        record["used"] = True
        permissions = effective_permissions_for_tenant(user.roles, user.permissions, tenant.enabled_modules)
        access_token = self.create_token(
            user=user,
            roles=user.roles,
            permissions=permissions,
            modules=tenant.enabled_modules,
            session_id=record["session_id"],
        )
        refresh_token = self.create_refresh_token(user=user, session_id=record["session_id"])
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            tenant_id=user.tenant_id,
            user_id=user.id,
            username=user.username,
            roles=user.roles,
            permissions=permissions,
            modules=tenant.enabled_modules,
            requires_password_change=user.temporary_password,
        )

    def logout(self, context: TenantContext) -> None:
        self.revoked_sessions.add(context.session_id)
        self.audit_logger.record(
            tenant_id=context.tenant_id,
            actor_user_id=context.user_id,
            session_id=context.session_id,
            action="logout",
            result="success",
        )

    def change_temporary_password(self, context: TenantContext, payload: ChangeTemporaryPasswordRequest) -> None:
        user = self.users.get_by_id(context.tenant_id, context.user_id)
        if not user or not user.active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no autorizado")
        if not user.temporary_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contrasena temporal ya fue cambiada")
        ok, message = validate_password_strength(payload.new_password)
        if not ok or len(payload.new_password) < 12:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        if not verify_password(payload.current_password, user.password_hash):
            raise self._invalid_credentials()
        user.password_hash = hash_password(payload.new_password)
        user.temporary_password = False
        user.password_changed_at = datetime.now(timezone.utc)
        user.session_version += 1
        self.revoked_sessions.add(context.session_id)
        self.users.save(user)

    def context_from_token(self, token: str, *, correlation_id: Optional[str] = None) -> TenantContext:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalido",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        roles = payload.get("roles") or []
        session_id = payload.get("session_id")
        if not user_id or not tenant_id or not session_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")
        if session_id in self.revoked_sessions:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesion revocada")

        tenant = self.tenants.get_by_id(tenant_id)
        if not tenant or not tenant.is_login_enabled():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta institucional no disponible")

        user = self.users.get_by_id(tenant_id, user_id)
        if not user or not user.active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no autorizado")

        if user.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")

        token_session_version = payload.get("session_version", user.session_version)
        if token_session_version != user.session_version:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesion revocada")
        permissions = effective_permissions_for_tenant(user.roles, user.permissions, tenant.enabled_modules)

        return TenantContext(
            tenant_id=tenant_id,
            user_id=user_id,
            username=user.username,
            roles=list(user.roles or roles),
            permissions=permissions,
            modules=list(tenant.enabled_modules),
            session_id=session_id,
            correlation_id=correlation_id,
        )

    def revoke_session(self, session_id: str) -> None:
        self.revoked_sessions.add(session_id)

    @staticmethod
    def _invalid_credentials() -> HTTPException:
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_LOGIN_ERROR)

    def _audit_failed_login(
        self,
        tenant_id: Optional[str],
        user_id: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
        correlation_id: Optional[str],
    ) -> None:
        self.audit_logger.record(
            tenant_id=tenant_id,
            actor_user_id=user_id,
            session_id=None,
            action="login.failed",
            result="failure",
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
            details={"reason": "invalid_credentials"},
        )

    def _enforce_rate_limit(self, institution_code: str, username: str) -> None:
        key = f"{institution_code.strip().upper()}:{username.strip().lower()}"
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=1)
        attempts = [item for item in self.login_attempts.get(key, []) if item >= window_start]
        attempts.append(now)
        self.login_attempts[key] = attempts
        if len(attempts) > LOGIN_RATE_LIMIT:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Demasiados intentos")

    @staticmethod
    def _hash_refresh_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_user_locked(user: MultitenantUser) -> bool:
        if user.locked_until is None:
            return False
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        return locked_until > datetime.now(timezone.utc)

    def _register_failed_attempt(self, user: MultitenantUser) -> None:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= LOCKOUT_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
        self.users.save(user)


def require_tenant_permission(permission: str):
    async def checker(context: TenantContext = Depends(get_current_tenant_context)) -> TenantContext:
        if not context.has_permission(permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permiso insuficiente")
        return context

    return checker


def get_multitenant_auth_service(request: Request) -> InstitutionalAuthService:
    service = getattr(request.app.state, "multitenant_auth_service", None)
    if service is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Multitenancy no configurado")
    return service


async def get_current_tenant_context(
    request: Request,
    token: str = Depends(oauth2_scheme),
    service: InstitutionalAuthService = Depends(get_multitenant_auth_service),
) -> TenantContext:
    correlation_id = request.headers.get("x-correlation-id") or secrets.token_hex(8)
    return service.context_from_token(token, correlation_id=correlation_id)
