# 🔐 Panel Web Admin - Guía de Inicialización

## ✅ Estado Actual del Sistema

### **Backend (FastAPI)**
- ✅ 6 endpoints de autenticación implementados
- ✅ Sistema JWT con tokens de 8 horas
- ✅ 8 roles con permisos granulares
- ✅ Sistema de auditoría automático
- ✅ Protección contra fuerza bruta
- ✅ Panel web integrado en `/admin`

### **Frontend (Panel Web)**
- ✅ HTML completo (522 líneas)
- ✅ CSS con diseño UAGro (663 líneas)
- ✅ JavaScript funcional (666 líneas)
- ✅ Login, CRUD usuarios, auditoría, exportar CSV

---

## 🚀 Método 1: Crear Admin en Azure Portal (RECOMENDADO)

### **¿Por qué este método?**
- No requiere credenciales locales
- Acceso directo a Cosmos DB
- Más rápido y seguro
- Ideal para inicializar el sistema

### **Pasos:**

#### 1. Acceder a Azure Portal
```
https://portal.azure.com
```

#### 2. Navegar a tu Cosmos DB Account
- Busca tu cuenta Cosmos DB
- Ve a: **Data Explorer**
- Encuentra la base de datos: `sasu_db`
- Encuentra el contenedor: `usuarios`

#### 3. Crear documento de usuario admin
Click en **"New Item"** y pega este JSON (ajusta los valores):

```json
{
  "id": "admin-001",
  "username": "admin.uagro",
  "email": "admin@uagro.mx",
  "nombre_completo": "Administrador UAGro",
  "password_hash": "$2b$12$LQ0Z5Z5Z5Z5Z5Z5Z5Z5Z5uYX9xYX9xYX9xYX9xYX9xYX9xYX9xYX9x",
  "rol": "admin",
  "campus": "llano-largo",
  "departamento": "Sistemas",
  "activo": true,
  "intentos_fallidos": 0,
  "bloqueado_hasta": null,
  "ultimo_acceso": null,
  "fecha_creacion": "2025-10-10T12:00:00Z"
}
```

#### 4. Generar el password_hash correcto

**Opción A - Usando Python localmente:**
```powershell
cd c:\CRES_Carnets_UAGROPRO\temp_backend
python -c "from passlib.context import CryptContext; pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto'); print(pwd_context.hash('TuPasswordAqui123'))"
```

**Opción B - Usando el panel web de otro admin:**
(Una vez que tengas un admin, puedes crear más desde el panel)

#### 5. Guardar el documento
- Click en **Save**
- El usuario admin ya está creado

#### 6. Acceder al panel web
```
https://fastapi-backend-o7ks.onrender.com/admin
```

**Credenciales:**
- Usuario: `admin.uagro` (o el que pusiste)
- Password: `TuPasswordAqui123` (o el que usaste)
- Campus: `llano-largo` (o el que pusiste)

---

## 🚀 Método 2: Usar Script Python Local

### **¿Cuándo usar este método?**
- Tienes las credenciales de Cosmos DB
- Prefieres automatización
- Ambiente de desarrollo local

### **Pasos:**

#### 1. Configurar variables de entorno

Edita el archivo `.env` en `temp_backend/`:

```env
COSMOS_URL=https://tu-cosmos-account.documents.azure.com:443/
COSMOS_KEY=tu-cosmos-primary-key-aqui
COSMOS_DATABASE=sasu_db
```

**¿Dónde encontrar estos valores?**
- Azure Portal > Cosmos DB Account > Settings > Keys
- O en Render.com > Dashboard > Environment Variables

#### 2. Ejecutar el script
```powershell
cd c:\CRES_Carnets_UAGROPRO\temp_backend
python create_admin.py
```

#### 3. Seguir el asistente interactivo
- Ingresa username (ej: `admin.uagro`)
- Ingresa email (ej: `admin@uagro.mx`)
- Ingresa nombre completo
- Selecciona campus
- Crea contraseña segura (8+ caracteres)

---

## 🚀 Método 3: Usar API Remota (Si ya existe un admin)

### **Pasos:**

```powershell
cd c:\CRES_Carnets_UAGROPRO\temp_backend
python create_admin_remote.py
```

Este script:
1. Verifica que el backend esté online
2. Te pide credenciales del admin existente
3. Crea nuevo usuario vía API

