from __future__ import annotations

from pathlib import PurePosixPath


def tenant_file_prefix(tenant_id: str, resource_type: str, resource_id: str) -> str:
    return str(PurePosixPath("tenants") / tenant_id / resource_type / resource_id)


def build_tenant_file_path(tenant_id: str, resource_type: str, resource_id: str, filename: str) -> str:
    safe_name = PurePosixPath(filename).name
    return str(PurePosixPath(tenant_file_prefix(tenant_id, resource_type, resource_id)) / safe_name)


def assert_file_belongs_to_tenant(path: str, tenant_id: str) -> bool:
    normalized = str(PurePosixPath(path))
    return normalized.startswith(f"tenants/{tenant_id}/")
