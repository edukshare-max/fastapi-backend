# 🔐 Sistema de Autenticación y Autorización - SASU CRES

**Fase 1 Completada:** Backend con autenticación JWT y gestión de usuarios

---

## 📋 **Características Implementadas**

### **✅ Sistema de Usuarios**
- Registro de usuarios con validación de contraseña fuerte
- Roles: admin, médico, nutrición, psicología, odontología, enfermería, recepción, lectura
- Campus: Llano Largo, Acapulco, Chilpancingo, Taxco, Iguala, Zihuatanejo
- Almacenamiento seguro con hash bcrypt

### **✅ Autenticación JWT**
- Login con username/password
- Tokens JWT con expiración de 8 horas
- Protección contra múltiples intentos fallidos (bloqueo temporal)
- Validación de tokens en cada request

### **✅ Autorización por Roles**
- Permisos granulares por rol
- Middleware de verificación de permisos
- Restricción de endpoints según rol

### **✅ Auditoría**
- Registro automático de todas las acciones
- Logs de login, logout, creación/modificación de datos
- Trazabilidad completa de operaciones

---

## 🚀 **Instalación y Configuración**

### **1. Instalar Dependencias**

```bash
cd temp_backend
pip install -r requirements.txt
```

### **2. Configurar Variables de Entorno**

Copiar `.env.example` a `.env` y configurar:

```bash
# Azure Cosmos DB
COSMOS_URL=https://tu-cuenta.documents.azure.com:443/
COSMOS_KEY=tu-clave-primaria
COSMOS_DB=SASU

# Contenedores (se crearán automáticamente si no existen)
COSMOS_CONTAINER_USUARIOS=usuarios
COSMOS_CONTAINER_AUDITORIA=auditoria

# JWT Secret (cambiar en producción)
JWT_SECRET_KEY=tu-clave-secreta-super-segura-aqui
```

### **3. Crear Contenedores en Cosmos DB**

Los contenedores se pueden crear desde Azure Portal o automáticamente:

```python
# usuarios: partition key = /id
# auditoria: partition key = /id
```

### **4. Crear Usuario Administrador Inicial**

```bash
python create_admin.py
```

Seguir las instrucciones en pantalla para crear el primer administrador.

---

## 📡 **Endpoints Disponibles**

### **Autenticación**

#### **POST /auth/register**
Crear nuevo usuario (solo admin)

```json
{
  "username": "drjuan",
  "email": "juan.lopez@uagro.mx",
  "password": "SecurePass123",
  "nombre_completo": "Dr. Juan López García",
  "rol": "medico",
  "campus": "llano-largo",
  "departamento": "Consultorio Médico"
}
```

**Headers requeridos:**
```
Authorization: Bearer {token_admin}
```

#### **POST /auth/login**
Iniciar sesión

```json
{
  "username": "drjuan",
  "password": "SecurePass123",
  "campus": "llano-largo"
}
```

**Respuesta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "user:drjuan@llano-largo",
    "username": "drjuan",
    "nombre_completo": "Dr. Juan López García",
    "rol": "medico",
    "campus": "llano-largo",
    ...
  }
}
```

#### **GET /auth/me**
Obtener información del usuario actual

**Headers:**
```
Authorization: Bearer {token}
```

### **Gestión de Usuarios (solo admin)**

#### **GET /auth/users**
Listar todos los usuarios

Parámetros opcionales:
- `campus`: Filtrar por campus
- `rol`: Filtrar por rol

#### **PATCH /auth/users/{user_id}**
Actualizar información de usuario

```json
{
  "activo": false,  // Desactivar usuario
  "rol": "nutricion"  // Cambiar rol
}
```

### **Auditoría (solo admin)**

#### **GET /auth/audit-logs**
Obtener logs de auditoría

Parámetros:
- `usuario`: Filtrar por usuario
- `accion`: Filtrar por tipo de acción
- `limit`: Número máximo de registros (default: 100)

---

## 🔑 **Roles y Permisos**

### **admin**
- Control total del sistema
- Crear/modificar/eliminar usuarios
- Acceso a auditoría
- Todas las operaciones de datos

### **medico**
- Crear y modificar carnets
- Crear y ver notas médicas
- Gestionar citas
- Ver promociones y vacunación

### **nutricion / psicologia / odontologia**
- Ver carnets (solo lectura)
- Crear notas de su departamento
- Gestionar citas de su área
- Ver promociones

### **enfermeria**
- Ver carnets y notas (solo lectura)
- Ver citas
- Ver vacunación

### **recepcion**
- Ver carnets (solo lectura)
- Gestionar citas (crear/modificar)

### **lectura**
- Solo lectura de carnets, notas, citas
- Acceso a reportes

---

## 🧪 **Testing**

### **1. Verificar que el servidor esté corriendo**

```bash
curl http://localhost:8000/health
```

### **2. Crear usuario admin**

```bash
python create_admin.py
```

### **3. Hacer login**

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "tu-password",
    "campus": "llano-largo"
  }'
```