---

## 🧪 Probar el Panel Web

### **1. Acceder al panel**

**Desarrollo local:**
```powershell
cd c:\CRES_Carnets_UAGROPRO\temp_backend
uvicorn main:app --reload
```
Luego abrir: http://localhost:8000/admin

**Producción:**
```
https://fastapi-backend-o7ks.onrender.com/admin
```

### **2. Login**
- Ingresa username
- Ingresa password
- Selecciona campus
- Click en "Iniciar Sesión"

### **3. Crear usuarios de prueba**

Desde el panel, click en **"Nuevo Usuario"** y crea:

**Usuario 1 - Médico:**
- Username: `dr.garcia`
- Email: `garcia@uagro.mx`
- Nombre: `Dr. Juan García`
- Rol: `medico`
- Campus: `llano-largo`
- Departamento: `Medicina`

**Usuario 2 - Nutrición:**
- Username: `lic.martinez`
- Email: `martinez@uagro.mx`
- Nombre: `Lic. María Martínez`
- Rol: `nutricion`
- Campus: `acapulco`
- Departamento: `Nutrición`

**Usuario 3 - Recepción:**
- Username: `recepcion.ll`
- Email: `recepcion@uagro.mx`
- Nombre: `Recepción Llano Largo`
- Rol: `recepcion`
- Campus: `llano-largo`
- Departamento: `Administración`

### **4. Verificar funcionalidades**

✅ **Filtros:**
- Buscar por nombre o username
- Filtrar por campus
- Filtrar por rol

✅ **Acciones:**
- Editar usuario (click en ✏️)
- Activar/desactivar (click en ✓/✗)
- Refresh de la lista

✅ **Auditoría:**
- Ver logs de todas las acciones
- Filtrar por usuario
- Filtrar por acción
- Exportar a CSV

✅ **Configuración:**
- Ver estadísticas del sistema
- Info de API
- Limpiar caché

---

## 📝 Credenciales Recomendadas para Admin Inicial

```
Username:     admin.uagro
Email:        admin@uagro.mx
Nombre:       Administrador UAGro SASU
Password:     Uagro2025!Admin
Campus:       llano-largo
Departamento: Sistemas
```

**⚠️ IMPORTANTE:** Cambia la contraseña después del primer login!

---

## 🔧 Solución de Problemas

### **Error: "KeyError: 'COSMOS_URL'"**
- Solución: Configura el archivo `.env` con las credenciales de Cosmos DB

### **Error: "Solo administradores pueden acceder"**
- Solución: Asegúrate que el rol del usuario sea `admin` en Cosmos DB

### **Panel web no carga (404)**
- Solución: Verifica que `admin_panel/` esté en la carpeta `temp_backend/`
- Verifica que `main.py` tenga la línea `app.mount("/admin", ...)`

### **Error de conexión al login**
- Solución: Verifica que el backend esté corriendo
- En Render.com, puede tardar 30-45 segundos si está en cold start

### **Token expirado**
- Solución: Los tokens duran 8 horas. Haz logout y vuelve a entrar.

---

## 📦 Desplegar a Producción

### **1. Subir cambios a GitHub**
```powershell
cd c:\CRES_Carnets_UAGROPRO
git add temp_backend/
git commit -m "feat: Panel web admin con autenticación JWT"
git push origin main
```

### **2. Render.com auto-deploy**
- Render detectará los cambios
- Hará build automático
- El panel estará en: `https://fastapi-backend-o7ks.onrender.com/admin`

### **3. Verificar despliegue**
- Accede al panel en producción
- Prueba login con el admin creado
- Crea 2-3 usuarios de prueba

---

## 🎯 Próximos Pasos

Una vez que el panel web funcione y tengas varios usuarios creados:

1. ✅ **FASE 8:** Crear LoginScreen en Flutter
2. ✅ **FASE 9:** Implementar gestión de sesión en Flutter
3. ✅ **FASE 10:** Restricciones por rol en Flutter

---

## 📞 Soporte

Si encuentras algún problema:
1. Revisa los logs del backend
2. Verifica la consola del navegador (F12)
3. Asegúrate que Cosmos DB tenga los contenedores `usuarios` y `auditoria`

---

**¡Sistema listo para inicialización! 🚀**
