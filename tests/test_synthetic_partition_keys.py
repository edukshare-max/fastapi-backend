import unittest
from datetime import datetime, timezone

from create_multitenant_containers import build_plan, ensure_container
from multitenancy_audit import CosmosAuditLogger
from multitenancy_repositories import (
    InMemoryTenantAwareClinicalRecordRepository,
    build_tenant_month_key,
    build_tenant_student_key,
)
from multitenancy_staging_config import StagingConfigurationError, load_staging_settings


class FakeContainer:
    def __init__(self, paths):
        self.paths = paths

    def read(self):
        return {"partitionKey": {"paths": self.paths}}


class FakeDatabase:
    def __init__(self, existing=None):
        self.existing = existing or {}
        self.created = []

    def get_container_client(self, name):
        if name not in self.existing:
            raise FakeNotFound()
        return FakeContainer(self.existing[name])

    def create_container_if_not_exists(self, *, id, partition_key):
        self.created.append((id, partition_key["paths"]))
        self.existing[id] = partition_key["paths"]


class FakeNotFound(Exception):
    pass


class FakeAuditHelper:
    def __init__(self):
        self.items = []

    def create_item(self, item):
        self.items.append(item)
        return item


class SyntheticPartitionKeyTest(unittest.TestCase):
    def test_loyola_and_cres_can_share_student_id_without_collision(self):
        records = InMemoryTenantAwareClinicalRecordRepository()
        loyola = records.create_record("loyola", "student-001", {"id": "record-1", "tenant_student_key": "cres|x"})
        cres = records.create_record("cres", "student-001", {"id": "record-1", "tenant_student_key": "loyola|x"})

        self.assertEqual(loyola["tenant_student_key"], "loyola|student-001")
        self.assertEqual(cres["tenant_student_key"], "cres|student-001")
        self.assertNotEqual(loyola["tenant_student_key"], cres["tenant_student_key"])

    def test_backend_ignores_flutter_synthetic_key_on_create_and_update(self):
        records = InMemoryTenantAwareClinicalRecordRepository()
        created = records.create_record(
            "loyola",
            "student-001",
            {"id": "record-1", "tenant_id": "cres", "tenant_student_key": "cres|student-999"},
        )
        updated = records.update_record(
            "loyola",
            "student-001",
            "record-1",
            {"tenant_id": "cres", "student_id": "student-999", "tenant_student_key": "cres|student-999"},
        )

        self.assertEqual(created["tenant_id"], "loyola")
        self.assertEqual(created["student_id"], "student-001")
        self.assertEqual(created["tenant_student_key"], "loyola|student-001")
        self.assertEqual(updated["tenant_id"], "loyola")
        self.assertEqual(updated["student_id"], "student-001")
        self.assertEqual(updated["tenant_student_key"], "loyola|student-001")

    def test_cross_tenant_read_update_delete_do_not_reveal_resource(self):
        records = InMemoryTenantAwareClinicalRecordRepository(
            [{"id": "record-1", "tenant_id": "cres", "student_id": "student-001", "summary": "private"}]
        )

        self.assertIsNone(records.get_record("loyola", "student-001", "record-1"))
        self.assertIsNone(records.update_record("loyola", "student-001", "record-1", {"summary": "tamper"}))
        self.assertFalse(records.delete_record("loyola", "student-001", "record-1"))
        self.assertEqual(records.get_record("cres", "student-001", "record-1")["summary"], "private")

    def test_invalid_synthetic_components_are_rejected(self):
        with self.assertRaises(ValueError):
            build_tenant_student_key("loyola|cres", "student-001")
        with self.assertRaises(ValueError):
            build_tenant_student_key("loyola", "student|001")

    def test_audit_logs_use_distinct_tenant_month_partitions_and_keep_tenant_id(self):
        helper = FakeAuditHelper()
        logger = CosmosAuditLogger(helper)
        logger.record(tenant_id="loyola", actor_user_id="u1", session_id="s1", action="login", result="success")
        logger.record(tenant_id="cres", actor_user_id="u2", session_id="s2", action="login", result="success")

        partitions = {item["tenant_month_key"] for item in helper.items}
        self.assertEqual({item["tenant_id"] for item in helper.items}, {"loyola", "cres"})
        self.assertEqual(len(partitions), 2)
        self.assertTrue(any(partition.startswith("loyola|") for partition in partitions))
        self.assertTrue(any(partition.startswith("cres|") for partition in partitions))

    def test_tenant_month_key_uses_utc_year_month(self):
        key = build_tenant_month_key("loyola", datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(key, "loyola|2026-07")

    def test_container_plan_uses_serverless_synthetic_keys(self):
        plan = {entry["container"]: entry["partition_key"] for entry in build_plan()}
        self.assertEqual(plan["clinical_records_v2"], "/tenant_student_key")
        self.assertEqual(plan["appointments_v2"], "/tenant_id")
        self.assertEqual(plan["referrals_v2"], "/tenant_id")
        self.assertEqual(plan["audit_logs_v2"], "/tenant_month_key")
        self.assertEqual(plan["licenses_v2"], "/tenant_id")

    def test_container_creation_is_idempotent_for_existing_keys(self):
        database = FakeDatabase({"clinical_records_v2": ["/tenant_student_key"]})
        result = ensure_container(
            database,
            type("Definition", (), {"name": "clinical_records_v2", "partition_key": "/tenant_student_key"})(),
        )

        self.assertEqual(result["status"], "exists")
        self.assertEqual(database.created, [])

    def test_container_creation_stops_on_incompatible_partition_key(self):
        database = FakeDatabase({"clinical_records_v2": ["/tenant_id"]})
        with self.assertRaises(RuntimeError):
            ensure_container(
                database,
                type("Definition", (), {"name": "clinical_records_v2", "partition_key": "/tenant_student_key"})(),
            )

    def test_production_database_is_never_authorized(self):
        env = {
            "APP_ENV": "staging",
            "ENABLE_MULTITENANT_ROUTES": "true",
            "COSMOS_ENDPOINT": "https://placeholder.documents.azure.com:443/",
            "COSMOS_KEY": "placeholder",
            "COSMOS_DATABASE_NAME": "SASU",
            "JWT_SECRET_KEY": "placeholder",
            "REFRESH_TOKEN_SECRET": "placeholder",
            "ALLOWED_ORIGINS": "https://staging.example.invalid",
            "ALLOW_PRODUCTION_DATABASE": "false",
        }
        with self.assertRaises(StagingConfigurationError):
            load_staging_settings(env)


if __name__ == "__main__":
    unittest.main()
