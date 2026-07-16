from __future__ import annotations

import argparse
import json
import os
import secrets
import string
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional, TextIO

from multitenancy_auth import hash_password, validate_password_strength
from multitenancy_models import MultitenantUser, Tenant, TenantStatus
from multitenancy_repositories import (
    CosmosTenantAwareStudentRepository,
    CosmosTenantRepository,
    CosmosUserRepository,
    TenantAwareStudentRepository,
    TenantRepository,
    UserRepository,
)
from multitenancy_staging_config import DEFAULT_STAGING_DATABASE, StagingConfigurationError, load_staging_settings


@dataclass(frozen=True)
class ContainerDefinition:
    name: str
    partition_key: str


MULTITENANT_CONTAINERS: List[ContainerDefinition] = [
    ContainerDefinition("tenants_v2", "/id"),
    ContainerDefinition("users_v2", "/tenant_id"),
    ContainerDefinition("students_v2", "/tenant_id"),
    ContainerDefinition("clinical_records_v2", "/tenant_student_key"),
    ContainerDefinition("appointments_v2", "/tenant_id"),
    ContainerDefinition("referrals_v2", "/tenant_id"),
    ContainerDefinition("audit_logs_v2", "/tenant_month_key"),
    ContainerDefinition("licenses_v2", "/tenant_id"),
]


LOYOLA_TENANT_ID = "loyola-demo"
LOYOLA_TENANT_CODE = "LOYOLA-DEMO-2026"
LOYOLA_ADMIN_USERNAME = "admin.loyola"
LOYOLA_ADMIN_USER_ID = "loyola-demo-admin-loyola"


def build_loyola_tenant(now: Optional[datetime] = None) -> Tenant:
    timestamp = now or datetime.now(timezone.utc)
    return Tenant(
        id=LOYOLA_TENANT_ID,
        code=LOYOLA_TENANT_CODE,
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
        created_at=timestamp,
        updated_at=timestamp,
    )


def build_loyola_students() -> list[dict]:
    return [
        {
            "id": "loyola-demo-student-ficticio-001",
            "tenant_id": LOYOLA_TENANT_ID,
            "matricula": "LOY-FICT-001",
            "nombre": "Alumno Ficticio Loyola Uno",
            "clinical_summary": "Registro simulado para demo LOYOLA",
            "demo": True,
        },
        {
            "id": "loyola-demo-student-ficticio-002",
            "tenant_id": LOYOLA_TENANT_ID,
            "matricula": "LOY-FICT-002",
            "nombre": "Alumno Ficticio Loyola Dos",
            "clinical_summary": "Registro simulado sin datos reales",
            "demo": True,
        },
    ]


def generate_temporary_password(length: int = 18) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%*-_"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        ok, _ = validate_password_strength(password)
        if ok and len(password) >= 12:
            return password


def validate_apply_environment(env: Optional[dict] = None) -> None:
    source = env or os.environ
    if source.get("COSMOS_DATABASE_NAME", "").strip().lower() == "sasu":
        raise StagingConfigurationError("Refusing to use production database SASU")
    settings = load_staging_settings(env)
    if settings.cosmos_database_name != DEFAULT_STAGING_DATABASE:
        raise StagingConfigurationError("COSMOS_DATABASE_NAME must be sasu_multitenant_staging")
    if not settings.enable_multitenant_routes:
        raise StagingConfigurationError("ENABLE_MULTITENANT_ROUTES must be true")
    if settings.enable_legacy_routes:
        raise StagingConfigurationError("ENABLE_LEGACY_ROUTES must be false")
    if settings.allow_production_database:
        raise StagingConfigurationError("ALLOW_PRODUCTION_DATABASE must be false")


def _safe_plan_payload() -> dict:
    return {
        "tenant": {
            "id": LOYOLA_TENANT_ID,
            "code": LOYOLA_TENANT_CODE,
            "name": "LOYOLA",
            "status": "trial",
            "plan": "demo",
            "enabled_modules": ["students", "appointments", "audit"],
            "branding": "demo institucional",
        },
        "user": {
            "id": LOYOLA_ADMIN_USER_ID,
            "tenant_id": LOYOLA_TENANT_ID,
            "username": LOYOLA_ADMIN_USERNAME,
            "roles": ["tenant_admin"],
            "active": True,
            "temporary_password": True,
            "must_change_password": True,
            "password": "generated-on-apply",
        },
        "students": [student["id"] for student in build_loyola_students()],
        "database": DEFAULT_STAGING_DATABASE,
    }


def _write_json(output: TextIO, payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True), file=output)


def _upsert_tenant(repo: TenantRepository, tenant: Tenant) -> str:
    existing = repo.get_by_id(tenant.id)
    if existing:
        tenant.created_at = existing.created_at
        tenant.updated_at = datetime.now(timezone.utc)
        repo.update(tenant)
        return "updated"
    repo.create(tenant)
    return "created"


def _upsert_user(repo: UserRepository, password: str) -> tuple[str, bool]:
    existing = repo.get_by_id(LOYOLA_TENANT_ID, LOYOLA_ADMIN_USER_ID)
    if existing:
        user = existing.model_copy(
            update={
                "tenant_id": LOYOLA_TENANT_ID,
                "username": LOYOLA_ADMIN_USERNAME,
                "roles": ["tenant_admin"],
                "active": True,
            }
        )
        repo.update(user)
        return "updated", False

    user = MultitenantUser(
        id=LOYOLA_ADMIN_USER_ID,
        tenant_id=LOYOLA_TENANT_ID,
        username=LOYOLA_ADMIN_USERNAME,
        password_hash=hash_password(password),
        roles=["tenant_admin"],
        active=True,
        temporary_password=True,
    )
    repo.create(user)
    return "created", True