### **4. Usar el token en requests**

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer {tu_token_aqui}"
```

---

## 🔒 **Seguridad Implementada**

### **1. Hash de Contraseñas**
- Algoritmo: bcrypt
- Cost factor: 12 (muy seguro)
- Salt automático por contraseña

### **2. Validación de Contraseñas**
- Mínimo 8 caracteres
- Debe contener mayúsculas, minúsculas y números
- Validación en backend

### **3. Protección contra Brute Force**
- Máximo 5 intentos fallidos
- Bloqueo temporal de 30 minutos
- Logs de intentos fallidos

### **4. Tokens JWT**
- Firmados con HS256
- Expiración de 8 horas
- Incluyen rol y campus para autorización

### **5. Auditoría Completa**
- Registro de todas las acciones sensibles
- Timestamp, usuario, IP, detalles
- Inmutable (solo escritura)

---

## 📊 **Próximos Pasos (Fases 2-10)**

- [x] **Fase 1:** Backend - Autenticación y usuarios ✅
- [ ] **Fase 2:** Backend - Integrar autenticación en endpoints existentes
- [ ] **Fase 3:** Backend - Proteger todos los endpoints con roles
- [ ] **Fase 4:** Backend - Sistema de auditoría completo
- [ ] **Fase 5:** Panel Web Admin - Estructura base
- [ ] **Fase 6:** Panel Web Admin - Gestión de usuarios
- [ ] **Fase 7:** Panel Web Admin - Vista de auditoría
- [ ] **Fase 8:** Flutter - Pantalla de login
- [ ] **Fase 9:** Flutter - Gestión de sesión
- [ ] **Fase 10:** Flutter - Restricciones por rol

---

## 📝 **Notas de Desarrollo**

### **Contenedores Cosmos DB Requeridos**

```
usuarios:
  - Partition Key: /id
  - Campos: id, username, email, password_hash, rol, campus, activo, etc.

auditoria:
  - Partition Key: /id  
  - Campos: id, usuario, accion, recurso, timestamp, ip, etc.
```

### **Estructura de IDs**

```
Usuarios: user:{username}@{campus}
  Ejemplo: user:drjuan@llano-largo

Auditoría: audit:{timestamp}-{random}
  Ejemplo: audit:20251010-143022-a1b2c3d4
```

---

## 🆘 **Troubleshooting**

### **Error: "Cannot connect to Cosmos DB"**
- Verificar COSMOS_URL y COSMOS_KEY en `.env`
- Verificar que los contenedores existan
- Verificar conectividad de red

### **Error: "Token inválido"**
- Verificar que el token no haya expirado (8 horas)
- Verificar que JWT_SECRET_KEY sea consistente
- Hacer login nuevamente

### **Error: "No tienes permisos"**
- Verificar que el usuario tenga el rol correcto
- Verificar los permisos en `auth_models.py` → `ROLE_PERMISSIONS`

---

**✅ FASE 1 COMPLETADA**

El backend está listo para autenticación. Ahora puedes:
1. Crear usuario admin con `python create_admin.py`
2. Probar login con curl o Postman
3. Continuar con Fase 2 (proteger endpoints existentes)
