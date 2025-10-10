"""
Script para crear usuarios admin usando el API de producción en Render.com
Este script NO requiere acceso directo a Cosmos DB
"""
import requests
import json
import getpass

# URL del backend en Render.com
API_BASE_URL = "https://fastapi-backend-o7ks.onrender.com"

def create_admin_via_api():
    print("=" * 60)
    print("CREAR USUARIO ADMINISTRADOR - Vía API")
    print("=" * 60)
    print()
    print("⚠️  ADVERTENCIA: Este es el PRIMER USUARIO del sistema.")
    print("    Necesitas credenciales de un admin existente, O")
    print("    debes crear el usuario directamente en Cosmos DB.")
    print()
    
    # Opción 1: Ya existe un admin
    print("¿Ya existe un usuario admin? (s/n): ", end="")
    has_admin = input().lower()
    
    if has_admin == 's':
        print("\nIngrese credenciales del admin existente:")
        admin_username = input("Usuario admin: ").strip()
        admin_password = getpass.getpass("Contraseña admin: ")
        admin_campus = input("Campus (llano-largo/acapulco/chilpancingo/taxco/iguala/zihuatanejo): ").strip()
        
        # Login como admin
        print("\n🔐 Autenticando...")
        try:
            login_response = requests.post(
                f"{API_BASE_URL}/auth/login",
                json={
                    "username": admin_username,
                    "password": admin_password,
                    "campus": admin_campus
                }
            )
            
            if login_response.status_code != 200:
                print(f"❌ Error de autenticación: {login_response.json().get('detail', 'Error desconocido')}")
                return
            
            token = login_response.json()["access_token"]
            print("✅ Autenticación exitosa")
            
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            return
    else:
        print("\n❌ ERROR: No se puede crear el primer admin sin credenciales.")
        print("\nOPCIONES:")
        print("1. Crear usuario manualmente en Azure Portal > Cosmos DB")
        print("2. Usar el script create_admin.py con credenciales locales")
        print("3. Contactar al administrador del sistema")
        return
    
    # Crear nuevo usuario
    print("\n" + "=" * 60)
    print("DATOS DEL NUEVO USUARIO")
    print("=" * 60)
    
    username = input("Usuario (solo letras, números, guiones): ").strip()
    email = input("Email: ").strip()
    nombre_completo = input("Nombre completo: ").strip()
    
    print("\nRoles disponibles:")
    print("  1. admin          - Acceso completo al sistema")
    print("  2. medico         - Carnets, notas, citas")
    print("  3. nutricion      - Carnets, notas de nutrición")
    print("  4. psicologia     - Carnets, notas de psicología")
    print("  5. odontologia    - Carnets, notas de odontología")
    print("  6. enfermeria     - Carnets, vacunaciones, citas")
    print("  7. recepcion      - Ver y crear citas")
    print("  8. lectura        - Solo lectura")
    
    rol_num = input("Seleccione rol (1-8): ").strip()
    roles = {
        "1": "admin", "2": "medico", "3": "nutricion", "4": "psicologia",
        "5": "odontologia", "6": "enfermeria", "7": "recepcion", "8": "lectura"
    }
    rol = roles.get(rol_num, "lectura")
    
    print("\nCampus disponibles:")
    print("  1. llano-largo")
    print("  2. acapulco")
    print("  3. chilpancingo")
    print("  4. taxco")
    print("  5. iguala")
    print("  6. zihuatanejo")
    
    campus_num = input("Seleccione campus (1-6): ").strip()
    campus_options = {
        "1": "llano-largo", "2": "acapulco", "3": "chilpancingo",
        "4": "taxco", "5": "iguala", "6": "zihuatanejo"
    }
    campus = campus_options.get(campus_num, "llano-largo")
    
    departamento = input("Departamento: ").strip()
    
    password = getpass.getpass("Contraseña (mínimo 8 caracteres): ")
    password_confirm = getpass.getpass("Confirmar contraseña: ")
    
    if password != password_confirm:
        print("❌ Las contraseñas no coinciden")
        return
    
    # Crear usuario
    print("\n🔄 Creando usuario...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/register",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": username,
                "email": email,
                "nombre_completo": nombre_completo,
                "rol": rol,
                "campus": campus,
                "departamento": departamento,
                "password": password
            }
        )
        
        if response.status_code == 200:
            user = response.json()
            print("\n" + "=" * 60)
            print("✅ USUARIO CREADO EXITOSAMENTE")
            print("=" * 60)
            print(f"ID:               {user['id']}")
            print(f"Usuario:          {user['username']}")
            print(f"Email:            {user['email']}")
            print(f"Nombre:           {user['nombre_completo']}")
            print(f"Rol:              {user['rol']}")
            print(f"Campus:           {user['campus']}")
            print(f"Departamento:     {user['departamento']}")
            print(f"Estado:           {'✓ Activo' if user['activo'] else '✗ Inactivo'}")
            print("=" * 60)
            print(f"\n🔐 Credenciales de acceso:")
            print(f"   Usuario: {username}")
            print(f"   Campus:  {campus}")
            print(f"   Panel:   {API_BASE_URL}/admin")
        else:
            error = response.json()
            print(f"❌ Error al crear usuario: {error.get('detail', 'Error desconocido')}")
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

def check_backend_status():
    """Verificar que el backend esté funcionando"""
    print("🔍 Verificando conexión con el backend...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Backend disponible")
            return True
        else:
            print("⚠️  Backend respondió con error")
            return False
    except requests.exceptions.Timeout:
        print("⏱️  Backend tardando en responder (cold start)...")
        print("   Reintentando en 30 segundos...")
        import time
        time.sleep(30)
        return check_backend_status()
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    print("\n🏥 SISTEMA SASU - Creación de Usuarios Admin")
    print(f"📡 Backend: {API_BASE_URL}\n")
    
    if check_backend_status():
        create_admin_via_api()
    else:
        print("\n❌ No se pudo conectar con el backend.")
        print("   Verifica que Render.com esté activo.")
