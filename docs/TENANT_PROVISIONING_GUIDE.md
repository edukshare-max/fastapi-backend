# Tenant Provisioning Guide

## CLI

Dry-run is the default:

```powershell
python multitenancy_provisioning.py tenant create --id loyola-demo --code LOYOLA-DEMO-2026 --name LOYOLA
python multitenancy_provisioning.py tenant suspend --id loyola-demo
python multitenancy_provisioning.py user create-admin --tenant-id loyola-demo --username admin.loyola
python multitenancy_provisioning.py user reset-password --tenant-id loyola-demo --username admin.loyola
python multitenancy_provisioning.py session revoke --session-id <uuid>
```

Use `--apply` only in staging after reviewing the printed plan.

## Temporary Passwords

Temporary passwords are generated randomly and printed once. They are not written to files. Users must change them at first access.

## Branding

```powershell
python multitenancy_provisioning.py tenant branding --id loyola-demo --primary-color "#164E8A" --secondary-color "#D8A21B"
```

Only HTTPS or embedded trusted logo references should be used.

## Modules

```powershell
python multitenancy_provisioning.py tenant modules --id loyola-demo --enable students appointments audit
```

Backend authorization still validates permissions and modules on each endpoint.
