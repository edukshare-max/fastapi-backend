"""
Script para verificar qué usuarios admin existen en el sistema
"""
import requests

API_BASE_URL = "https://fastapi-backend-o7ks.onrender.com"

print("=" * 70)
print("🔍 VERIFICAR USUARIOS ADMIN EXISTENTES")
print("=" * 70)
print()

# Hacer una query al endpoint de salud para verificar conectividad
try:
    health = requests.get(f"{API_BASE_URL}/health", timeout=10)
    print(f"✅ Backend: {health.status_code}")
except Exception as e:
    print(f"❌ Error conectando al backend: {e}")
    exit(1)

# Intentar crear admin para ver el mensaje de error detallado
admin_data = {
    "username": "TestAdmin",
    "email": "test@uagro.mx",
    "nombre_completo": "Test Admin",
    "rol": "admin",
    "campus": "llano-largo",
    "departamento": "Test",
    "password": "Test1234"
}

print("\n🔄 Intentando crear un admin de prueba...")
print("   (Esto fallará pero nos dará información)")
print()

try:
    response = requests.post(
        f"{API_BASE_URL}/auth/init-admin",
        json=admin_data,
        timeout=30
    )
    
    if response.status_code == 403:
        print("✅ CONFIRMADO: Ya existe al menos un admin en el sistema")
        print(f"   Detalle: {response.json().get('detail', 'N/A')}")
    elif response.status_code == 200:
        print("⚠️  ADVERTENCIA: Se pudo crear un admin!")
        print("   Esto significa que NO había admins en el sistema")
        user = response.json()
        print(f"   Usuario creado: {user.get('username', 'N/A')}")
    else:
        print(f"❌ Error inesperado: {response.status_code}")
        print(f"   Respuesta: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ Error: {e}")

print()
print("=" * 70)
print("INSTRUCCIONES:")
print("=" * 70)
print()
print("Para ver TODOS los usuarios en Cosmos DB:")
print("1. Azure Portal > Cosmos DB > sasu_db > usuarios")
print("2. En la query, ejecuta:")
print("   SELECT * FROM c WHERE c.rol = 'admin'")
print()
print("Si hay múltiples registros, elimina TODOS y ejecuta:")
print("   python init_direccion_innova.py")
print()
print("=" * 70)
