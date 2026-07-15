# SASU Multitenancy Migration Plan

## Phase 1 Status

Implemented foundation only:

- tenant model;
- tenant-aware auth service;
- tenant context dependency;
- tenant-aware student repository contract;
- staging container definitions;
- dry-run migration script;
- isolation tests.

Production data and containers are not modified.

## Staging Container Creation

Script:

```text
create_multitenant_containers.py
```

Default behavior is dry-run. Creation requires:

```text
SASU_ENVIRONMENT=staging
SASU_MULTITENANT_STAGING_CONFIRM=CREATE_STAGING_CONTAINERS
```

The script checks the installed Azure Cosmos SDK before creating hierarchical partition key candidates.

## CRES Dry-Run Migration

Script:

```text
migrate_cres_to_multitenant.py
```

Default behavior:

1. reads source JSONL;
2. adds `tenant_id: cres` in memory;
3. validates required fields;
4. detects duplicates;
5. produces a JSON report;
6. writes no destination records;
7. generates per-record SHA-256 control hashes.

`--write` intentionally raises in phase 1. Write mode must be implemented only after staging validation and approval.

## LOYOLA Demo Tenant

LOYOLA staging seed is fictitious:

```json
{
  "id": "loyola",
  "code": "LOYOLA-DEMO-2026",
  "name": "LOYOLA",
  "status": "trial",
  "plan": "demo"
}
```

No CRES data is copied into LOYOLA.

## Suggested Sequence

1. Deploy the foundation to staging with multitenant routes disabled.
2. Run backend tests.
3. Create staging v2 containers with explicit confirmation.
4. Seed CRES and LOYOLA tenants in staging only.
5. Run CRES dry-run migration and review counts/hashes.
6. Enable `/v2` routes in staging only.
7. Connect a non-production Flutter client to `/v2/auth/login`.
8. Run isolation, permission, and audit checks.
9. Prepare production migration runbook.

## Reversal Plan

- Keep existing legacy routes and containers untouched.
- Disable `ENABLE_MULTITENANT_ROUTES`.
- Do not point Flutter production builds at `/v2`.
- Keep v2 containers separate until migration is approved.
- Roll back by removing staging-only environment variables.

## Pending Risks

- Existing legacy routes still use campus/matricula scoping, not tenant scoping.
- `CosmosDBHelper.query_items()` enables cross-partition queries globally.
- Real production data may contain duplicate IDs or missing required fields.
- Hierarchical partition keys depend on Azure Cosmos SDK and account support.
- Superadmin APIs need a separate authorization boundary.
- Full clinical record repositories still need tenant-aware implementations.
