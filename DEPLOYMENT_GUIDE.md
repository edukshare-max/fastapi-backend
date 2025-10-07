# 🚀 GUÍA DE DEPLOYMENT EN RENDER - PASO A PASO

## Prerrequisitos

✅ **Código del backend Node.js completo** (ya tienes esto)  
⏳ **Cuenta en Render.com** (crear si no tienes)  
⏳ **Repositorio Git** (GitHub, GitLab o Bitbucket)  
⏳ **Credenciales de Azure Cosmos DB SASU**

---

## PASO 1: Subir código a repositorio Git

### Opción A: Crear nuevo repositorio en GitHub

1. **Ir a GitHub.com** y crear nuevo repositorio:
   - Nombre: `carnet-backend-sasu`
   - Descripción: `Backend Node.js para Carnet Digital UAGro - SASU`
   - Privado o público (recomendado: privado)

2. **Inicializar Git en tu directorio backend:**
```bash
cd "C:\Users\gilbe\Documents\Carnet_digital _alumnos\backend-nodejs"
git init
git add .
git commit -m "Initial commit: Backend Node.js para SASU"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/carnet-backend-sasu.git
git push -u origin main
```

### Opción B: Usar repositorio existente
Si ya tienes un repositorio, simplemente hacer push del directorio backend.

---

## PASO 2: Configurar servicio en Render

### 2.1 Crear cuenta en Render
1. Ir a **https://render.com**
2. Crear cuenta (puedes usar GitHub para OAuth)
3. Verificar email si es necesario

### 2.2 Crear nuevo Web Service
1. **Dashboard** → **New** → **Web Service**
2. **Connect repository**: Conectar tu repositorio Git
3. **Configurar deployment:**

```yaml
# Configuración básica
Name: carnet-alumnos-nodes
Environment: Node
Region: Ohio (US East)
Branch: main
Root Directory: . (o backend-nodejs si está en subdirectorio)

# Build & Deploy
Build Command: npm install
Start Command: npm start

# Configuración avanzada
Auto-Deploy: Yes
```

---

## PASO 3: Configurar variables de entorno en Render

### 3.1 Variables requeridas
En **Render Dashboard** → **Tu servicio** → **Environment**:

```env
# FUNDAMENTAL - Cosmos DB SASU
COSMOS_ENDPOINT=https://tu-cosmos-account.documents.azure.com:443/
COSMOS_KEY=tu_cosmos_key_real_aqui
COSMOS_DATABASE=SASU
COSMOS_CONTAINER_CARNETS=carnets_id
COSMOS_CONTAINER_CITAS=cita_id

# SEGURIDAD - JWT
JWT_SECRET=un_secret_muy_seguro_y_largo_para_produccion_12345
JWT_EXPIRES_IN=7d

# CONFIGURACIÓN
NODE_ENV=production
PORT=3000

# CORS - Permitir Flutter Web
CORS_ORIGINS=http://localhost:3000,https://carnet-alumnos-nodes.onrender.com,https://app.carnetdigital.space

# RATE LIMITING
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100
```

### 3.2 ⚠️ **IMPORTANTE: Obtener credenciales SASU**

**Necesitas las credenciales reales de Azure Cosmos DB SASU:**
- `COSMOS_ENDPOINT`: URL del endpoint de Cosmos DB
- `COSMOS_KEY`: Clave primaria o secundaria de acceso

**📞 Contactar administrador SASU para obtener:**
1. **Endpoint URL** de Azure Cosmos DB
2. **Access Key** (Primary o Secondary)
3. **Confirmar nombres** de base de datos y contenedores

---

## PASO 4: Deploy y verificación

### 4.1 Deployment automático
1. **Render detectará** el push al repositorio
2. **Iniciará build** automáticamente
3. **Logs en tiempo real** en Render Dashboard

### 4.2 Verificar deployment exitoso
**URL final:** `https://carnet-alumnos-nodes.onrender.com`

**Tests básicos:**
```bash
# Health check
curl https://carnet-alumnos-nodes.onrender.com/ping

# Debería responder:
{
  "success": true,
  "message": "Backend SASU online",
  "timestamp": "2025-10-07T...",
  "environment": "production"
}
```

### 4.3 Si hay errores
**Revisar logs en Render Dashboard:**
- **Deploy Logs**: Errores de instalación/build
- **Service Logs**: Errores de runtime/conexión

**Errores comunes:**
- ❌ Variables de entorno faltantes
- ❌ Credenciales de Cosmos DB incorrectas
- ❌ Problemas de red/firewall

---

## PASO 5: Probar integración completa con Flutter

### 5.1 Test de login
```bash
curl -X POST https://carnet-alumnos-nodes.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "24785914@uagro.mx",
    "matricula": "24785914"
  }'
```

**Respuesta esperada:**
```json
{
  "success": true,
  "token": "jwt_token_aqui",
  "matricula": "24785914",
  "message": "Login exitoso"
}
```

### 5.2 Test de carnet
```bash
curl -X GET https://carnet-alumnos-nodes.onrender.com/me/carnet \
  -H "Authorization: Bearer TU_JWT_TOKEN_AQUI"
```

### 5.3 Test desde Flutter Web
1. **Compilar Flutter:**
```bash
cd "C:\Users\gilbe\Documents\Carnet_digital _alumnos"
flutter build web
```

2. **Servir localmente:**
```bash
flutter run -d chrome
```

3. **Probar login** con credenciales reales de SASU

---

## PASO 6: Monitoreo y mantenimiento

### 6.1 URLs importantes
- **App URL**: https://carnet-alumnos-nodes.onrender.com
- **Render Dashboard**: https://dashboard.render.com
- **Health Check**: https://carnet-alumnos-nodes.onrender.com/ping

### 6.2 Logs y debugging
- **Service Logs**: En tiempo real en Render Dashboard
- **Deploy Logs**: Historial de deployments
- **Metrics**: CPU, memoria, requests/min

### 6.3 Updates y redeploys
- **Auto-deploy**: En cada push a `main`
- **Manual deploy**: Botón "Manual Deploy" en Dashboard
- **Rollback**: Historial de deployments disponible

---

## 🎯 CHECKLIST FINAL

### Backend Ready ✅
- [x] Código Node.js completo
- [x] Package.json configurado
- [x] Endpoints implementados (/auth/login, /me/carnet, /me/citas)
- [x] CORS y seguridad configurados
- [x] Documentación completa

### Deployment Ready ⏳
- [ ] Repositorio Git creado y pushed
- [ ] Servicio Render configurado
- [ ] Variables de entorno añadidas
- [ ] Credenciales SASU obtenidas
- [ ] Deploy exitoso
- [ ] Tests básicos funcionando

### Integration Ready ⏳
- [ ] Flutter Web conectando exitosamente
- [ ] Login funcionando con datos reales
- [ ] Carnet mostrando información SASU
- [ ] Citas cargando correctamente

---

## 🆘 SIGUIENTE PASO CRÍTICO

**🔑 OBTENER CREDENCIALES SASU**

Necesitas contactar al administrador de SASU para obtener:
1. **COSMOS_ENDPOINT** de Azure Cosmos DB
2. **COSMOS_KEY** de acceso
3. **Confirmación** de nombres de base de datos y contenedores

**Sin estas credenciales, el backend no podrá conectar a SASU.**

¿Ya tienes las credenciales de Azure Cosmos DB SASU?