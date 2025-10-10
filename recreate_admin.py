"""
Script para borrar todos los usuarios y crear un admin nuevo
con el sistema actualizado de 88 instituciones
"""

import os
import json
from azure.cosmos import CosmosClient
from passlib.context import CryptContext
import uuid
from datetime import datetime

# Cargar credenciales desde cres_pwd.json
with open('cres_pwd.json', 'r') as f:
    creds = json.load(f)

# Desencriptar las credenciales (simple decode)
def decrypt_credentials():
    """Lee las credenciales de las variables de entorno de Render"""
    # En producción estas vienen de Render, aquí las cargamos de otro lado
    # Por simplicidad, vamos a leerlas del archivo .env
    from dotenv import load_dotenv
    load_dotenv()
    return {
        'COSMOS_URL': os.environ.get('COSMOS_URL'),
        'COSMOS_KEY': os.environ.get('COSMOS_KEY'),
        'COSMOS_DB': os.environ.get('COSMOS_DB'),
        'COSMOS_CONTAINER': os.environ.get('COSMOS_CONTAINER')
    }

# Configurar cliente Cosmos DB
cosmos_creds = decrypt_credentials()
client = CosmosClient(cosmos_creds['COSMOS_URL'], credential=cosmos_creds['COSMOS_KEY'])
database = client.get_database_client(cosmos_creds['COSMOS_DB'])
container = database.get_container_client(cosmos_creds['COSMOS_CONTAINER'])

# Password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin_user():
    """
    Crea el usuario admin directamente en Cosmos DB
    """
    try:
        print("\n" + "=" * 60)
        print("👤 Creando usuario administrador en Cosmos DB")
        print("=" * 60)
        
        username = "DireccionInnovaSalud"
        password = "Admin2025"
        campus = "cres-llano-largo"
        rol = "DireccionInnovaSalud"
        
        print(f"\n📋 Datos del admin:")
        print(f"   Username: {username}")
        print(f"   Campus: {campus} (CRES Campus Llano Largo)")
        print(f"   Rol: {rol}")
        
        # Crear el documento del usuario
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
        
        # Insertar en Cosmos DB
        container.create_item(body=user_doc)
        
        print(f"\n✅ Usuario admin creado exitosamente en Cosmos DB")
        print(f"   ID: {user_id}")
        return True
        
    except Exception as e:
        print(f"\n❌ Error al crear admin: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    Menú principal
    """
    print("\n" + "=" * 60)
    print("🔄 Reset de Usuarios - Sistema CRES")
    print("=" * 60)
    
    print("\n📝 Pasos para reset completo:")
    print("\n1️⃣  Ve a Azure Portal:")
    print("   https://portal.azure.com")
    
    print("\n2️⃣  Navega a tu Cosmos DB:")
    print("   → Busca tu cuenta de Cosmos DB")
    print("   → Data Explorer")
    print("   → Selecciona tu database y container")
    
    print("\n3️⃣  Borra los usuarios:")
    print("   → Busca los items con type='user'")
    print("   → Delete cada uno (especialmente DireccionInnovaSalud)")
    
    print("\n4️⃣  Después ejecuta este script de nuevo para crear el admin")
    
    input("\n⏸️  Presiona Enter cuando hayas borrado los usuarios en Azure Portal...")
    
    # Intentar crear el nuevo admin
    if create_admin_user():
        print("\n" + "=" * 60)
        print("✅ Admin creado exitosamente")
        print("=" * 60)
        print("\n🔐 Credenciales:")
        print("   Username: DireccionInnovaSalud")
        print("   Password: Admin2025")
        print("   Campus: cres-llano-largo (CRES Campus Llano Largo)")
        print("\n🌐 Panel admin:")
        print("   https://fastapi-backend-o7ks.onrender.com/admin/")
    else:
        print("\n❌ No se pudo crear el admin")
        print("   Verifica que hayas borrado el usuario anterior")

if __name__ == "__main__":
    main()
