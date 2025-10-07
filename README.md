# Backend Node.js para Carnet Digital UAGro - SASU

## Descripción
Backend REST API desarrollado en Node.js con Express para la aplicación Carnet Digital de la Universidad Autónoma de Guerrero. Se conecta a la base de datos SASU en Azure Cosmos DB.

## Características

- 🔐 **Autenticación JWT** con email + matrícula
- 🗄️ **Azure Cosmos DB** integración con SASU
- 📋 **Endpoints RESTful** para carnet y citas
- 🛡️ **Seguridad** con CORS, Helmet y Rate Limiting
- 🚀 **Deploy automático** en Render

## Endpoints

### Autenticación
- `POST /auth/login` - Login con email y matrícula
- `POST /auth/verify` - Verificar token JWT

### Datos del Usuario (requieren autenticación)
- `GET /me/carnet` - Obtener información del carnet
- `GET /me/citas` - Obtener todas las citas
- `GET /me/citas/:id` - Obtener cita específica

### Utilidades
- `GET /ping` - Health check del servidor

## Estructura del Proyecto

```
backend-nodejs/
├── config/
│   └── database.js         # Configuración de Azure Cosmos DB
├── middleware/
│   └── auth.js             # Middleware de autenticación JWT
├── routes/
│   ├── auth.js             # Rutas de autenticación
│   ├── carnet.js           # Rutas del carnet
│   └── citas.js            # Rutas de citas
├── .env.example            # Ejemplo de variables de entorno
├── .gitignore              # Archivos ignorados por Git
├── index.js                # Punto de entrada del servidor
├── package.json            # Dependencias y scripts
└── README.md               # Esta documentación
```

## Instalación Local

### Prerrequisitos
- Node.js 18.x o superior
- npm o yarn
- Acceso a Azure Cosmos DB SASU

### Pasos

1. **Clonar y entrar al directorio:**
```bash
cd backend-nodejs
```

2. **Instalar dependencias:**
```bash
npm install
```

3. **Configurar variables de entorno:**
```bash
cp .env.example .env
# Editar .env con tus credenciales reales
```

4. **Ejecutar en desarrollo:**
```bash
npm run dev
```

5. **Ejecutar en producción:**
```bash
npm start
```

## Variables de Entorno

```env
# Servidor
PORT=3000
NODE_ENV=production

# Azure Cosmos DB
COSMOS_ENDPOINT=https://tu-cosmos-account.documents.azure.com:443/
COSMOS_KEY=tu_cosmos_key_aqui
COSMOS_DATABASE=SASU
COSMOS_CONTAINER_CARNETS=carnets_id
COSMOS_CONTAINER_CITAS=cita_id

# JWT
JWT_SECRET=tu_jwt_secret_muy_seguro
JWT_EXPIRES_IN=7d

# CORS
CORS_ORIGINS=http://localhost:3000,https://carnet-alumnos-nodes.onrender.com

# Rate Limiting
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100
```

## Deployment en Render

### Configuración Automática
Este proyecto está configurado para deployarse automáticamente en Render:

1. **Conectar repositorio** a Render
2. **Configurar variables de entorno** en Render Dashboard
3. **Deploy automático** en cada push a main

### Variables de Entorno en Render
Configurar en Render Dashboard > Environment:
- `COSMOS_ENDPOINT`
- `COSMOS_KEY`
- `JWT_SECRET`
- `NODE_ENV=production`

### URL de Producción
```
https://carnet-alumnos-nodes.onrender.com
```

## Estructura de Datos SASU

### Carnet (Container: carnets_id)
```json
{
  "id": "carnet:24785914",
  "matricula": "24785914",
  "nombreCompleto": "Giovanni Ocampo Garcia",
  "correo": "24785914@uagro.mx",
  "edad": 18,
  "categoria": "Alumno (a)",
  "programa": "Economía",
  "tipoSangre": "B +",
  "alergias": "Ninguna",
  "emergenciaContacto": "Mayra Ocampo (Mamá)",
  "emergenciaTelefono": "7441759577"
}
```

### Cita (Container: cita_id)
```json
{
  "id": "cita:294cbf1b-af89-4df5-84ee-d30d0628cc23",
  "matricula": "2025",
  "inicio": "2025-10-04T09:00:00Z",
  "fin": "2025-10-04T09:30:00Z",
  "motivo": "SEGUIMIENTO",
  "estado": "programada"
}
```

## Seguridad

- ✅ **CORS** configurado para dominios específicos
- ✅ **Helmet** para headers de seguridad
- ✅ **Rate Limiting** para prevenir abuso
- ✅ **JWT Tokens** con expiración
- ✅ **Validación** de entrada en todos los endpoints
- ✅ **Logs** de acceso y errores

## Testing

### Test Manual con curl

**Login:**
```bash
curl -X POST https://carnet-alumnos-nodes.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"24785914@uagro.mx","matricula":"24785914"}'
```

**Obtener Carnet:**
```bash
curl -X GET https://carnet-alumnos-nodes.onrender.com/me/carnet \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Obtener Citas:**
```bash
curl -X GET https://carnet-alumnos-nodes.onrender.com/me/citas \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Monitoreo

- Logs disponibles en Render Dashboard
- Health check en `/ping`
- Métricas de performance automáticas en Render

## Soporte

Para reportar problemas o solicitar funcionalidades:
1. Verificar logs en Render Dashboard
2. Revisar variables de entorno
3. Contactar al equipo de desarrollo UAGro

---

**Desarrollado para Universidad Autónoma de Guerrero (UAGro)**  
**Integración con Sistema SASU**