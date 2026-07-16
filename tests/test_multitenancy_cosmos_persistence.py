import io
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from multitenancy_auth import InstitutionalAuthService, hash_password, verify_password
from multitenancy_audit import InMemoryAuditLogger
from multitenancy_models import InstitutionalLoginRequest, MultitenantUser, Tenant, TenantStatus
from multitenancy_provisioning import (
    LOYOLA_ADMIN_USER_ID,
    LOYOLA_ADMIN_USERNAME,
    LOYOLA_TENANT_CODE,
    LOYOLA_TENANT_ID,
    provision_loyola_demo,
    reset_loyola_password,
)
from multitenancy_repositories import (
    CosmosTenantRepository,
    CosmosUserRepository,
    InMemoryTenantAwareStudentRepository,
    InMemoryTenantRepository,
    InMemoryUserRepository,
)
from multitenancy_staging_config import StagingConfigurationError


STAGING_ENV = {
    "APP_ENV": "staging",
    "ENABLE_MULTITENANT_ROUTES": "true",
    "ENABLE_LEGACY_ROUTES": "false",
    "COSMOS_ENDPOINT": "https://placeholder.documents.azure.com:443/",
    "COSMOS_KEY": "secret-cosmos-key",
    "COSMOS_DATABASE_NAME": "sasu_multitenant_staging",
    "ALLOW_PRODUCTION_DATABASE": "false",
    "JWT_SECRET_KEY": "secret-jwt",
    "REFRESH_TOKEN_SECRET": "secret-refresh",
    "ALLOWED_ORIGINS": "https://staging-client.example.invalid",
}


class FakeCosmosHelper:
    def __init__(self, partition_key):
        self.partition_key = partition_key
        self.items = {}
        self.writes = []

    def _key(self, item_id, partition_value):
        return (partition_value, item_id)

    def read_item(self, item_id, partition_key):
        key = self._key(item_id, partition_key)
        if key not in self.items:
            raise KeyError(item_id)
        return dict(self.items[key])

    def create_item(self, item):
        partition_field = self.partition_key.lstrip("/")
        partition_value = item[partition_field]
        stored = dict(item)
        self.items[self._key(stored["id"], partition_value)] = stored
        self.writes.append(("create", stored["id"], partition_value))
        return dict(stored)

    def upsert_item(self, item, partition_value):
        stored = dict(item)
        self.items[self._key(stored["id"], partition_value)] = stored
        self.writes.append(("upsert", stored["id"], partition_value))
        return dict(stored)

    def query_items(self, sql, params=None):
        values = {param["name"]: param["value"] for param in (params or [])}
        results = []
        for item in self.items.values():
            if "@tenant_id" in values and item.get("tenant_id") != values["@tenant_id"]:
                continue
            if "@code" in values and item.get("code") != values["@code"] and item.get("code_upper") != values["@code"]:
                continue
            if (
                "@username" in values
                and item.get("username") != values["@username"]
                and item.get("username_normalized") != values["@username"]
            ):
                continue
            results.append(dict(item))
        return results


