from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Optional


REQUIRED_STAGING_ENV = {
    "APP_ENV",
    "ENABLE_MULTITENANT_ROUTES",
    "ENABLE_LEGACY_ROUTES",
    "COSMOS_ENDPOINT",
    "COSMOS_KEY",
    "COSMOS_DATABASE_NAME",
    "JWT_SECRET_KEY",
    "REFRESH_TOKEN_SECRET",
    "ALLOWED_ORIGINS",
}

DEFAULT_STAGING_DATABASE = "sasu_multitenant_staging"
PRODUCTION_NAME_MARKERS = {"prod", "production", "cres"}


@dataclass(frozen=True)
class StagingSettings:
    app_env: str
    enable_multitenant_routes: bool
    cosmos_endpoint: str
    cosmos_key: str
    cosmos_database_name: str
    allowed_origins: tuple[str, ...]
    enable_legacy_routes: bool = False
    allow_production_database: bool = False


class StagingConfigurationError(RuntimeError):
    pass


def parse_bool(value: str, *, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().strip('"').strip("'").lower() in {"1", "true", "yes", "y", "on"}


def parse_allowed_origins(value: str) -> tuple[str, ...]:
    origins = tuple(origin.strip() for origin in value.split(",") if origin.strip())
    if "*" in origins:
        raise StagingConfigurationError("ALLOWED_ORIGINS must not contain '*' for authenticated staging APIs")
    return origins


def database_name_looks_productive(name: str) -> bool:
    lowered = name.lower()
    if lowered == DEFAULT_STAGING_DATABASE:
        return False
    return any(marker in lowered for marker in PRODUCTION_NAME_MARKERS)


def load_staging_settings(env: Optional[dict] = None, *, required: Iterable[str] = REQUIRED_STAGING_ENV) -> StagingSettings:
    source = env or os.environ
    missing = sorted(key for key in required if not source.get(key))
    if missing:
        raise StagingConfigurationError(f"Missing required staging settings: {', '.join(missing)}")

    app_env = source["APP_ENV"].strip().lower()
    routes_enabled = parse_bool(source["ENABLE_MULTITENANT_ROUTES"])
    legacy_routes_enabled = parse_bool(source["ENABLE_LEGACY_ROUTES"])
    database_name = source["COSMOS_DATABASE_NAME"].strip()
    allow_production = source.get("ALLOW_PRODUCTION_DATABASE", "false").strip().lower() == "true"

    if app_env != "staging":
        raise StagingConfigurationError("APP_ENV must be staging")
    if not routes_enabled:
        raise StagingConfigurationError("ENABLE_MULTITENANT_ROUTES must be true in multitenant staging")
    if database_name_looks_productive(database_name) and not allow_production:
        raise StagingConfigurationError("Refusing to use a database name that looks productive")
    if database_name != DEFAULT_STAGING_DATABASE and not source.get("ALLOW_CUSTOM_STAGING_DATABASE"):
        raise StagingConfigurationError("Custom staging database requires ALLOW_CUSTOM_STAGING_DATABASE")
    if legacy_routes_enabled and database_name == DEFAULT_STAGING_DATABASE:
        raise StagingConfigurationError("ENABLE_LEGACY_ROUTES must be false for multitenant staging database")

    return StagingSettings(
        app_env=app_env,
        enable_multitenant_routes=routes_enabled,
        cosmos_endpoint=source["COSMOS_ENDPOINT"],
        cosmos_key=source["COSMOS_KEY"],
        cosmos_database_name=database_name,
        allowed_origins=parse_allowed_origins(source["ALLOWED_ORIGINS"]),
        enable_legacy_routes=legacy_routes_enabled,
        allow_production_database=allow_production,
    )
