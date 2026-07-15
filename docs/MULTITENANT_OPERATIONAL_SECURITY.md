# Multitenant Operational Security

## Isolation Rules

- The authenticated token supplies `tenant_id`.
- Body, query, URL, or header tenant values cannot switch scope.
- Other-tenant resources return 404.
- Uncontracted modules return 403.

## Authentication

- Passwords are bcrypt hashes.
- JWTs are signed and expire.
- Refresh tokens rotate and are stored only as hashes.
- Logout and session revocation invalidate sessions.
- Suspended tenants and disabled users lose access.

## Logging

Logs and audit events must not store:

- passwords;
- password hashes;
- full tokens;
- clinical notes;
- complete expediente bodies.

## Incident Response

1. Suspend tenant or user.
2. Revoke sessions.
3. Rotate secrets if token leakage is suspected.
4. Review audit logs by tenant and correlation id.
5. Keep production and staging investigations separate.

## Production Readiness Gaps

- Real Cosmos persistence must be validated in staging.
- Superadmin panel is not complete.
- Legacy endpoints still need tenant-aware migration.
- Clinical records need dedicated repository tests before real data.
