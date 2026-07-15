# SASU Multitenancy Security Model

## Authentication Contract

```http
POST /auth/login
```

```json
{
  "institution_code": "LOYOLA-DEMO-2026",
  "username": "direccion.salud",
  "password": "..."
}
```

Login resolves the institution, validates tenant status/license, looks up the user inside that tenant, validates bcrypt password hash, verifies the user is active, emits a JWT, and records an audit event.

All invalid credential cases return the same generic message to avoid institution or user enumeration.

## JWT Claims

```json
{
  "sub": "user-id",
  "tenant_id": "loyola",
  "roles": ["tenant_admin"],
  "permissions": ["students.read"],
  "session_id": "uuid",
  "session_version": 1,
  "exp": 0
}
```

The token does not include passwords, full clinical notes, secrets, or personal clinical payloads.

## Tenant Context

`get_current_tenant_context()` validates:

- token signature and expiration;
- `sub`, `tenant_id`, and `session_id` claims;
- tenant existence and enabled status;
- tenant license validity;
- user existence inside the same tenant;
- active user state;
- session version for future revocation.

Flutter cannot override tenant scope after login. `tenant_id` in body, query string, URL path, or headers is ignored or rejected for institutional endpoints.

## Roles

Initial roles:

```text
platform_superadmin
tenant_admin
medical_staff
psychology_staff
nutrition_staff
dentistry_staff
student_services
auditor
```

Institutional endpoints verify permissions, not only role names.

Initial permissions:

```text
tenants.manage
users.manage
students.read
students.write
medical_records.read
medical_records.write
psychology_records.read
psychology_records.write
nutrition_records.read
nutrition_records.write
appointments.read
appointments.write
audit.read
```

## Cross-Tenant Access

If a resource exists in another tenant, institutional endpoints return `404 Recurso no encontrado`. They do not confirm that the resource exists elsewhere.

Cross-tenant attempts should be logged with action `cross_tenant_access.attempt` in future route expansion, without storing clinical bodies.

## Audit Logging

Structured audit events include:

- `tenant_id`;
- `actor_user_id`;
- `session_id`;
- action;
- resource type and id;
- UTC timestamp;
- result;
- normalized IP when available;
- user agent;
- `correlation_id`.

Audit details redact:

- passwords;
- password hashes;
- tokens;
- authorization headers;
- full clinical notes;
- full expediente bodies.

## File Storage

Internal object paths must be generated server-side:

```text
tenants/{tenant_id}/{resource_type}/{resource_id}/{safe_filename}
```

The client cannot choose a different tenant through file names or paths.

## Revocation Preparation

JWT includes `session_id` and `session_version`. Phase 1 validates `session_version` against the user record. A future session registry can revoke a single session ID.
