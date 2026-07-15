from __future__ import annotations

from multitenancy_models import MultitenantUser, Tenant, TenantStatus
from multitenancy_repositories import (
    InMemoryTenantAwareStudentRepository,
    InMemoryTenantRepository,
    InMemoryUserRepository,
)


def build_staging_tenants() -> InMemoryTenantRepository:
    return InMemoryTenantRepository(
        [
            Tenant(
                id="cres-staging",
                code="CRES-STAGING-2026",
                name="CRES - Entorno de pruebas",
                status=TenantStatus.ACTIVE,
                plan="internal-testing",
                enabled_modules=["students", "appointments", "audit"],
                branding={
                    "primary_color": "#0B5CAB",
                    "secondary_color": "#1E8F5A",
                    "logo_url": "embedded://cres-staging",
                    "subtitle": "Entorno de pruebas",
                },
            ),
            Tenant(
                id="loyola-demo",
                code="LOYOLA-DEMO-2026",
                name="LOYOLA",
                status=TenantStatus.TRIAL,
                plan="demo",
                enabled_modules=["students", "appointments", "audit"],
                branding={
                    "primary_color": "#164E8A",
                    "secondary_color": "#D8A21B",
                    "logo_url": "embedded://loyola-demo",
                    "subtitle": "Demo institucional",
                    "demo": True,
                },
            ),
        ]
    )


def build_staging_users(password_hash: str | None = None) -> InMemoryUserRepository:
    if password_hash is None:
        password_hash = "SET_WITH_PROVISIONING_CLI"
    return InMemoryUserRepository(
        [
            MultitenantUser(
                id="cres-admin-demo",
                tenant_id="cres-staging",
                username="admin.cres",
                password_hash=password_hash,
                roles=["tenant_admin"],
                temporary_password=True,
            ),
            MultitenantUser(
                id="loyola-admin-demo",
                tenant_id="loyola-demo",
                username="admin.loyola",
                password_hash=password_hash,
                roles=["tenant_admin"],
                temporary_password=True,
            ),
            MultitenantUser(
                id="loyola-medica-demo",
                tenant_id="loyola-demo",
                username="medica.loyola",
                password_hash=password_hash,
                roles=["medical_staff"],
            ),
        ]
    )


def build_staging_students() -> InMemoryTenantAwareStudentRepository:
    return InMemoryTenantAwareStudentRepository(
        [
            {
                "id": "cres-staging-student-001",
                "tenant_id": "cres-staging",
                "matricula": "STG-001",
                "nombre": "Paciente Ficticio CRES Uno",
                "clinical_summary": "Expediente simulado CRES",
            },
            {
                "id": "loyola-demo-student-001",
                "tenant_id": "loyola-demo",
                "matricula": "STG-001",
                "nombre": "Paciente Ficticio Loyola Uno",
                "clinical_summary": "Expediente simulado LOYOLA",
            },
            {
                "id": "loyola-demo-student-002",
                "tenant_id": "loyola-demo",
                "matricula": "LOY-002",
                "nombre": "Paciente Ficticio Loyola Dos",
                "clinical_summary": "Consulta nutricional simulada",
            },
        ]
    )