class CosmosPersistenceTest(unittest.TestCase):
    def test_tenant_loyola_persists_in_tenants_v2_repository(self):
        helper = FakeCosmosHelper("/id")
        repo = CosmosTenantRepository(helper)
        tenant = Tenant(id=LOYOLA_TENANT_ID, code=LOYOLA_TENANT_CODE, name="LOYOLA", status=TenantStatus.TRIAL)

        repo.create(tenant)
        restarted_repo = CosmosTenantRepository(helper)

        self.assertEqual(restarted_repo.get_by_id(LOYOLA_TENANT_ID).name, "LOYOLA")
        self.assertEqual(restarted_repo.get_by_code(LOYOLA_TENANT_CODE).id, LOYOLA_TENANT_ID)

    def test_user_persists_in_users_v2_with_tenant_partition(self):
        helper = FakeCosmosHelper("/tenant_id")
        repo = CosmosUserRepository(helper)
        user = MultitenantUser(
            id=LOYOLA_ADMIN_USER_ID,
            tenant_id=LOYOLA_TENANT_ID,
            username=LOYOLA_ADMIN_USERNAME,
            password_hash="$2b$hash-only",
            roles=["tenant_admin"],
        )

        repo.create(user)
        restarted_repo = CosmosUserRepository(helper)

        self.assertEqual(restarted_repo.get_by_id(LOYOLA_TENANT_ID, LOYOLA_ADMIN_USER_ID).username, LOYOLA_ADMIN_USERNAME)
        self.assertEqual(
            restarted_repo.get_by_username(LOYOLA_TENANT_ID, LOYOLA_ADMIN_USERNAME).id,
            LOYOLA_ADMIN_USER_ID,
        )
        self.assertIn(("create", LOYOLA_ADMIN_USER_ID, LOYOLA_TENANT_ID), helper.writes)

    def test_same_username_in_different_tenants_does_not_collide(self):
        helper = FakeCosmosHelper("/tenant_id")
        repo = CosmosUserRepository(helper)
        repo.create(
            MultitenantUser(
                id="loyola-admin",
                tenant_id="loyola-demo",
                username="admin.demo",
                password_hash="$2b$hash",
            )
        )
        repo.create(
            MultitenantUser(
                id="cres-admin",
                tenant_id="cres-staging",
                username="admin.demo",
                password_hash="$2b$hash",
            )
        )

        self.assertEqual(repo.get_by_username("loyola-demo", "admin.demo").id, "loyola-admin")
        self.assertEqual(repo.get_by_username("cres-staging", "admin.demo").id, "cres-admin")

    def test_apply_provisions_hash_login_and_temporary_password_flag(self):
        tenants = InMemoryTenantRepository([])
        users = InMemoryUserRepository([])
        students = InMemoryTenantAwareStudentRepository([])
        output = io.StringIO()

        provision_loyola_demo(
            apply=True,
            tenant_repo=tenants,
            user_repo=users,
            students_repo=students,
            env=STAGING_ENV,
            output=output,
        )
        temporary_password = self._temporary_password_from_output(output.getvalue())
        stored_user = users.get_by_id(LOYOLA_TENANT_ID, LOYOLA_ADMIN_USER_ID)

        self.assertIsNotNone(tenants.get_by_id(LOYOLA_TENANT_ID))
        self.assertIsNotNone(stored_user)
        self.assertNotEqual(stored_user.password_hash, temporary_password)
        self.assertTrue(verify_password(temporary_password, stored_user.password_hash))

        service = InstitutionalAuthService(tenants, users, InMemoryAuditLogger())
        response = service.login(
            InstitutionalLoginRequest(
                institution_code=LOYOLA_TENANT_CODE,
                username=LOYOLA_ADMIN_USERNAME,
                password=temporary_password,
            )
        )
        self.assertEqual(response.tenant_id, LOYOLA_TENANT_ID)
        self.assertTrue(response.requires_password_change)

    def test_restart_repositories_does_not_remove_user(self):
        tenant_helper = FakeCosmosHelper("/id")
        user_helper = FakeCosmosHelper("/tenant_id")
        students = InMemoryTenantAwareStudentRepository([])
        output = io.StringIO()

        provision_loyola_demo(
            apply=True,
            tenant_repo=CosmosTenantRepository(tenant_helper),
            user_repo=CosmosUserRepository(user_helper),
            students_repo=students,
            env=STAGING_ENV,
            output=output,
        )

        restarted_users = CosmosUserRepository(user_helper)
        self.assertIsNotNone(restarted_users.get_by_id(LOYOLA_TENANT_ID, LOYOLA_ADMIN_USER_ID))

    def test_loyola_user_cannot_query_cres_staging_student(self):
        tenants = InMemoryTenantRepository(
            [Tenant(id=LOYOLA_TENANT_ID, code=LOYOLA_TENANT_CODE, name="LOYOLA", status=TenantStatus.TRIAL)]
        )
        users = InMemoryUserRepository([])
        students = InMemoryTenantAwareStudentRepository(
            [{"id": "cres-only", "tenant_id": "cres-staging", "matricula": "CRES-001"}]
        )
        output = io.StringIO()
        provision_loyola_demo(
            apply=True,
            tenant_repo=tenants,
            user_repo=users,
            students_repo=students,
            env=STAGING_ENV,
            output=output,
        )
        password = self._temporary_password_from_output(output.getvalue())
        service = InstitutionalAuthService(tenants, users, InMemoryAuditLogger())
        token = service.login(
            InstitutionalLoginRequest(
                institution_code=LOYOLA_TENANT_CODE,
                username=LOYOLA_ADMIN_USERNAME,
                password=password,
            )
        )
        context = service.context_from_token(token.access_token)

        self.assertIsNone(students.get_student(context.tenant_id, "cres-only"))

    def test_command_is_idempotent_and_does_not_recreate_password(self):
        tenants = InMemoryTenantRepository([])
        users = InMemoryUserRepository([])
        students = InMemoryTenantAwareStudentRepository([])
        first_output = io.StringIO()
        second_output = io.StringIO()

        provision_loyola_demo(
            apply=True,
            tenant_repo=tenants,
            user_repo=users,
            students_repo=students,
            env=STAGING_ENV,
            output=first_output,
        )
        first_hash = users.get_by_id(LOYOLA_TENANT_ID, LOYOLA_ADMIN_USER_ID).password_hash
        provision_loyola_demo(
            apply=True,
            tenant_repo=tenants,
            user_repo=users,
            students_repo=students,
            env=STAGING_ENV,
            output=second_output,
        )

        self.assertEqual(users.get_by_id(LOYOLA_TENANT_ID, LOYOLA_ADMIN_USER_ID).password_hash, first_hash)
        self.assertNotIn("TEMPORARY_PASSWORD_ONE_TIME=", second_output.getvalue())
        self.assertEqual(len(students.list_students(LOYOLA_TENANT_ID)), 2)

    def test_dry_run_does_not_write(self):
        tenants = InMemoryTenantRepository([])
        users = InMemoryUserRepository([])
        students = InMemoryTenantAwareStudentRepository([])
        output = io.StringIO()

        provision_loyola_demo(
            apply=False,
            tenant_repo=tenants,
            user_repo=users,
            students_repo=students,
            env=STAGING_ENV,
            output=output,
        )

        self.assertIsNone(tenants.get_by_id(LOYOLA_TENANT_ID))
        self.assertIsNone(users.get_by_id(LOYOLA_TENANT_ID, LOYOLA_ADMIN_USER_ID))
        self.assertEqual(students.list_students(LOYOLA_TENANT_ID), [])

    def test_apply_rejects_sasu_database(self):
        env = dict(STAGING_ENV, COSMOS_DATABASE_NAME="SASU")
        with self.assertRaises(StagingConfigurationError):
            provision_loyola_demo(
                apply=True,
                tenant_repo=InMemoryTenantRepository([]),
                user_repo=InMemoryUserRepository([]),
                students_repo=InMemoryTenantAwareStudentRepository([]),
                env=env,
                output=io.StringIO(),
            )

    def test_output_does_not_print_environment_secrets_or_hashes(self):
        output = io.StringIO()
        provision_loyola_demo(
            apply=True,
            tenant_repo=InMemoryTenantRepository([]),
            user_repo=InMemoryUserRepository([]),
            students_repo=InMemoryTenantAwareStudentRepository([]),
            env=STAGING_ENV,
            output=output,
        )
        text = output.getvalue()

        self.assertNotIn(STAGING_ENV["COSMOS_KEY"], text)
        self.assertNotIn(STAGING_ENV["JWT_SECRET_KEY"], text)
        self.assertNotIn(STAGING_ENV["REFRESH_TOKEN_SECRET"], text)
        self.assertNotIn("password_hash", text)

    def test_reset_password_dry_run_does_not_write_or_generate_password(self):
        users = InMemoryUserRepository([self._existing_loyola_user()])
        output = io.StringIO()

        with patch("multitenancy_provisioning.generate_temporary_password") as generator:
            payload = reset_loyola_password(apply=False, user_repo=users, env=STAGING_ENV, output=output)

        generator.assert_not_called()
        self.assertEqual(payload["mode"], "dry-run")
        self.assertEqual(payload["base"], "sasu_multitenant_staging")
        self.assertEqual(payload["tenant_id"], LOYOLA_TENANT_ID)
        self.assertEqual(payload["username"], LOYOLA_ADMIN_USERNAME)
        self.assertEqual(payload["action"], "reset temporary password")
        self.assertEqual(users.get_by_id(LOYOLA_TENANT_ID, LOYOLA_ADMIN_USER_ID).session_version, 3)
        self.assertNotIn("TEMPORARY_PASSWORD_ONE_TIME", output.getvalue())
        self.assertNotIn("password_hash", output.getvalue())

    def test_reset_password_apply_rejects_sasu_database(self):
        env = dict(STAGING_ENV, COSMOS_DATABASE_NAME="SASU")

        with self.assertRaises(StagingConfigurationError):
            reset_loyola_password(
                apply=True,
                user_repo=InMemoryUserRepository([self._existing_loyola_user()]),
                env=env,
                output=io.StringIO(),
            )

    def test_reset_password_apply_rejects_production_environment(self):
        env = dict(STAGING_ENV, APP_ENV="production")

        with self.assertRaises(StagingConfigurationError):
            reset_loyola_password(
                apply=True,
                user_repo=InMemoryUserRepository([self._existing_loyola_user()]),
                env=env,
                output=io.StringIO(),
            )

    def test_reset_password_missing_user_is_not_created(self):
        users = InMemoryUserRepository([])

        with self.assertRaises(RuntimeError):
            reset_loyola_password(apply=True, user_repo=users, env=STAGING_ENV, output=io.StringIO())

        self.assertIsNone(users.get_by_id(LOYOLA_TENANT_ID, LOYOLA_ADMIN_USER_ID))

    def test_reset_password_stores_hash_revokes_sessions_and_clears_lockout(self):
        old_password = "OldPassword123"
        locked_until = datetime(2026, 1, 2, tzinfo=timezone.utc)
        existing_user = self._existing_loyola_user(
            password_hash=hash_password(old_password),
            session_version=7,
            failed_login_attempts=4,
            locked_until=locked_until,
            temporary_password=False,
            password_changed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            active=False,
        )
        users = InMemoryUserRepository([existing_user])
        output = io.StringIO()

        payload = reset_loyola_password(apply=True, user_repo=users, env=STAGING_ENV, output=output)
        temporary_password = self._temporary_password_from_output(output.getvalue())
        stored_user = users.get_by_id(LOYOLA_TENANT_ID, LOYOLA_ADMIN_USER_ID)

        self.assertEqual(payload["status"], "password-reset")
        self.assertEqual(payload["temporary_password_created"], True)
        self.assertEqual(payload["sessions_revoked"], True)
        self.assertNotEqual(stored_user.password_hash, temporary_password)
        self.assertNotEqual(stored_user.password_hash, existing_user.password_hash)
        self.assertTrue(verify_password(temporary_password, stored_user.password_hash))
        self.assertFalse(verify_password(old_password, stored_user.password_hash))
        self.assertTrue(stored_user.temporary_password)
        self.assertIsNone(stored_user.password_changed_at)
        self.assertEqual(stored_user.session_version, 8)
        self.assertEqual(stored_user.failed_login_attempts, 0)
        self.assertIsNone(stored_user.locked_until)
        self.assertTrue(stored_user.active)

    def test_reset_password_does_not_modify_tenant_or_students(self):
        tenant = Tenant(id=LOYOLA_TENANT_ID, code=LOYOLA_TENANT_CODE, name="LOYOLA", status=TenantStatus.TRIAL)
        tenants = InMemoryTenantRepository([tenant])
        students = InMemoryTenantAwareStudentRepository(
            [{"id": "student-1", "tenant_id": LOYOLA_TENANT_ID, "matricula": "LOY-001"}]
        )
        users = InMemoryUserRepository([self._existing_loyola_user()])

        reset_loyola_password(apply=True, user_repo=users, env=STAGING_ENV, output=io.StringIO())

        self.assertEqual(tenants.get_by_id(LOYOLA_TENANT_ID).model_dump(), tenant.model_dump())
        self.assertEqual(students.list_students(LOYOLA_TENANT_ID), [{"id": "student-1", "tenant_id": LOYOLA_TENANT_ID, "matricula": "LOY-001"}])

    def test_reset_password_output_does_not_print_secrets_or_hashes(self):
        output = io.StringIO()
        reset_loyola_password(
            apply=True,
            user_repo=InMemoryUserRepository([self._existing_loyola_user()]),
            env=STAGING_ENV,
            output=output,
        )
        text = output.getvalue()
        safe_json = text.split("TEMPORARY_PASSWORD_ONE_TIME=", 1)[0].strip()
        payload = json.loads(safe_json)

        self.assertEqual(payload["mode"], "apply")
        self.assertEqual(payload["action"], "reset-loyola-password")
        self.assertEqual(payload["database"], "sasu_multitenant_staging")
        self.assertNotIn(STAGING_ENV["COSMOS_KEY"], text)
        self.assertNotIn(STAGING_ENV["JWT_SECRET_KEY"], text)
        self.assertNotIn(STAGING_ENV["REFRESH_TOKEN_SECRET"], text)
        self.assertNotIn("password_hash", text)
        self.assertNotIn("$2b$", text)

    @staticmethod
    def _temporary_password_from_output(text):
        for line in text.splitlines():
            if line.startswith("TEMPORARY_PASSWORD_ONE_TIME="):
                return line.split("=", 1)[1]
        raise AssertionError("Temporary password was not printed")

    @staticmethod
    def _existing_loyola_user(**overrides):
        values = {
            "id": LOYOLA_ADMIN_USER_ID,
            "tenant_id": LOYOLA_TENANT_ID,
            "username": LOYOLA_ADMIN_USERNAME,
            "password_hash": hash_password("ExistingPassword123"),
            "roles": ["tenant_admin"],
            "active": True,
            "temporary_password": True,
            "session_version": 3,
            "failed_login_attempts": 0,
            "locked_until": None,
            "password_changed_at": None,
        }
        values.update(overrides)
        return MultitenantUser(**values)


if __name__ == "__main__":
    unittest.main()
