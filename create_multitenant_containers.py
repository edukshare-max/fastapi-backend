import argparse
import json
import os
import sys

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from multitenancy_provisioning import (
    MULTITENANT_CONTAINERS,
)
from multitenancy_staging_config import DEFAULT_STAGING_DATABASE, load_staging_settings


def build_plan() -> list[dict]:
    plan = []
    for definition in MULTITENANT_CONTAINERS:
        plan.append(
            {
                "container": definition.name,
                "partition_key": definition.partition_key,
                "will_skip": False,
            }
        )
    return plan


def build_partition_key(definition):
    return PartitionKey(path=definition.partition_key)


def ensure_container(database, definition) -> dict:
    try:
        current = database.get_container_client(definition.name)
        properties = current.read()
        paths = properties.get("partitionKey", {}).get("paths", [])
        expected = [definition.partition_key]
        if paths != expected:
            raise RuntimeError(
                f"Container {definition.name} has incompatible partition key {paths}; expected {expected}"
            )
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
    if settings.cosmos_database_name != DEFAULT_STAGING_DATABASE:
        raise SystemExit(f"Refusing to use database {settings.cosmos_database_name}; expected {DEFAULT_STAGING_DATABASE}")

    plan = build_plan()
    print(json.dumps({"mode": "apply" if args.apply else "dry-run", "database": settings.cosmos_database_name, "plan": plan}, indent=2))

    if args.dry_run:
        return 0

    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], credential=os.environ["COSMOS_KEY"])
    database = client.get_database_client(settings.cosmos_database_name)
    report = []
    for definition in MULTITENANT_CONTAINERS:
        report.append(ensure_container(database, definition))
    print(json.dumps({"report": report}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
