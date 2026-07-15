from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass
from typing import List


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


def azure_cosmos_supports_hierarchical_partition_keys() -> bool:
    try:
        version = importlib.metadata.version("azure-cosmos")
    except importlib.metadata.PackageNotFoundError:
        return False
    major, minor, *_ = [int(part) for part in version.split(".") if part.isdigit()]
    return (major, minor) >= (4, 4)
