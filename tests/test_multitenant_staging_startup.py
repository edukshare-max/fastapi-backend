import importlib
import asyncio
import io
import os
import sys
import unittest
from contextlib import contextmanager, redirect_stdout
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi import FastAPI

from multitenancy_provisioning import MULTITENANT_CONTAINERS
from multitenancy_staging_config import StagingConfigurationError, load_staging_settings


STAGING_ENV = {
    "APP_ENV": "staging",
    "ENABLE_MULTITENANT_ROUTES": "true",
    "ENABLE_LEGACY_ROUTES": "false",
    "COSMOS_ENDPOINT": "https://placeholder.documents.azure.com:443/",
    "COSMOS_KEY": "placeholder-key",
    "COSMOS_DATABASE_NAME": "sasu_multitenant_staging",
    "ALLOW_PRODUCTION_DATABASE": "false",
    "JWT_SECRET_KEY": "placeholder-jwt",
    "REFRESH_TOKEN_SECRET": "placeholder-refresh",
    "ALLOWED_ORIGINS": "https://staging-client.example.invalid",
}


LEGACY_ENV_KEYS = {
    "COSMOS_CONTAINER_CARNETS",
    "COSMOS_CONTAINER_NOTAS",
    "COSMOS_CONTAINER_PROMOCIONES_SALUD",
    "COSMOS_CONTAINER_VACUNACION",
    "COSMOS_CONTAINER_CITAS",
    "COSMOS_CONTAINER_USUARIOS",
    "COSMOS_CONTAINER_AUDITORIA",
}


@contextmanager
def patched_env(values, remove=()):
    previous = {key: os.environ.get(key) for key in set(values) | set(remove)}
    for key in remove:
        os.environ.pop(key, None)
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def import_staging_main_fresh():
    for module_name in [
        "staging_main",
        "main",
        "cosmos_helper",
        "auth_service",
        "auth_models",
        "multitenancy_auth",
        "multitenancy_provisioning",
    ]:
        sys.modules.pop(module_name, None)
    return importlib.import_module("staging_main")


def route_endpoint(app, path):
    for route in app.routes:
        if getattr(route, "path", None) == path:
            return route.endpoint
    raise AssertionError(f"Route not found: {path}")


class FakeCosmosDatabase:
    def __init__(self, containers=None, fail=False):
        self.containers = containers or []
        self.fail = fail

    def list_containers(self):
        if self.fail:
            raise RuntimeError("cosmos unavailable with sensitive connection details")
        return [{"id": container} for container in self.containers]


class FakeCosmosClient:
    def __init__(self, endpoint, credential=None, containers=None, fail=False):
        self.endpoint = endpoint
        self.credential = credential
        self.database_name = None
        self.database = FakeCosmosDatabase(containers or [item.name for item in MULTITENANT_CONTAINERS], fail=fail)

    def get_database_client(self, database_name):
        self.database_name = database_name
        return self.database


