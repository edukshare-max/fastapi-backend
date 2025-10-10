"""
Script para eliminar el usuario admin existente y crear uno nuevo.
"""
import requests
import json

# Configuración
API_BASE_URL = "https://fastapi-backend-o7ks.onrender.com"

print("=" * 70)
print("🔧 RESET ADMIN USER")
print("=" * 70)
print()

# Como no tenemos autenticación, vamos a usar el endpoint especial
# Primero, necesitamos saber el ID del usuario para eliminarlo
# El ID sigue el formato: user:{username}@{campus}

user_id = "user:DireccionInnovaSalud@llano-largo"

print(f"📋 Usuario a eliminar: {user_id}")
print()
print("⚠️  IMPORTANTE:")
print("   Este usuario debe eliminarse manualmente desde Azure Cosmos DB")
print("   porque los endpoints de eliminación requieren autenticación.")
print()
print("PASOS MANUALES:")
print("1. Ve a Azure Portal > Cosmos DB > sasu_db > usuarios")
print("2. Busca el item con id: user:DireccionInnovaSalud@llano-largo")
print("3. Elimina ese item")
print("4. Ejecuta de nuevo: python init_direccion_innova.py")
print()
print("=" * 70)
