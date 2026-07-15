from __future__ import annotations

import argparse
import importlib.metadata
import json
import secrets
import string
from dataclasses import dataclass
from typing import List

from auth_service import AuthService


@dataclass(frozen=True)
class ContainerDefinition:
    name: str
    partition_key: str
    hierarchical_partition_key: bool = False


MULTITENANT_CONTAINERS: List[ContainerDefinition] = [
    ContainerDefinition("tenants_v2", "/id"),
    ContainerDefinition("users_v2", "/tenant_id"),
    ContainerDefinition("students_v2", "/tenant_id"),
    ContainerDefinition("clinical_records_v2", "/tenant_id/student_id/id", True),
    ContainerDefinition("appointments_v2", "/tenant_id"),
    ContainerDefinition("referrals_v2", "/tenant_id"),
    ContainerDefinition("audit_logs_v2", "/tenant_id/month/id", True),
    ContainerDefinition("licenses_v2", "/tenant_id"),
]


STAGING_TENANTS = [
    {
        "id": "cres",
        "code": "CRES-INTERNAL",
        "name": "CRES",
        "status": "active",
        "plan": "internal",
    },
    {
        "id": "loyola",
        "code": "LOYOLA-DEMO-2026",
        "name": "LOYOLA",
        "status": "trial",
        "plan": "demo",
    },
]


def generate_temporary_password(length: int = 18) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%*-_"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        ok, _ = AuthService.validate_password_strength(password)
        if ok and len(password) >= 12:
            return password


def azure_cosmos_supports_hierarchical_partition_keys() -> bool:
    try:
        version = importlib.metadata.version("azure-cosmos")
    except importlib.metadata.PackageNotFoundError:
        return False
    major, minor, *_ = [int(part) for part in version.split(".") if part.isdigit()]
    return (major, minor) >= (4, 4)


def _print_plan(action: str, payload: dict, apply: bool) -> None:
    safe_payload = dict(payload)
    safe_payload.pop("temporary_password", None)
    safe_payload.pop("temporary_password_hash", None)
    print(json.dumps({"mode": "apply" if apply else "dry-run", "action": action, "payload": safe_payload}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="SASU multitenant staging provisioning CLI")
    parser.add_argument("--apply", action="store_true", help="Apply the requested staging change")
    sub = parser.add_subparsers(dest="resource", required=True)

    tenant = sub.add_parser("tenant")
    tenant_sub = tenant.add_subparsers(dest="action", required=True)
    tenant_create = tenant_sub.add_parser("create")
    tenant_create.add_argument("--id", required=True)
    tenant_create.add_argument("--code", required=True)
    tenant_create.add_argument("--name", required=True)
    tenant_create.add_argument("--plan", default="demo")
    tenant_create.add_argument("--status", default="trial")
    tenant_sub.add_parser("list")
    tenant_suspend = tenant_sub.add_parser("suspend")
    tenant_suspend.add_argument("--id", required=True)
    tenant_activate = tenant_sub.add_parser("activate")
    tenant_activate.add_argument("--id", required=True)
    tenant_branding = tenant_sub.add_parser("branding")
    tenant_branding.add_argument("--id", required=True)
    tenant_branding.add_argument("--primary-color", required=True)
    tenant_branding.add_argument("--secondary-color", required=True)
    tenant_modules = tenant_sub.add_parser("modules")
    tenant_modules.add_argument("--id", required=True)
    tenant_modules.add_argument("--enable", nargs="+", default=[])

    user = sub.add_parser("user")
    user_sub = user.add_subparsers(dest="action", required=True)
    create_admin = user_sub.add_parser("create-admin")
    create_admin.add_argument("--tenant-id", required=True)
    create_admin.add_argument("--username", required=True)
    reset_password = user_sub.add_parser("reset-password")
    reset_password.add_argument("--tenant-id", required=True)
    reset_password.add_argument("--username", required=True)

    session = sub.add_parser("session")
    session_sub = session.add_subparsers(dest="action", required=True)
    revoke = session_sub.add_parser("revoke")
    revoke.add_argument("--session-id", required=True)

    args = parser.parse_args()
    apply = bool(args.apply)

    if args.resource == "tenant" and args.action == "create":
        _print_plan(
            "tenant.create",
            {"id": args.id, "code": args.code, "name": args.name, "status": args.status, "plan": args.plan},
            apply,
        )
    elif args.resource == "tenant" and args.action == "list":
        _print_plan("tenant.list", {"fields": ["id", "code", "name", "status", "plan"]}, apply)
    elif args.resource == "tenant" and args.action in {"suspend", "activate"}:
        _print_plan(f"tenant.{args.action}", {"id": args.id}, apply)
    elif args.resource == "tenant" and args.action == "branding":
        _print_plan(
            "tenant.branding",
            {"id": args.id, "primary_color": args.primary_color, "secondary_color": args.secondary_color},
            apply,
        )
    elif args.resource == "tenant" and args.action == "modules":
        _print_plan("tenant.modules", {"id": args.id, "enabled_modules": args.enable}, apply)
    elif args.resource == "user" and args.action in {"create-admin", "reset-password"}:
        temporary_password = generate_temporary_password()
        _print_plan(
            f"user.{args.action}",
            {
                "tenant_id": args.tenant_id,
                "username": args.username,
                "roles": ["tenant_admin"],
                "temporary_password_hash": AuthService.hash_password(temporary_password),
                "password_hash_generated": True,
                "temporary_password": temporary_password,
                "must_change_password": True,
            },
            apply,
        )
        print("TEMPORARY_PASSWORD_ONE_TIME=" + temporary_password)
    elif args.resource == "session" and args.action == "revoke":
        _print_plan("session.revoke", {"session_id": args.session_id}, apply)
    else:
        raise SystemExit("Unsupported command")

    if not apply:
        print("Dry-run only. Re-run with --apply in staging after reviewing the plan.")
    else:
        print("Apply mode selected. Wire this command to Cosmos staging before production use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
