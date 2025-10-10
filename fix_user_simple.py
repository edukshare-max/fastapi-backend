"""
Script simple para actualizar el campus del usuario DireccionInnovaSalud
"""

import os
import json
import asyncio
from azure.cosmos import CosmosClient

# Cargar credenciales desde cres_pwd.json
with open('cres_pwd.json', 'r') as f:
    creds = json.load(f)

# Configurar cliente Cosmos DB directamente
client = CosmosClient(creds['COSMOS_ENDPOINT'], credential=creds['COSMOS_KEY'])
database = client.get_database_client(creds['COSMOS_DB'])
container = database.get_container_client(creds['COSMOS_CONTAINER'])

async def update_user_campus():
    """
    Actualiza el campus del usuario DireccionInnovaSalud a cres-llano-largo
    """
    try:
        print("\n" + "=" * 60)
        print("🔄 Actualizando campus del usuario")
        print("=" * 60)
        
        username = "DireccionInnovaSalud"
        
        # Buscar usuario
        query = f"SELECT * FROM c WHERE c.username = '{username}' AND c.type = 'user'"
        items = list(container.query_items(query=query, enable_cross_partition_query=True))
        
        if not items:
            print(f"❌ Usuario '{username}' no encontrado")
            return False
        
        user = items[0]
        old_campus = user.get("campus")
        
        print(f"\n📋 Usuario encontrado:")
        print(f"   Username: {username}")
        print(f"   Campus actual: {old_campus}")
        print(f"   Rol: {user.get('rol')}")
        
        # Actualizar campus
        new_campus = "cres-llano-largo"
        user["campus"] = new_campus
        
        container.upsert_item(user)
        
        print(f"\n✅ Usuario actualizado exitosamente")
        print(f"   Nuevo campus: {new_campus}")
        print(f"   Campus completo: CRES Campus Llano Largo (Acapulco)")
        
        print("\n" + "=" * 60)
        print("✅ Migración completada")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error al actualizar usuario: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(update_user_campus())
