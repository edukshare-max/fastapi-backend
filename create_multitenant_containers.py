import argparse
import json
import os
import sys

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from multitenancy_provisioning import (
    MULTITENANT_CONTAINERS,
    azure_cosmos_supports_hierarchical_partition_keys,
)
from multitenancy_staging_config import load_staging_settings


def build_plan(supports_hpk: bool) -> list[dict]:
    plan = []
    for definition in MULTITENANT_CONTAINERS:
        plan.append(
            {
                "container": definition.name,
                "partition_key": definition.partition_key_paths,
                "hierarchical": definition.hierarchical_partition_key,
                "will_skip": definition.hierarchical_partition_key and not supports_hpk,
            }
        )
    return plan


def build_partition_key(definition):
    paths = definition.partition_key_paths
    if len(paths) == 1:
        return PartitionKey(path=paths[0])
    return {"paths": paths, "kind": "MultiHash", "version": 2}


def ensure_container(database, definition) -> dict:
    try:
        current = database.get_container_client(definition.name)
        properties = current.read()
        paths = properties.get("partitionKey", {}).get("paths", [])
        expected = definition.partition_key_paths
        if paths != expected:
            return {
                "container": definition.name,
                "status": "partition_key_mismatch",
                "existing_partition_key": paths,
                "expected_partition_key": expected,
            }
        return {"container": definition.name, "status": "exists"}
    except CosmosResourceNotFoundError:
        database.create_container_if_not_exists(
            id=definition.name,
            partition_key=build_partition_key(definition),
        )
        return {"container": definition.name, "status": "created"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show plan only")
    parser.add_argument("--apply", action="store_true", help="Create missing staging containers")
    args = parser.parse_args()

    if args.dry_run and args.apply:
        raise SystemExit("--dry-run and --apply are mutually exclusive")
    if not args.apply:
        args.dry_run = True

    settings = load_staging_settings()
    supports_hpk = azure_cosmos_supports_hierarchical_partition_keys()
    plan = build_plan(supports_hpk)
    print(json.dumps({"mode": "apply" if args.apply else "dry-run", "database": settings.cosmos_database_name, "plan": plan}, indent=2))

    if args.dry_run:
        return 0

    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], credential=os.environ["COSMOS_KEY"])
    database = client.get_database_client(settings.cosmos_database_name)
    report = []
    for definition in MULTITENANT_CONTAINERS:
        if definition.hierarchical_partition_key and not supports_hpk:
            report.append({"container": definition.name, "status": "skipped_hierarchical_key_not_supported"})
            continue
        report.append(ensure_container(database, definition))
    print(json.dumps({"report": report}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
