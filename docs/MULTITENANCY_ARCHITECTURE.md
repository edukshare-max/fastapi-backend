# SASU Multitenancy Architecture

## Scope

Phase 1 adds the backend foundation for multiple institutions on one SASU backend. It does not migrate production data, remove the LOYOLA_DEMO Flutter variant, or enable the new routes by default.

## Current Backend Diagnosis

- Backend: FastAPI in `temp_backend`, deployed as a separate service from the Flutter Windows app.
- Current auth: `/auth/login` issues JWTs with `sub`, `rol`, and `campus`.
- JWT signing: `python-jose`, `HS256`, secret read from server environment with a generated fallback.
- Passwords: `passlib` bcrypt through `AuthService.hash_password()` and `verify_password()`.
- Users: `UserInDB` contains `username`, `email`, `password_hash`, `rol`, `campus`, `activo`, failed attempts, and lockout timestamp.
- Cosmos access: `CosmosDBHelper` wraps `create_item`, `read_item`, `query_items`, and `upsert_item`; `query_items` currently enables cross-partition queries.
- Current containers include carnets, notas, promociones, vacunacion, appointments, referrals, tickets, ticket_messages, and update metadata. Environment variables choose exact container names.
- Current partition keys include `/id`, `/matricula`, `/student/matricula`, `/campus`, and `/ticketId`.
- Risky current patterns: some appointment/referral/ticket lookups query by `id` or `matricula` without tenant scoping. A caller who knows an identifier could potentially discover another institution's record once the backend serves more than one institution.
- Files: current phase adds tenant file path helpers only; no public permanent links are introduced.
- Roles: current roles are legacy Spanish role names. Phase 1 adds a tenant permission model without deleting legacy roles.
- Audit: current audit exists in auth models; phase 1 adds structured audit events for tenant-aware flows.
- Tests: existing backend tests cover referrals and tickets. Phase 1 adds isolation tests for tenant context.

No secrets or full production URLs are documented here.

## Target Model

```text
Tenant
  id: stable internal tenant_id
  code: institutional login code
  name: visible name
  status: trial | active | suspended | expired | disabled
  plan
  license_expires_at
  student_limit
  user_limit
  enabled_modules
  branding
  created_at
  updated_at
```

The visible institution name is never the only internal identifier. All institutional data uses `tenant_id`.

## Architecture

```text
Flutter CRES / LOYOLA_DEMO
        |
        v
POST /v2/auth/login
        |
Institution code resolver -> tenants_v2
        |
Tenant user lookup -> users_v2 partitioned by tenant_id
        |
JWT with tenant_id, roles, permissions, session_id
        |
get_current_tenant_context()
        |
Tenant-aware repositories
        |
Cosmos containers partitioned by tenant_id
```

## Route Activation

The new router is opt-in:

```text
ENABLE_MULTITENANT_ROUTES=true
```

By default, existing CRES and LOYOLA_DEMO behavior remains unchanged.

## Tenant-Aware Repositories

Institutional repositories must require `tenant_id`:

```python
students.get_student(tenant_id=context.tenant_id, student_id=student_id)
students.list_students(tenant_id=context.tenant_id)
students.update_student(tenant_id=context.tenant_id, student_id=student_id, updates=payload)
```

Repositories must not expose institutional methods such as `get_student(student_id)` without tenant scope.

## Proposed Containers

| Container | Partition key | Notes |
| --- | --- | --- |
| `tenants_v2` | `/id` | Tenant registry |
| `users_v2` | `/tenant_id` | Users scoped to tenant |
| `students_v2` | `/tenant_id` | Allows same matricula across tenants |
| `clinical_records_v2` | `/tenant_id/student_id/id` | Hierarchical candidate |
| `appointments_v2` | `/tenant_id` | Tenant queue |
| `referrals_v2` | `/tenant_id` | Tenant referral isolation |
| `audit_logs_v2` | `/tenant_id/month/id` | Hierarchical candidate |
| `licenses_v2` | `/tenant_id` | Licensing state |

`multitenancy_provisioning.azure_cosmos_supports_hierarchical_partition_keys()` checks the installed SDK before enabling hierarchical partition key candidates.

## Seed Tenants for Staging

```json
{"id":"cres","code":"CRES-INTERNAL","name":"CRES","status":"active","plan":"internal"}
{"id":"loyola","code":"LOYOLA-DEMO-2026","name":"LOYOLA","status":"trial","plan":"demo"}
```

## Limits

- No production container is created by default.
- No production data is migrated.
- Flutter is not wired to the new login flow in this phase.
- Superadmin endpoints are intentionally not implemented in institutional routes.
