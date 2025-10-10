"""
Script simple para crear admin - Solo necesitas las credenciales de Cosmos DB
Puedes obtenerlas de: https://dashboard.render.com > tu servicio > Environment
"""

import json
from azure.cosmos import CosmosClient
from passlib.context import CryptContext
import uuid
from datetime import datetime

# Password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin():
    print("\n" + "=" * 70)
    print("👤 CREAR ADMIN - Sistema CRES")
    print("=" * 70)
    
    print("\n📝 Necesito las credenciales de Cosmos DB")
    print("   Puedes obtenerlas de:")
    print("   → Render Dashboard: https://dashboard.render.com")
    print("   → Tu servicio > Environment tab")
    print("   → O desde Azure Portal > Cosmos DB > Keys")
    
    print("\n" + "-" * 70)
    cosmos_url = input("COSMOS_URL (ej: https://xxx.documents.azure.com:443/): ").strip()
    cosmos_key = input("COSMOS_KEY (la primary key larga): ").strip()
    cosmos_db = input("COSMOS_DB (ej: sasu_db): ").strip() or "sasu_db"
    cosmos_container = input("COSMOS_CONTAINER (ej: usuarios): ").strip() or "usuarios"
    print("-" * 70)
    
    try:
        print("\n🔄 Conectando a Cosmos DB...")
        client = CosmosClient(cosmos_url, credential=cosmos_key)
        database = client.get_database_client(cosmos_db)
        container = database.get_container_client(cosmos_container)
        print("✅ Conexión exitosa")
        
        # Datos del admin
        username = "DireccionInnovaSalud"
        password = "Admin2025"
        campus = "cres-llano-largo"
        rol = "DireccionInnovaSalud"
        
        print(f"\n📋 Creando usuario:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Campus: {campus} (CRES Campus Llano Largo)")
        print(f"   Rol: {rol}")
        
        # Crear documento
        user_id = str(uuid.uuid4())
        hashed_password = pwd_context.hash(password)
        
        user_doc = {
            "id": user_id,
            "username": username,
            "hashed_password": hashed_password,
            "campus": campus,
            "rol": rol,
            "type": "user",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Insertar
        container.create_item(body=user_doc)
        
        print("\n" + "=" * 70)
        print("✅ ADMIN CREADO EXITOSAMENTE")
        print("=" * 70)
        print(f"\n🔐 Credenciales:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Campus: {campus}")
        print(f"\n🌐 Panel admin:")
        print(f"   https://fastapi-backend-o7ks.onrender.com/admin/")
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_admin()
