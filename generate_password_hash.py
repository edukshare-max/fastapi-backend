"""
Generador de hash de contraseña para usuarios admin
Útil para crear usuarios directamente en Azure Portal
"""
import sys
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

print("=" * 60)
print("GENERADOR DE PASSWORD HASH")
print("=" * 60)
print()
print("Este hash lo puedes usar para crear usuarios directamente")
print("en Azure Portal > Cosmos DB > usuarios container")
print()

if len(sys.argv) > 1:
    password = sys.argv[1]
else:
    password = input("Ingresa la contraseña a hashear: ")

if len(password) < 8:
    print("❌ La contraseña debe tener al menos 8 caracteres")
    sys.exit(1)

print()
print("🔐 Generando hash...")
password_hash = pwd_context.hash(password)

print()
print("=" * 60)
print("✅ HASH GENERADO")
print("=" * 60)
print()
print(f"Password:      {password}")
print(f"Hash:          {password_hash}")
print()
print("=" * 60)
print("📋 Copia este JSON completo para Azure Portal:")
print("=" * 60)
print(f"""
{{
  "id": "admin-001",
  "username": "admin.uagro",
  "email": "admin@uagro.mx",
  "nombre_completo": "Administrador UAGro",
  "password_hash": "{password_hash}",
  "rol": "admin",
  "campus": "llano-largo",
  "departamento": "Sistemas",
  "activo": true,
  "intentos_fallidos": 0,
  "bloqueado_hasta": null,
  "ultimo_acceso": null,
  "fecha_creacion": "2025-10-10T12:00:00Z"
}}
""")
print("=" * 60)
print()
print("⚠️  Recuerda ajustar: id, username, email, nombre_completo, campus")
print()
