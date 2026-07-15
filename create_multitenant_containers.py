import os
import sys

from azure.cosmos import CosmosClient, PartitionKey

from cosmos_helper import get_cosmos_db_name
from multitenancy_provisioning import (
    MULTITENANT_CONTAINERS,
    azure_cosmos_supports_hierarchical_partition_keys,
)


def main() -> int:
    if os.environ.get("SASU_MULTITENANT_STAGING_CONFIRM") != "CREATE_STAGING_CONTAINERS":
        print("Dry-run: set SASU_MULTITENANT_STAGING_CONFIRM=CREATE_STAGING_CONTAINERS to create staging containers.")
        for definition in MULTITENANT_CONTAINERS:
            print(f"- {definition.name}: {definition.partition_key}")
        return 0

    if os.environ.get("SASU_ENVIRONMENT") != "staging":
        raise RuntimeError("Container creation is allowed only with SASU_ENVIRONMENT=staging")

    supports_hpk = azure_cosmos_supports_hierarchical_partition_keys()
    client = CosmosClient(os.environ["COSMOS_URL"], credential=os.environ["COSMOS_KEY"])
    database = client.get_database_client(get_cosmos_db_name())

    for definition in MULTITENANT_CONTAINERS:
        if definition.hierarchical_partition_key and not supports_hpk:
            print(f"Skipping {definition.name}: installed azure-cosmos does not support hierarchical keys.")
            continue
        database.create_container_if_not_exists(
            id=definition.name,
            partition_key=PartitionKey(path=definition.partition_key),
        )
        print(f"Ensured {definition.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
