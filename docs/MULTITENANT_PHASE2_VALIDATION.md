# Multitenant Phase 2 Validation

## Required Backend Commands

```powershell
python -m unittest discover
git diff --check
```

## Required Flutter Commands

```powershell
flutter pub get
dart format --output=none --set-exit-if-changed lib test
flutter analyze lib test
flutter test
flutter build windows --release --dart-define=APP_VARIANT=CRES
flutter build windows --release --dart-define=APP_VARIANT=LOYOLA_DEMO
flutter build windows --release --dart-define=APP_VARIANT=MULTITENANT --dart-define=MULTITENANT_API_BASE_URL=https://URL-STAGING
```

## Isolation Evidence

Automated tests must prove:

- LOYOLA can read LOYOLA demo data.
- LOYOLA cannot read, modify, delete, or discover CRES-STAGING data.
- CRES-STAGING and LOYOLA can share the same matricula without collision.
- Token tampering and refresh token reuse are rejected.
- Suspended tenants and blocked users lose access.
- Logs do not contain passwords or full tokens.

## Not Production Ready Until

- Staging Cosmos is created and verified.
- Flutter generic client logs in against a live staging URL.
- Render staging `/ready` is green.
- Manual demo credentials are rotated after presentation.
