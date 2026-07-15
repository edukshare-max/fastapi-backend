# Multitenant Staging Deployment

## Service

Suggested Render service name:

```text
sasu-multitenant-staging
```

Use `render.staging.yaml`. Do not replace the production Render file.

## Required Variables

```text
APP_ENV=staging
ENABLE_MULTITENANT_ROUTES=true
COSMOS_ENDPOINT=<secret>
COSMOS_KEY=<secret>
COSMOS_DATABASE_NAME=sasu_multitenant_staging
JWT_SECRET_KEY=<secret>
REFRESH_TOKEN_SECRET=<secret>
ALLOWED_ORIGINS=https://staging-client.example
ALLOW_PRODUCTION_DATABASE=false
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=14
LOGIN_RATE_LIMIT=10
```

Never commit real secrets. Staging refuses ambiguous or production-looking database names.

## Containers

Plan first:

```powershell
python create_multitenant_containers.py --dry-run
```

Apply only after reviewing environment and plan:

```powershell
python create_multitenant_containers.py --apply
```

The script creates missing containers only. It does not delete containers or change existing partition keys.

## Health Checks

```text
GET /health
GET /ready
```

`/ready` confirms staging configuration without exposing secrets or infrastructure details.

## Not Done

No production deployment was executed by this phase. No CRES production data is migrated.