class MultitenantStagingStartupTest(unittest.TestCase):
    def import_staging_main(self):
        with patched_env(STAGING_ENV, remove=LEGACY_ENV_KEYS):
            return import_staging_main_fresh()

    def test_staging_main_app_exists_without_legacy_variables(self):
        module = self.import_staging_main()
        self.assertIsInstance(module.app, FastAPI)
        with open("staging_main.py", encoding="utf-8") as handle:
            self.assertEqual(handle.read().count("FastAPI("), 1)
        self.assertEqual(module.app.state.multitenant_staging_settings.cosmos_database_name, "sasu_multitenant_staging")
        self.assertFalse(hasattr(module, "carnets"))
        self.assertNotIn("main", sys.modules)
        self.assertNotIn("auth_service", sys.modules)
        self.assertNotIn("auth_models", sys.modules)

    def test_legacy_routes_are_not_registered_when_disabled(self):
        module = self.import_staging_main()
        paths = {route.path for route in module.app.routes}
        self.assertNotIn("/carnet/{id}", paths)
        self.assertNotIn("/auth/login", paths)
        self.assertNotIn("/updates/latest", paths)
        self.assertNotIn("/legacy/health", paths)
        self.assertTrue(all(path in {"/health", "/ready"} or path.startswith("/v2") for path in paths))

    def test_v2_routes_are_registered(self):
        module = self.import_staging_main()
        paths = {route.path for route in module.app.routes}
        self.assertIn("/v2/public/institution/resolve", paths)
        self.assertIn("/v2/auth/login", paths)
        self.assertIn("/v2/students", paths)

    def test_health_works_in_staging(self):
        module = self.import_staging_main()
        module.app.state.cosmos_client_factory = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("health must not create a Cosmos client")
        )
        response = asyncio.run(route_endpoint(module.app, "/health")())
        self.assertEqual(response, {"status": "ok", "service": "sasu-multitenant-staging"})

    def test_string_boolean_values_are_parsed_robustly(self):
        env = dict(STAGING_ENV, ENABLE_MULTITENANT_ROUTES=" 'true' ", ENABLE_LEGACY_ROUTES=' "false" ')
        with patched_env(env, remove=LEGACY_ENV_KEYS):
            module = import_staging_main_fresh()
        self.assertTrue(module.app.state.multitenant_staging_settings.enable_multitenant_routes)
        self.assertFalse(module.app.state.multitenant_staging_settings.enable_legacy_routes)
        paths = {route.path for route in module.app.routes}
        self.assertIn("/health", paths)
        self.assertIn("/ready", paths)
        self.assertIn("/v2/auth/login", paths)

    def test_ready_reports_staging_database(self):
        module = self.import_staging_main()
        client = FakeCosmosClient("endpoint", credential="secret")
        module.app.state.cosmos_client_factory = lambda *args, **kwargs: client
        request = SimpleNamespace(app=module.app)
        body = asyncio.run(route_endpoint(module.app, "/ready")(request))
        self.assertEqual(body["database"], "sasu_multitenant_staging")
        self.assertEqual(body["environment"], "staging")
        self.assertEqual(body["containers"], 8)
        self.assertEqual(client.database_name, "sasu_multitenant_staging")

    def test_ready_is_registered_without_v2_prefix(self):
        module = self.import_staging_main()
        paths = {route.path for route in module.app.routes}
        self.assertIn("/ready", paths)
        self.assertNotIn("/v2/ready", paths)

    def test_ready_returns_503_when_cosmos_is_unavailable(self):
        module = self.import_staging_main()
        module.app.state.cosmos_client_factory = lambda *args, **kwargs: FakeCosmosClient(
            "endpoint", credential="secret", fail=True
        )
        request = SimpleNamespace(app=module.app)
        with self.assertRaises(HTTPException) as exc:
            asyncio.run(route_endpoint(module.app, "/ready")(request))
        self.assertEqual(exc.exception.status_code, 503)
        self.assertEqual(exc.exception.detail, "Staging no disponible")
        self.assertNotIn("sensitive", exc.exception.detail)

    def test_ready_verifies_all_eight_containers(self):
        module = self.import_staging_main()
        containers = [item.name for item in MULTITENANT_CONTAINERS if item.name != "licenses_v2"]
        module.app.state.cosmos_client_factory = lambda *args, **kwargs: FakeCosmosClient(
            "endpoint", credential="secret", containers=containers
        )
        request = SimpleNamespace(app=module.app)
        with self.assertRaises(HTTPException) as exc:
            asyncio.run(route_endpoint(module.app, "/ready")(request))
        self.assertEqual(exc.exception.status_code, 503)
        self.assertEqual(exc.exception.detail, "Staging no disponible")

    def test_staging_rejects_sasu_database(self):
        env = dict(STAGING_ENV, COSMOS_DATABASE_NAME="SASU")
        with self.assertRaises(StagingConfigurationError):
            load_staging_settings(env)

    def test_no_fallback_to_carnets_container_exists_in_staging(self):
        module = self.import_staging_main()
        paths = {route.path for route in module.app.routes}
        self.assertNotIn("/carnet/search", paths)
        self.assertFalse(hasattr(module, "carnets"))

    def test_health_route_is_not_duplicated(self):
        module = self.import_staging_main()
        paths = [route.path for route in module.app.routes]
        self.assertEqual(paths.count("/health"), 1)

    def test_legacy_roles_and_campus_are_not_logged_in_staging(self):
        output = io.StringIO()
        with patched_env(STAGING_ENV, remove=LEGACY_ENV_KEYS):
            with redirect_stdout(output):
                import_staging_main_fresh()
        text = output.getvalue()
        self.assertIn("APP_ENV=staging", text)
        self.assertIn("ENABLE_MULTITENANT_ROUTES=true", text)
        self.assertIn("ENABLE_LEGACY_ROUTES=false", text)
        self.assertIn("/health", text)
        self.assertIn("/ready", text)
        self.assertIn("/v2/public/institution/resolve", text)
        self.assertIn("/v2/auth/login", text)
        self.assertNotIn("AuthService inicializado correctamente", text)
        self.assertNotIn("Roles disponibles", text)
        self.assertNotIn("Campus disponibles", text)

    def test_staging_main_rejects_legacy_routes_enabled(self):
        env = dict(STAGING_ENV, ENABLE_LEGACY_ROUTES="true")
        with patched_env(env, remove=LEGACY_ENV_KEYS):
            with self.assertRaises(StagingConfigurationError):
                import_staging_main_fresh()

    def test_render_staging_yaml_contains_required_runtime_keys(self):
        with open("render.staging.yaml", encoding="utf-8") as handle:
            text = handle.read()
        required = {
            "APP_ENV",
            "ENABLE_MULTITENANT_ROUTES",
            "ENABLE_LEGACY_ROUTES",
            "COSMOS_ENDPOINT",
            "COSMOS_KEY",
            "COSMOS_DATABASE_NAME",
            "ALLOW_PRODUCTION_DATABASE",
            "JWT_SECRET_KEY",
            "REFRESH_TOKEN_SECRET",
            "ALLOWED_ORIGINS",
        }
        for key in required:
            self.assertIn(f"key: {key}", text)
        self.assertIn('value: "false"', text)
        self.assertIn("key: PYTHON_VERSION", text)
        self.assertIn('value: "3.13.7"', text)
        self.assertIn("pip install -r requirements.staging.txt", text)
        self.assertIn("uvicorn staging_main:app", text)


if __name__ == "__main__":
    unittest.main()
