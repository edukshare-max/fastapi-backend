import os
import time
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError
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
        try:
            return self.container.read_item(item=id_value, partition_key=id_value)
        except CosmosHttpResponseError as e:
            raise CosmosHttpResponseError(status_code=e.status_code, message=e.message)

    def query_items(self, sql, params=None):
        try:
            return list(self.container.query_items(
                query=sql,
                parameters=params or [],
                enable_cross_partition_query=True
            ))
        except CosmosHttpResponseError as e:
            raise CosmosHttpResponseError(status_code=e.status_code, message=e.message)

    def upsert_item(self, item, partition_value):
        try:
            # Probar diferentes métodos según la versión del SDK
            try:
                # Método nuevo (azure-cosmos >= 4.0)
                result = self.container.upsert_item(body=item, partition_key=partition_value)
            except TypeError as te:
                if "partition_key" in str(te):
                    # Método viejo (azure-cosmos < 4.0) - pasar partition key en el item
                    pk_field = self.partition_key.lstrip('/')  # Remover '/' inicial
                    item[pk_field] = partition_value
                    result = self.container.upsert_item(item)
                else:
                    raise
            
            return result
        except CosmosHttpResponseError as e:
            # Retry para 429 (throttling)
            if e.status_code == 429:
                time.sleep(0.2)  # 200ms
                try:
                    # Retry una vez
                    try:
                        result = self.container.upsert_item(body=item, partition_key=partition_value)
                    except TypeError:
                        pk_field = self.partition_key.lstrip('/')
                        item[pk_field] = partition_value
                        result = self.container.upsert_item(item)
                    return result
                except CosmosHttpResponseError as retry_e:
                    raise CosmosHttpResponseError(status_code=retry_e.status_code, message=retry_e.message)
            
            # Idempotencia para 409 (conflict)
            if e.status_code == 409:
                # Devolver el documento actual
                try:
                    return self.get_by_id(item.get('id'))
                except:
                    raise CosmosHttpResponseError(status_code=e.status_code, message=e.message)
            
            raise CosmosHttpResponseError(status_code=e.status_code, message=e.message)