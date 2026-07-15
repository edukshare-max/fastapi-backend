from __future__ import annotations

import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from auth_service import ALGORITHM, AuthService, SECRET_KEY
from multitenancy_audit import InMemoryAuditLogger
from multitenancy_models import (
    InstitutionalLoginRequest,
    MultitenantUser,
    TenantContext,
    TokenResponse,
    permissions_for_roles,
)
from multitenancy_repositories import TenantRepository, UserRepository


GENERIC_LOGIN_ERROR = "Credenciales invalidas"
MULTITENANT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("MULTITENANT_ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


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

    def login(
        self,
        payload: InstitutionalLoginRequest,
        *,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> TokenResponse:
        tenant = self.tenants.get_by_code(payload.institution_code)
        user: Optional[MultitenantUser] = None
        if tenant and tenant.is_login_enabled():
            user = self.users.get_by_username(tenant.id, payload.username)

        if not tenant or not tenant.is_login_enabled() or not user:
            self._audit_failed_login(None, None, ip_address, user_agent, correlation_id)
            raise self._invalid_credentials()

        if not AuthService.verify_password(payload.password, user.password_hash):
            self._audit_failed_login(tenant.id, None, ip_address, user_agent, correlation_id)
            raise self._invalid_credentials()

        if not user.active:
            self._audit_failed_login(tenant.id, user.id, ip_address, user_agent, correlation_id)
            raise self._invalid_credentials()

        session_id = str(uuid.uuid4())
        permissions = permissions_for_roles(user.roles, user.permissions)
        token = self.create_token(
            user=user,
            roles=user.roles,
            permissions=permissions,
            session_id=session_id,
        )
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
            tenant_id=tenant.id,
            user_id=user.id,
            roles=user.roles,
            permissions=permissions,
        )

    def create_token(
        self,
        *,
        user: MultitenantUser,
        roles: list[str],
        permissions: list[str],
        session_id: Optional[str] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=MULTITENANT_ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        payload = {
            "sub": user.id,
            "tenant_id": user.tenant_id,
            "roles": roles,
            "permissions": permissions,
            "session_id": session_id or str(uuid.uuid4()),
            "session_version": user.session_version,
            "exp": expire,
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

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
        permissions = payload.get("permissions") or []
        session_id = payload.get("session_id")
        if not user_id or not tenant_id or not session_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")

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

        return TenantContext(
            tenant_id=tenant_id,
            user_id=user_id,
            roles=list(roles),
            permissions=list(permissions),
            session_id=session_id,
            correlation_id=correlation_id,
        )

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
