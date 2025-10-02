import os
from azure.cosmos import CosmosClient
from dotenv import load_dotenv

load_dotenv()

COSMOS_URL = os.environ["COSMOS_URL"]
COSMOS_KEY = os.environ["COSMOS_KEY"]
DB_NAME = os.environ["COSMOS_DB"]

class CosmosDBHelper:
    def __init__(self, container_name, partition_key):
        self.client = CosmosClient(COSMOS_URL, credential=COSMOS_KEY)
        self.database = self.client.get_database_client(DB_NAME)
        self.container = self.database.get_container_client(container_name)
        self.partition_key = partition_key

    def get_by_id(self, id_value):
        return self.container.read_item(item=id_value, partition_key=id_value)

    def query_items(self, sql, params=None):
        return list(self.container.query_items(
            query=sql,
            parameters=params or [],
            enable_cross_partition_query=True
        ))

    def upsert_item(self, item, partition_value):
        return self.container.upsert_item(body=item, partition_key=partition_value)