def _upsert_students(repo: TenantAwareStudentRepository, students: Iterable[dict]) -> list[dict]:
    results = []
    for student in students:
        existing = repo.get_student(LOYOLA_TENANT_ID, student["id"])
        if existing:
            repo.update_student(LOYOLA_TENANT_ID, student["id"], student)
            results.append({"id": student["id"], "status": "updated"})
        else:
            repo.create_student(LOYOLA_TENANT_ID, student)
            results.append({"id": student["id"], "status": "created"})
    return results


def provision_loyola_demo(
    *,
    apply: bool = False,
    tenant_repo: Optional[TenantRepository] = None,
    user_repo: Optional[UserRepository] = None,
    students_repo: Optional[TenantAwareStudentRepository] = None,
    env: Optional[dict] = None,
    output: TextIO = sys.stdout,
) -> dict:
    if not apply:
        payload = {"mode": "dry-run", "action": "loyola-demo", "payload": _safe_plan_payload()}
        _write_json(output, payload)
        print("Dry-run only. Re-run with --apply in staging after reviewing the plan.", file=output)
        return payload

    validate_apply_environment(env)
    tenant_repo = tenant_repo or CosmosTenantRepository()
    user_repo = user_repo or CosmosUserRepository()
    students_repo = students_repo or CosmosTenantAwareStudentRepository()

    temporary_password = generate_temporary_password()
    tenant_status = _upsert_tenant(tenant_repo, build_loyola_tenant())
    user_status, password_created = _upsert_user(user_repo, temporary_password)
    student_results = _upsert_students(students_repo, build_loyola_students())

    payload = {
        "mode": "apply",
        "action": "loyola-demo",
        "database": DEFAULT_STAGING_DATABASE,
        "tenant": {"id": LOYOLA_TENANT_ID, "status": tenant_status},
        "user": {
            "id": LOYOLA_ADMIN_USER_ID,
            "tenant_id": LOYOLA_TENANT_ID,
            "username": LOYOLA_ADMIN_USERNAME,
            "status": user_status,
            "temporary_password_created": password_created,
        },
        "students": student_results,
    }
    _write_json(output, payload)
    if password_created:
        print(f"TEMPORARY_PASSWORD_ONE_TIME={temporary_password}", file=output)
    return payload


def reset_loyola_password(
    *,
    apply: bool = False,
    user_repo: Optional[UserRepository] = None,
    env: Optional[dict] = None,
    output: TextIO = sys.stdout,
) -> dict:
    if not apply:
        payload = {
            "action": "reset temporary password",
            "base": DEFAULT_STAGING_DATABASE,
            "mode": "dry-run",
            "tenant_id": LOYOLA_TENANT_ID,
            "username": LOYOLA_ADMIN_USERNAME,
        }
        _write_json(output, payload)
        return payload

    validate_apply_environment(env)
    user_repo = user_repo or CosmosUserRepository()
    user = user_repo.get_by_id(LOYOLA_TENANT_ID, LOYOLA_ADMIN_USER_ID)
    if not user:
        raise RuntimeError("LOYOLA user not found; refusing to create a replacement user")
    if user.tenant_id != LOYOLA_TENANT_ID or user.id != LOYOLA_ADMIN_USER_ID:
        raise RuntimeError("Resolved user does not match the LOYOLA admin identity")
    if user.username.strip().lower() != LOYOLA_ADMIN_USERNAME:
        raise RuntimeError("Resolved user username does not match admin.loyola")
    username_user = user_repo.get_by_username(LOYOLA_TENANT_ID, LOYOLA_ADMIN_USERNAME)
    if not username_user or username_user.id != LOYOLA_ADMIN_USER_ID:
        raise RuntimeError("LOYOLA username lookup does not match the expected user")

    temporary_password = generate_temporary_password(18)
    ok, message = validate_password_strength(temporary_password)
    if not ok:
        raise RuntimeError(message)

    updated_user = user.model_copy(
        update={
            "password_hash": hash_password(temporary_password),
            "temporary_password": True,
            "password_changed_at": None,
            "session_version": user.session_version + 1,
            "failed_login_attempts": 0,
            "locked_until": None,
            "active": True,
        }
    )
    user_repo.update(updated_user)

    payload = {
        "mode": "apply",
        "action": "reset-loyola-password",
        "database": DEFAULT_STAGING_DATABASE,
        "tenant_id": LOYOLA_TENANT_ID,
        "username": LOYOLA_ADMIN_USERNAME,
        "status": "password-reset",
        "temporary_password_created": True,
        "sessions_revoked": True,
    }
    _write_json(output, payload)
    print(f"TEMPORARY_PASSWORD_ONE_TIME={temporary_password}", file=output)
    return payload


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="SASU multitenant staging provisioning CLI")
    parser.add_argument(
        "scenario",
        choices=["loyola-demo", "reset-loyola-password"],
        help="Provisioning scenario to plan or apply",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Print the provisioning plan without writing")
    mode.add_argument("--apply", action="store_true", help="Apply the provisioning plan to Cosmos staging")
    args = parser.parse_args(argv)

    if args.scenario == "reset-loyola-password":
        reset_loyola_password(apply=bool(args.apply))
    else:
        provision_loyola_demo(apply=bool(args.apply))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
