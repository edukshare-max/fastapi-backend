# 🔐 Credenciales del Administrador

## Información de Acceso

**Panel Web Administrativo:**
- URL: https://fastapi-backend-o7ks.onrender.com/admin

**Credenciales del Primer Administrador:**
- **Usuario:** `DireccionInnovaSalud`
- **Contraseña:** `Admin2025`
- **Campus:** `llano-largo`
- **Rol:** `admin` (acceso completo)
- **Departamento:** Direccion

---

## Estado del Sistema

✅ **Backend desplegado en:** https://fastapi-backend-o7ks.onrender.com
✅ **Contenedores Cosmos DB creados:**
  - `usuarios` (partition key: `/id`)
  - `auditoria` (partition key: `/id`)
✅ **Panel web activo:** `/admin`
✅ **Endpoints de autenticación:**
  - `POST /auth/login` - Iniciar sesión
  - `POST /auth/register` - Registrar nuevo usuario (requiere admin)
  - `GET /auth/me` - Obtener usuario actual
  - `GET /auth/users` - Listar usuarios (requiere admin)
  - `PATCH /auth/users/{id}` - Actualizar usuario (requiere admin)
  - `GET /auth/audit-logs` - Ver logs de auditoría (requiere admin)

---

## Próximos Pasos

1. **Verificar acceso al panel web** con las credenciales arriba
2. **Crear usuarios de prueba:**
   - Un médico
   - Un nutricionista
   - Un recepcionista
3. **Probar funcionalidades del panel:**
   - Crear usuarios
   - Editar usuarios
   - Activar/desactivar usuarios
   - Ver logs de auditoría
   - Exportar logs a CSV

4. **Integración con Flutter:**
   - FASE 8: Pantalla de Login
   - FASE 9: Gestión de sesión
   - FASE 10: Restricciones por rol

---

## Roles Disponibles

- **admin**: Acceso completo al sistema
- **medico**: Carnets, notas, citas, vacunación
- **nutricion**: Carnets (lectura), notas de nutrición, citas
- **psicologia**: Carnets (lectura), notas de psicología, citas
- **odontologia**: Carnets (lectura), notas de odontología, citas
- **enfermeria**: Carnets (lectura), vacunación
- **recepcion**: Carnets (lectura), citas
- **lectura**: Solo lectura de carnets

---

## Campus Disponibles

- `llano-largo` - Campus Llano Largo (principal)
- `acapulco` - Campus Acapulco
- `chilpancingo` - Campus Chilpancingo
- `taxco` - Campus Taxco
- `iguala` - Campus Iguala
- `zihuatanejo` - Campus Zihuatanejo

---

## Seguridad

🔒 **Características de seguridad implementadas:**
- Tokens JWT con expiración de 8 horas
- Contraseñas hasheadas con bcrypt
- Protección contra fuerza bruta (5 intentos, bloqueo 30 min)
- Auditoría completa de todas las acciones
- Validación de fortaleza de contraseñas
- Permisos granulares por rol

---

## Soporte

Para problemas o dudas:
- Revisar logs en Render.com Dashboard
- Consultar documentación en `README_AUTH.md`
- Verificar logs de auditoría en el panel web
