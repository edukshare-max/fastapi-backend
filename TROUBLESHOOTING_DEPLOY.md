# 🔍 Troubleshooting Deploy - Render.com

## ❌ Error Detectado

**Status:** Instance failed (exit code 3)
**Timestamp:** October 10, 2025 at 11:56 AM
**Service:** drqzl

---

## 🔎 Posibles Causas

### 1. **Error de Importación** (Más probable)
Los nuevos archivos `auth_models.py` o `auth_service.py` tienen errores de sintaxis o importaciones faltantes.

### 2. **Variables de Entorno Faltantes**
El backend necesita las nuevas variables:
- `COSMOS_CONTAINER_USUARIOS`
- `COSMOS_CONTAINER_AUDITORIA`
- `JWT_SECRET_KEY`

### 3. **Dependencias No Instaladas**
Render.com no instaló las nuevas dependencias:
- `python-jose[cryptography]`
- `passlib[bcrypt]`
- `python-multipart`

---

## 🛠️ Solución Rápida

### **Paso 1: Verificar requirements.txt**

El archivo debe tener:
```
python-jose[cryptography]
passlib[bcrypt]
python-multipart
```

### **Paso 2: Agregar Variables de Entorno en Render.com**

Ve a: Render Dashboard > fastapi-backend > Environment

Agregar:
```
COSMOS_CONTAINER_USUARIOS=usuarios
COSMOS_CONTAINER_AUDITORIA=auditoria
JWT_SECRET_KEY=tu-secret-key-super-segura-cambiala-12345678
```

### **Paso 3: Verificar Logs en Render.com**

Dashboard > fastapi-backend > Logs

Buscar líneas rojas con:
- `ImportError`
- `ModuleNotFoundError`
- `KeyError`
- `SyntaxError`

---

## 📝 Checklist de Verificación

- [ ] requirements.txt tiene las 3 nuevas dependencias
- [ ] Variables de entorno configuradas en Render
- [ ] auth_models.py y auth_service.py no tienen errores de sintaxis
- [ ] Contenedores 'usuarios' y 'auditoria' existen en Cosmos DB

---

## 🚨 Si el error persiste

Revisar logs específicos de Render.com para identificar el error exacto.
