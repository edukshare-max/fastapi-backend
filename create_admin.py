# temp_backend/create_admin.py
"""
Script para crear el primer usuario administrador del sistema.
Ejecutar una sola vez para inicializar el sistema de autenticación.
"""

import os
import sys
from dotenv import load_dotenv
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

# Importar después de cargar .env
from cosmos_helper import CosmosDBHelper
from auth_service import AuthService
from auth_models import UserRole, Campus

def create_admin_user():
    """Crea el usuario administrador inicial."""
    
    print("=" * 60)
    print("🔐 CREACIÓN DE USUARIO ADMINISTRADOR INICIAL")
    print("=" * 60)
    
    # Conectar a Cosmos DB
    try:
        usuarios = CosmosDBHelper(
            os.environ.get("COSMOS_CONTAINER_USUARIOS", "usuarios"),
            "/id"
        )
        print("✅ Conectado a Cosmos DB")
    except Exception as e:
        print(f"❌ Error al conectar a Cosmos DB: {e}")
        return False
    
    # Datos del admin
    print("\n📝 Ingrese los datos del administrador:")
    username = input("Username (ej: admin): ").strip() or "admin"
    email = input("Email (ej: admin@cres.uagro.mx): ").strip() or "admin@cres.uagro.mx"
    nombre_completo = input("Nombre completo: ").strip() or "Administrador CRES"
    password = input("Contraseña (mínimo 8 caracteres): ").strip()
    
    if not password or len(password) < 8:
        print("❌ La contraseña debe tener al menos 8 caracteres")
        return False
    
    # Validar fortaleza
    is_valid, message = AuthService.validate_password_strength(password)
    if not is_valid:
        print(f"❌ {message}")
        return False
    
    # Campus
    print("\n🏫 Seleccione el campus:")
    for i, campus in enumerate(Campus, 1):
        print(f"  {i}. {campus.value}")
    
    campus_choice = input("Selección (1-6) [1]: ").strip() or "1"
    campus = list(Campus)[int(campus_choice) - 1]
    
    # Generar ID
    user_id = AuthService.generate_user_id(username, campus)
    
    # Verificar si ya existe
    try:
        existing = usuarios.read_item(user_id, user_id)
        if existing:
            print(f"\n⚠️  El usuario '{username}@{campus.value}' ya existe.")
            overwrite = input("¿Sobrescribir? (s/N): ").strip().lower()
            if overwrite != 's':
                print("❌ Operación cancelada")
                return False
    except:
        pass  # No existe, continuar
    
    # Crear usuario
    user_dict = {
        "id": user_id,
        "username": username,
        "email": email,
        "password_hash": AuthService.hash_password(password),
        "nombre_completo": nombre_completo,
        "rol": UserRole.ADMIN.value,
        "campus": campus.value,
        "departamento": "Administración",
        "activo": True,
        "fecha_creacion": datetime.utcnow().isoformat(),
        "ultimo_acceso": None,
        "intentos_fallidos": 0,
        "bloqueado_hasta": None
    }
    
    try:
        usuarios.upsert_item(user_dict, user_id)
        print("\n" + "=" * 60)
        print("✅ USUARIO ADMINISTRADOR CREADO EXITOSAMENTE")
        print("=" * 60)
        print(f"\n📋 Detalles del usuario:")
        print(f"   ID: {user_id}")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Nombre: {nombre_completo}")
        print(f"   Rol: ADMINISTRADOR")
        print(f"   Campus: {campus.value}")
        print(f"\n🔑 Credenciales de acceso:")
        print(f"   Usuario: {username}")
        print(f"   Contraseña: {'*' * len(password)}")
        print(f"\n🌐 Panel Web: https://admin-sasu.onrender.com")
        print(f"💻 App Flutter: Usar estas credenciales en el login")
        print("\n" + "=" * 60)
        return True
    
    except Exception as e:
        print(f"\n❌ Error al crear usuario: {e}")
        return False

if __name__ == "__main__":
    success = create_admin_user()
    sys.exit(0 if success else 1)
