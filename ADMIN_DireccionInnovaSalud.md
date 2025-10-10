# 🔐 Usuario Administrador: DireccionInnovaSalud

## 📋 Información del Usuario

```
Username:     DireccionInnovaSalud
Email:        innovasalud@uagro.mx
Nombre:       Dirección Innova Salud
Password:     Uagro2025!Admin
Campus:       llano-largo
Departamento: Dirección
Rol:          admin
```

---

## 🚀 OPCIÓN 1: Crear en Azure Portal (RECOMENDADO)

### Pasos:

1. **Ir a Azure Portal**
   ```
   https://portal.azure.com
   ```

2. **Navegar a Cosmos DB**
   - Tu cuenta Cosmos DB
   - Data Explorer
   - Base de datos: `sasu_db`
   - Contenedor: `usuarios`

3. **Click en "New Item"**

4. **Pegar este JSON** (ajusta si es necesario):

```json
{
  "id": "admin-direccion-innova",
  "username": "DireccionInnovaSalud",
  "email": "innovasalud@uagro.mx",
  "nombre_completo": "Dirección Innova Salud",
  "password_hash": "$2b$12$KIXGWl8N5c8yM0mGvQ8hxeJ3J8vZ3gxqX8N5c8yM0mGvQ8hxeJ3J8O",
  "rol": "admin",
  "campus": "llano-largo",
  "departamento": "Dirección",
  "activo": true,
  "intentos_fallidos": 0,
  "bloqueado_hasta": null,
  "ultimo_acceso": null,
  "fecha_creacion": "2025-10-10T18:00:00Z"
}
```

5. **Click en "Save"**

---

## ⚠️ NOTA IMPORTANTE

El `password_hash` en el JSON de arriba es un **placeholder**.

Después de crear el usuario en Azure Portal, necesitas:

### **Generar el hash correcto:**

Hay 3 opciones:

#### **A. Usar el backend en Render.com** (MÁS FÁCIL)

Ya que el backend está desplegado, puedes:

1. Crear el usuario con cualquier hash en Azure Portal
2. Luego, desde Render.com, ejecutar un comando para actualizar el hash:

```python
# Conectar a Render.com > Shell
python -c "from auth_service import AuthService; print(AuthService.hash_password('Uagro2025!Admin'))"
```

3. Actualizar el `password_hash` en Azure Portal con el resultado

#### **B. Crear desde otro admin** (SI YA EXISTE UNO)

Si ya tienes otro usuario admin:
1. Login al panel web con ese admin
2. Crear nuevo usuario "DireccionInnovaSalud" desde el panel
3. El hash se generará automáticamente

#### **C. Usar Python localmente** (Requiere credenciales)

Si tienes las credenciales de Cosmos DB configuradas en `.env`:

```powershell
cd c:\CRES_Carnets_UAGROPRO\temp_backend
python -c "from passlib.context import CryptContext; ctx = CryptContext(schemes=['bcrypt'], deprecated='auto'); print(ctx.hash('Uagro2025!Admin'[:72]))"
```

---

## 🚀 OPCIÓN 2: Usar Script Interactivo (Requiere .env)

Si configuraste el archivo `.env` con las credenciales de Cosmos DB:

```powershell
cd c:\CRES_Carnets_UAGROPRO\temp_backend
python create_admin.py
```

Luego ingresa:
- Username: `DireccionInnovaSalud`
- Email: `innovasalud@uagro.mx`
- Nombre: `Dirección Innova Salud`
- Campus: `llano-largo` (opción 1)
- Departamento: `Dirección`
- Password: `Uagro2025!Admin`

---

## 🧪 Probar el Login

Una vez creado el usuario:

### **Desarrollo local:**
```
http://localhost:8000/admin
```

### **Producción (Render.com):**
```
https://fastapi-backend-o7ks.onrender.com/admin
```

### **Credenciales:**
- Usuario: `DireccionInnovaSalud`
- Contraseña: `Uagro2025!Admin`
- Campus: `llano-largo`

---

## 📝 Sugerencia de Flujo Más Simple

### **Método Rápido (Sin hash manual):**

1. **Crear usuario temporal simple en Azure Portal:**
   ```json
   {
     "id": "temp-admin",
     "username": "temp",
     "email": "temp@temp.com",
     "nombre_completo": "Temp Admin",
     "password_hash": "$2b$12$LQm5vQ8hxeJ3J8vZ3gxqX8N5c8yM0mGvQ8hxeJ3J8O",
     "rol": "admin",
     "campus": "llano-largo",
     "departamento": "Temp",
     "activo": true,
     "intentos_fallidos": 0,
     "bloqueado_hasta": null,
     "ultimo_acceso": null,
     "fecha_creacion": "2025-10-10T18:00:00Z"
   }
   ```

2. **Intentar login desde el panel web** con cualquier contraseña

3. **Ver los logs del backend en Render.com** para diagnosticar

4. **O mejor:** Simplemente **pushear el código a GitHub** y que Render haga deploy

5. **Luego usar la API de registro** desde Postman/curl para crear el primer admin

---

## 🎯 Recomendación Final

Como el sistema ya está en Render.com, lo más práctico es:

1. **Pushear los cambios a GitHub** (ya están listos)
2. **Esperar que Render haga auto-deploy** (2-3 minutos)
3. **Usar Postman o curl** para crear el primer admin vía API:

```bash
curl -X POST "https://fastapi-backend-o7ks.onrender.com/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "DireccionInnovaSalud",
    "email": "innovasalud@uagro.mx",
    "nombre_completo": "Dirección Innova Salud",
    "rol": "admin",
    "campus": "llano-largo",
    "departamento": "Dirección",
    "password": "Uagro2025!Admin"
  }'
```

**Nota:** Este endpoint requiere autenticación admin, así que primero necesitas crear uno manualmente en Cosmos DB o modificar temporalmente el endpoint para permitir la primera creación.

¿Prefieres que ajustemos el código para permitir crear el primer admin sin autenticación?
