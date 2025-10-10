"""
Script de migración para actualizar valores de campus de usuarios existentes
Actualiza usuarios con valores antiguos al nuevo sistema de 88 instituciones
"""

import asyncio
from cosmos_helper import container, get_user_by_username

# Mapeo de valores antiguos a nuevos
CAMPUS_MIGRATION_MAP = {
    # Valores antiguos → Valores nuevos
    "llano-largo": "cres-llano-largo",
    "cruz-grande": "cres-cruz-grande",
    "zumpango": "cres-zumpango",
    "taxco-viejo": "cres-taxco-viejo",
    "huamuxtitlan": "cres-huamuxtitlan",
    "tecpan": "cres-tecpan",
    
    # Clínicas
    "clinica-chilpancingo": "clinica-chilpancingo",  # Ya correcto
    "clinica-acapulco": "clinica-acapulco",  # Ya correcto
    "clinica-iguala": "clinica-iguala",  # Ya correcto
    "clinica-ometepec": "clinica-ometepec",  # Ya correcto
    
    # Facultades (si existían con prefijo diferente)
    "medicina": "fac-medicina",
    "arquitectura": "fac-arquitectura",
    "quimico": "fac-quimico",
    "enfermeria": "fac-enfermeria",
    "gobierno": "fac-gobierno",
    
    # Preparatorias (formato antiguo prep-X → mantener igual)
    # prep-1 a prep-50 ya son correctos
    
    # Rectoría
    "rectoria": "rectoria",  # Ya correcto
}

async def migrate_user(username: str, new_campus: str = None):
    """
    Actualiza el campus de un usuario específico
    Si no se proporciona new_campus, intenta mapearlo automáticamente
    """
    try:
        # Obtener usuario actual
        user = await get_user_by_username(username)
        if not user:
            print(f"❌ Usuario '{username}' no encontrado")
            return False
        
        old_campus = user.get("campus")
        print(f"\n📋 Usuario: {username}")
        print(f"   Campus actual: {old_campus}")
        print(f"   Rol: {user.get('rol')}")
        
        # Si se proporciona new_campus, usar ese
        if new_campus:
            target_campus = new_campus
        # Si no, intentar mapear automáticamente
        elif old_campus in CAMPUS_MIGRATION_MAP:
            target_campus = CAMPUS_MIGRATION_MAP[old_campus]
        else:
            print(f"⚠️  No hay mapeo automático para '{old_campus}'")
            print(f"   Valores sugeridos:")
            print(f"   - cres-llano-largo (CRES Campus Llano Largo)")
            print(f"   - fac-medicina (Facultad de Medicina)")
            print(f"   - prep-1 (Escuela Preparatoria No. 1)")
            print(f"   - rectoria (Rectoría)")
            return False
        
        # Actualizar usuario
        user["campus"] = target_campus
        await container.upsert_item(user)
        
        print(f"✅ Usuario actualizado exitosamente")
        print(f"   Nuevo campus: {target_campus}")
        return True
        
    except Exception as e:
        print(f"❌ Error al migrar usuario: {e}")
        return False

async def migrate_all_users():
    """
    Migra todos los usuarios en la base de datos
    """
    try:
        query = "SELECT * FROM c WHERE c.type = 'user'"
        items = container.query_items(query=query, enable_cross_partition_query=True)
        
        users = [item for item in items]
        print(f"\n🔍 Encontrados {len(users)} usuarios")
        
        migrated = 0
        skipped = 0
        
        for user in users:
            username = user.get("username")
            old_campus = user.get("campus")
            
            # Si ya está en formato nuevo, saltar
            if old_campus.startswith(("cres-", "fac-", "prep-", "clinica-")) or old_campus == "rectoria":
                print(f"⏭️  {username}: campus ya actualizado ({old_campus})")
                skipped += 1
                continue
            
            # Intentar migrar
            if await migrate_user(username):
                migrated += 1
            else:
                skipped += 1
        
        print(f"\n📊 Resumen:")
        print(f"   ✅ Migrados: {migrated}")
        print(f"   ⏭️  Omitidos: {skipped}")
        print(f"   📝 Total: {len(users)}")
        
    except Exception as e:
        print(f"❌ Error en migración masiva: {e}")

async def main():
    """
    Menú principal del script de migración
    """
    print("=" * 60)
    print("🔄 Script de Migración de Campus")
    print("=" * 60)
    
    # Por defecto, migrar el usuario DireccionInnovaSalud a CRES Llano Largo
    # (que es la dirección principal de Innova Salud)
    await migrate_user("DireccionInnovaSalud", "cres-llano-largo")
    
    print("\n" + "=" * 60)
    print("✅ Migración completada")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
