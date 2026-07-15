from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TenantStatus(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    DISABLED = "disabled"


class Tenant(BaseModel):
    id: str
    code: str
    name: str
    status: TenantStatus
    plan: str = "standard"
    license_expires_at: Optional[datetime] = None
    student_limit: Optional[int] = None
    user_limit: Optional[int] = None
    enabled_modules: List[str] = Field(default_factory=list)
    branding: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_login_enabled(self, now: Optional[datetime] = None) -> bool:
        if self.status not in {TenantStatus.TRIAL, TenantStatus.ACTIVE}:
            return False
        if self.license_expires_at is None:
            return True
        current = now or datetime.now(timezone.utc)
        expires_at = self.license_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at > current


class TenantContext(BaseModel):
    tenant_id: str
    user_id: str
    roles: List[str]
    permissions: List[str]
    session_id: str
    correlation_id: Optional[str] = None

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions


class InstitutionalLoginRequest(BaseModel):
    institution_code: str
    username: str
    password: str


class MultitenantUser(BaseModel):
    id: str
    tenant_id: str
    username: str
    password_hash: str
    active: bool = True
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    session_version: int = 1


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    user_id: str
    roles: List[str]
    permissions: List[str]


class AuditEvent(BaseModel):
    tenant_id: Optional[str]
    actor_user_id: Optional[str]
    session_id: Optional[str]
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    occurred_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    result: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    correlation_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


PLATFORM_ROLES = {
    "platform_superadmin",
    "tenant_admin",
    "medical_staff",
    "psychology_staff",
    "nutrition_staff",
    "dentistry_staff",
    "student_services",
    "auditor",
}

INITIAL_PERMISSIONS = {
    "tenants.manage",
    "users.manage",
    "students.read",
    "students.write",
    "medical_records.read",
    "medical_records.write",
    "psychology_records.read",
    "psychology_records.write",
    "nutrition_records.read",
    "nutrition_records.write",
    "appointments.read",
    "appointments.write",
    "audit.read",
}

ROLE_PERMISSIONS = {
    "platform_superadmin": sorted(INITIAL_PERMISSIONS),
    "tenant_admin": [
        "users.manage",
        "students.read",
        "students.write",
        "medical_records.read",
        "appointments.read",
        "appointments.write",
        "audit.read",
    ],
    "medical_staff": [
        "students.read",
        "medical_records.read",
        "medical_records.write",
        "appointments.read",
        "appointments.write",
    ],
    "psychology_staff": [
        "students.read",
        "psychology_records.read",
        "psychology_records.write",
        "appointments.read",
    ],
    "nutrition_staff": [
        "students.read",
        "nutrition_records.read",
        "nutrition_records.write",
        "appointments.read",
    ],
    "dentistry_staff": ["students.read", "appointments.read", "appointments.write"],
    "student_services": ["students.read", "students.write", "appointments.read"],
    "auditor": ["students.read", "audit.read"],
}


SENSITIVE_AUDIT_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "authorization",
    "clinical_notes",
    "expediente",
    "cuerpo",
    "nota",
}


def permissions_for_roles(roles: List[str], explicit_permissions: Optional[List[str]] = None) -> List[str]:
    permissions = set(explicit_permissions or [])
    for role in roles:
        permissions.update(ROLE_PERMISSIONS.get(role, []))
    return sorted(permissions)


def sanitize_audit_details(details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in (details or {}).items():
        if key.lower() in SENSITIVE_AUDIT_KEYS:
            sanitized[key] = "[redacted]"
        else:
            sanitized[key] = value
    return sanitized
