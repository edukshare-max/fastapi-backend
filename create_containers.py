#!/usr/bin/env python3
"""
Script para crear los contenedores necesarios en Cosmos DB
para el sistema de autenticación.
"""
import os
from dotenv import load_dotenv
from azure.cosmos import CosmosClient, PartitionKey

# Cargar variables de entorno
load_dotenv()

def create_auth_containers():
    """Crea los contenedores necesarios para autenticación"""
    
    # Obtener credenciales (usar las mismas variables que cosmos_helper.py)
    endpoint = os.getenv("COSMOS_URL")
    key = os.getenv("COSMOS_KEY")
    database_name = os.getenv("COSMOS_DB")
    
    if not all([endpoint, key, database_name]):
        print("❌ ERROR: Faltan variables de entorno necesarias")
        print("Asegúrate de tener en el .env:")
        print("  - COSMOS_URL")
        print("  - COSMOS_KEY")
        print("  - COSMOS_DB")
        return False
    
    print("=" * 70)
    print("🏥 CREAR CONTENEDORES DE AUTENTICACIÓN")
    print("=" * 70)
    print(f"\n📡 Database: {database_name}")
    print(f"📡 Endpoint: {endpoint[:50] if endpoint else '(no endpoint)'}...")
    
    try:
        # Conectar a Cosmos DB
        print("\n🔍 Conectando a Cosmos DB...")
        client = CosmosClient(endpoint, key)
        database = client.get_database_client(database_name)
        print("✅ Conectado exitosamente")
        
        # Crear contenedor 'usuarios'
        print("\n📦 Creando contenedor 'usuarios'...")
        try:
            usuarios_container = database.create_container(
                id="usuarios",
                partition_key=PartitionKey(path="/id"),
                offer_throughput=400  # RU/s mínimo
            )
            print("✅ Contenedor 'usuarios' creado")
        except Exception as e:
            if "Conflict" in str(e):
                print("ℹ️  Contenedor 'usuarios' ya existe")
            else:
                print(f"❌ Error al crear 'usuarios': {e}")
                return False
        
        # Crear contenedor 'auditoria'
        print("\n📦 Creando contenedor 'auditoria'...")
        try:
            auditoria_container = database.create_container(
                id="auditoria",
                partition_key=PartitionKey(path="/id"),
                offer_throughput=400  # RU/s mínimo
            )
            print("✅ Contenedor 'auditoria' creado")
        except Exception as e:
            if "Conflict" in str(e):
                print("ℹ️  Contenedor 'auditoria' ya existe")
            else:
                print(f"❌ Error al crear 'auditoria': {e}")
                return False
        
        # Verificar contenedores existentes
        print("\n📋 Verificando todos los contenedores:")
        containers = list(database.list_containers())
        for container in containers:
            print(f"   ✓ {container['id']}")
        
        print("\n" + "=" * 70)
        print("✅ CONTENEDORES LISTOS")
        print("=" * 70)
        print("\nAhora puedes ejecutar:")
        print("  python init_direccion_innova.py")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = create_auth_containers()
    exit(0 if success else 1)
