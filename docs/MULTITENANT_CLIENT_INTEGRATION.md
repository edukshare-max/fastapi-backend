# Multitenant Client Integration

## Build Variant

```text
APP_VARIANT=MULTITENANT
```

The default variant remains CRES. LOYOLA_DEMO local remains available and does not require a server.

## Required Dart Define

```powershell
--dart-define=MULTITENANT_API_BASE_URL=https://staging-url
```

If the URL is absent, the client must show a configuration error and must not fall back to the CRES API.

## Startup Flow

1. User enters institutional code.
2. Client calls `POST /v2/public/institution/resolve`.
3. Client displays institution name, demo status, branding, and modules.
4. User logs in via `POST /v2/auth/login`.
5. After login, tenant scope comes only from the token.

Flutter must never send `tenant_id` to select data.

## Token Storage

Use Windows secure storage and namespace keys by environment:

```text
sasu_cres
sasu_loyola_demo
sasu_multitenant
```

Do not store passwords.

## Slow Staging Backend

The client should show a clear startup message, use limited retries, and avoid repeatedly sending credentials while Render wakes up.
