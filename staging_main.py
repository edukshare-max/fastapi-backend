from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from multitenancy_audit import InMemoryAuditLogger
from multitenancy_auth import InstitutionalAuthService
from multitenancy_provisioning import MULTITENANT_CONTAINERS
from multitenancy_repositories import CosmosTenantAwareStudentRepository, CosmosTenantRepository, CosmosUserRepository
from multitenancy_routes import create_multitenancy_health_router, create_multitenancy_router
from multitenancy_staging_config import DEFAULT_STAGING_DATABASE, StagingConfigurationError, load_staging_settings


def _require_exact_staging_configuration():
    settings = load_staging_settings()
    if settings.app_env != "staging":
        raise StagingConfigurationError("APP_ENV must be staging")
    if not settings.enable_multitenant_routes:
        raise StagingConfigurationError("ENABLE_MULTITENANT_ROUTES must be true")
    if settings.enable_legacy_routes:
        raise StagingConfigurationError("ENABLE_LEGACY_ROUTES must be false")
    if settings.cosmos_database_name != DEFAULT_STAGING_DATABASE:
        raise StagingConfigurationError("COSMOS_DATABASE_NAME must be sasu_multitenant_staging")
    if settings.allow_production_database:
        raise StagingConfigurationError("ALLOW_PRODUCTION_DATABASE must be false")
    return settings


def _log_staging_startup(app: FastAPI) -> None:
    settings = app.state.multitenant_staging_settings
    print(f"APP_ENV={settings.app_env}")
    print(f"ENABLE_MULTITENANT_ROUTES={str(settings.enable_multitenant_routes).lower()}")
    print(f"ENABLE_LEGACY_ROUTES={str(settings.enable_legacy_routes).lower()}")
    print(f"COSMOS_DATABASE_NAME={settings.cosmos_database_name}")
    registered_routes = sorted(
        {
            f"{','.join(sorted(route.methods or []))} {route.path}"
            for route in app.routes
            if hasattr(route, "methods")
        }
    )
    print(f"REGISTERED_ROUTES={registered_routes}")


settings = _require_exact_staging_configuration()

app = FastAPI(
    title="SASU Multitenant Staging",
    version="staging",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.state.multitenant_staging_settings = settings
app.state.multitenant_auth_service = InstitutionalAuthService(
    CosmosTenantRepository(),
    CosmosUserRepository(),
    InMemoryAuditLogger(),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
)


@app.middleware("http")
async def add_staging_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(create_multitenancy_health_router([item.name for item in MULTITENANT_CONTAINERS]))
app.include_router(create_multitenancy_router(CosmosTenantAwareStudentRepository()), prefix="/v2", tags=["multitenancy"])

_log_staging_startup(app)
