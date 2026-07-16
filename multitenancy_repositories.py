from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from multitenancy_models import MultitenantUser, Tenant


SYNTHETIC_KEY_SEPARATOR = "|"


def _validate_synthetic_key_component(name: str, value: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    if SYNTHETIC_KEY_SEPARATOR in normalized:
        raise ValueError(f"{name} contains an invalid separator")
    return normalized


def build_tenant_student_key(tenant_id: str, student_id: str) -> str:
    tenant = _validate_synthetic_key_component("tenant_id", tenant_id)
    student = _validate_synthetic_key_component("student_id", student_id)
    return f"{tenant}{SYNTHETIC_KEY_SEPARATOR}{student}"


def build_tenant_month_key(tenant_id: str, utc_datetime: datetime) -> str:
    tenant = _validate_synthetic_key_component("tenant_id", tenant_id)
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
    return f"{tenant}{SYNTHETIC_KEY_SEPARATOR}{utc_datetime.astimezone(timezone.utc):%Y-%m}"


class TenantRepository:
    def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        raise NotImplementedError

    def get_by_code(self, code: str) -> Optional[Tenant]:
        raise NotImplementedError

    def save(self, tenant: Tenant) -> Tenant:
        raise NotImplementedError

    def create(self, tenant: Tenant) -> Tenant:
        raise NotImplementedError

    def update(self, tenant: Tenant) -> Tenant:
        raise NotImplementedError


class UserRepository:
    def get_by_id(self, tenant_id: str, user_id: str) -> Optional[MultitenantUser]:
        raise NotImplementedError

    def get_by_username(self, tenant_id: str, username: str) -> Optional[MultitenantUser]:
        raise NotImplementedError

    def save(self, user: MultitenantUser) -> MultitenantUser:
        raise NotImplementedError

    def create(self, user: MultitenantUser) -> MultitenantUser:
        raise NotImplementedError

    def update(self, user: MultitenantUser) -> MultitenantUser:
        raise NotImplementedError


class InMemoryTenantRepository(TenantRepository):
    def __init__(self, tenants: Iterable[Tenant]):
        self.by_id = {tenant.id: tenant for tenant in tenants}
        self.by_code = {tenant.code.upper(): tenant for tenant in tenants}

    def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        return self.by_id.get(tenant_id)

    def get_by_code(self, code: str) -> Optional[Tenant]:
        return self.by_code.get(code.strip().upper())

    def save(self, tenant: Tenant) -> Tenant:
        self.by_id[tenant.id] = tenant
        self.by_code[tenant.code.upper()] = tenant
        return tenant

    def create(self, tenant: Tenant) -> Tenant:
        return self.save(tenant)

    def update(self, tenant: Tenant) -> Tenant:
        return self.save(tenant)


class InMemoryUserRepository(UserRepository):
    def __init__(self, users: Iterable[MultitenantUser]):
        self.users = list(users)

    def get_by_id(self, tenant_id: str, user_id: str) -> Optional[MultitenantUser]:
        return next((user for user in self.users if user.tenant_id == tenant_id and user.id == user_id), None)

    def get_by_username(self, tenant_id: str, username: str) -> Optional[MultitenantUser]:
        normalized = username.strip().lower()
        return next(
            (
                user
                for user in self.users
                if user.tenant_id == tenant_id and user.username.strip().lower() == normalized
            ),
            None,
        )

    def save(self, user: MultitenantUser) -> MultitenantUser:
        for index, current in enumerate(self.users):
            if current.tenant_id == user.tenant_id and current.id == user.id:
                self.users[index] = user
                return user
        self.users.append(user)
        return user

    def create(self, user: MultitenantUser) -> MultitenantUser:
        return self.save(user)

    def update(self, user: MultitenantUser) -> MultitenantUser:
        return self.save(user)


def _strip_cosmos_metadata(item: dict) -> dict:
    return {key: value for key, value in item.items() if not key.startswith("_")}


class CosmosTenantRepository(TenantRepository):
    def __init__(self, helper=None):
        self._tenants = helper

    @property
    def tenants(self):
        if self._tenants is None:
            from cosmos_helper import CosmosDBHelper

            self._tenants = CosmosDBHelper("tenants_v2", "/id")
        return self._tenants

    def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        try:
            item = self.tenants.read_item(tenant_id, tenant_id)
        except Exception:
            return None
        return Tenant(**_strip_cosmos_metadata(item))

    def get_by_code(self, code: str) -> Optional[Tenant]:
        normalized = code.strip().upper()
        query = "SELECT * FROM c WHERE c.code = @code OR c.code_upper = @code"
        params = [{"name": "@code", "value": normalized}]
        results = self.tenants.query_items(query, params)
        return Tenant(**_strip_cosmos_metadata(results[0])) if results else None

    def save(self, tenant: Tenant) -> Tenant:
        return self.update(tenant)

    def create(self, tenant: Tenant) -> Tenant:
        item = self._to_item(tenant)
        return Tenant(**_strip_cosmos_metadata(self.tenants.create_item(item)))

    def update(self, tenant: Tenant) -> Tenant:
        item = self._to_item(tenant)
        return Tenant(**_strip_cosmos_metadata(self.tenants.upsert_item(item, tenant.id)))

    @staticmethod
    def _to_item(tenant: Tenant) -> dict:
        item = tenant.model_dump(mode="json")
        item["code"] = tenant.code.strip().upper()
        item["code_upper"] = tenant.code.strip().upper()
        return item


class CosmosUserRepository(UserRepository):
    def __init__(self, helper=None):
        self._users = helper

    @property
    def users(self):
        if self._users is None:
            from cosmos_helper import CosmosDBHelper

            self._users = CosmosDBHelper("users_v2", "/tenant_id")
        return self._users

    def get_by_id(self, tenant_id: str, user_id: str) -> Optional[MultitenantUser]:
        try:
            item = self.users.read_item(user_id, tenant_id)
        except Exception:
            return None
        if item.get("tenant_id") != tenant_id:
            return None
        return MultitenantUser(**_strip_cosmos_metadata(item))

    def get_by_username(self, tenant_id: str, username: str) -> Optional[MultitenantUser]:
        normalized = username.strip().lower()
        query = (
            "SELECT * FROM c WHERE c.tenant_id = @tenant_id "
            "AND (c.username = @username OR c.username_normalized = @username)"
        )
        params = [{"name": "@tenant_id", "value": tenant_id}, {"name": "@username", "value": normalized}]
        results = self.users.query_items(query, params)
        return MultitenantUser(**_strip_cosmos_metadata(results[0])) if results else None

    def save(self, user: MultitenantUser) -> MultitenantUser:
        return self.update(user)

    def create(self, user: MultitenantUser) -> MultitenantUser:
        item = self._to_item(user)
        return MultitenantUser(**_strip_cosmos_metadata(self.users.create_item(item)))

    def update(self, user: MultitenantUser) -> MultitenantUser:
        item = self._to_item(user)
        return MultitenantUser(**_strip_cosmos_metadata(self.users.upsert_item(item, user.tenant_id)))

    @staticmethod
    def _to_item(user: MultitenantUser) -> dict:
        item = user.model_dump(mode="json")
        item["username"] = user.username.strip().lower()
        item["username_normalized"] = user.username.strip().lower()
        item["must_change_password"] = bool(user.temporary_password)
        return item


class TenantAwareStudentRepository:
    def get_student(self, tenant_id: str, student_id: str) -> Optional[dict]:
        raise NotImplementedError

    def get_student_by_matricula(self, tenant_id: str, matricula: str) -> Optional[dict]:
        raise NotImplementedError

    def list_students(self, tenant_id: str) -> List[dict]:
        raise NotImplementedError

    def create_student(self, tenant_id: str, student: dict) -> dict:
        raise NotImplementedError

    def update_student(self, tenant_id: str, student_id: str, updates: dict) -> Optional[dict]:
        raise NotImplementedError

    def delete_student(self, tenant_id: str, student_id: str) -> bool:
        raise NotImplementedError


class InMemoryTenantAwareStudentRepository(TenantAwareStudentRepository):
    def __init__(self, students: Optional[Iterable[dict]] = None):
        self.students: List[dict] = [deepcopy(student) for student in (students or [])]
        self.calls: List[tuple] = []

    def _require_tenant_id(self, tenant_id: str) -> None:
        if not tenant_id:
            raise ValueError("tenant_id is required")

    def get_student(self, tenant_id: str, student_id: str) -> Optional[dict]:
        self._require_tenant_id(tenant_id)
        self.calls.append(("get_student", tenant_id, student_id))
        for student in self.students:
            if student.get("tenant_id") == tenant_id and student.get("id") == student_id:
                return deepcopy(student)
        return None

    def get_student_by_matricula(self, tenant_id: str, matricula: str) -> Optional[dict]:
        self._require_tenant_id(tenant_id)
        self.calls.append(("get_student_by_matricula", tenant_id, matricula))
        for student in self.students:
            if student.get("tenant_id") == tenant_id and student.get("matricula") == matricula:
                return deepcopy(student)
        return None

    def list_students(self, tenant_id: str) -> List[dict]:
        self._require_tenant_id(tenant_id)
        self.calls.append(("list_students", tenant_id))
        return [deepcopy(student) for student in self.students if student.get("tenant_id") == tenant_id]

    def create_student(self, tenant_id: str, student: dict) -> dict:
        self._require_tenant_id(tenant_id)
        self.calls.append(("create_student", tenant_id))
        stored = deepcopy(student)
        stored["tenant_id"] = tenant_id
        stored.setdefault("id", f"{tenant_id}:{stored.get('matricula')}")
        self.students.append(stored)
        return deepcopy(stored)

    def update_student(self, tenant_id: str, student_id: str, updates: dict) -> Optional[dict]:
        self._require_tenant_id(tenant_id)
        self.calls.append(("update_student", tenant_id, student_id))
        for index, student in enumerate(self.students):
            if student.get("tenant_id") == tenant_id and student.get("id") == student_id:
                next_student = deepcopy(student)
                next_student.update({key: value for key, value in updates.items() if key != "tenant_id"})
                next_student["tenant_id"] = tenant_id
                self.students[index] = next_student
                return deepcopy(next_student)
        return None

    def delete_student(self, tenant_id: str, student_id: str) -> bool:
        self._require_tenant_id(tenant_id)
        self.calls.append(("delete_student", tenant_id, student_id))
        for index, student in enumerate(self.students):
            if student.get("tenant_id") == tenant_id and student.get("id") == student_id:
                del self.students[index]
                return True
        return False


class CosmosTenantAwareStudentRepository(TenantAwareStudentRepository):
    def __init__(self, helper=None):
        self._students = helper

    @property
    def students(self):
        if self._students is None:
            from cosmos_helper import CosmosDBHelper

            self._students = CosmosDBHelper("students_v2", "/tenant_id")
        return self._students

    def get_student(self, tenant_id: str, student_id: str) -> Optional[dict]:
        query = "SELECT * FROM c WHERE c.tenant_id = @tenant_id AND c.id = @id"
        params = [{"name": "@tenant_id", "value": tenant_id}, {"name": "@id", "value": student_id}]
        results = self.students.query_items(query, params)
        return results[0] if results else None

    def get_student_by_matricula(self, tenant_id: str, matricula: str) -> Optional[dict]:
        query = "SELECT * FROM c WHERE c.tenant_id = @tenant_id AND c.matricula = @matricula"
        params = [{"name": "@tenant_id", "value": tenant_id}, {"name": "@matricula", "value": matricula}]
        results = self.students.query_items(query, params)
        return results[0] if results else None

    def list_students(self, tenant_id: str) -> List[dict]:
        query = "SELECT * FROM c WHERE c.tenant_id = @tenant_id"
        params = [{"name": "@tenant_id", "value": tenant_id}]
        return self.students.query_items(query, params)

    def create_student(self, tenant_id: str, student: dict) -> dict:
        item = deepcopy(student)
        item["tenant_id"] = tenant_id
        return self.students.create_item(item)

    def update_student(self, tenant_id: str, student_id: str, updates: dict) -> Optional[dict]:
        current = self.get_student(tenant_id, student_id)
        if not current:
            return None
        current.update({key: value for key, value in updates.items() if key != "tenant_id"})
        current["tenant_id"] = tenant_id
        return self.students.upsert_item(current, tenant_id)

    def delete_student(self, tenant_id: str, student_id: str) -> bool:
        current = self.get_student(tenant_id, student_id)
        if not current:
            return False
        self.students.container.delete_item(item=student_id, partition_key=tenant_id)
        return True


class TenantAwareClinicalRecordRepository:
    def get_record(self, tenant_id: str, student_id: str, record_id: str) -> Optional[dict]:
        raise NotImplementedError

    def list_records(self, tenant_id: str, student_id: str) -> List[dict]:
        raise NotImplementedError

    def create_record(self, tenant_id: str, student_id: str, record: dict) -> dict:
        raise NotImplementedError

    def update_record(self, tenant_id: str, student_id: str, record_id: str, updates: dict) -> Optional[dict]:
        raise NotImplementedError

    def delete_record(self, tenant_id: str, student_id: str, record_id: str) -> bool:
        raise NotImplementedError


class InMemoryTenantAwareClinicalRecordRepository(TenantAwareClinicalRecordRepository):
    def __init__(self, records: Optional[Iterable[dict]] = None):
        self.records: List[dict] = []
        for record in records or []:
            stored = deepcopy(record)
            stored["tenant_student_key"] = build_tenant_student_key(stored["tenant_id"], stored["student_id"])
            self.records.append(stored)

    def get_record(self, tenant_id: str, student_id: str, record_id: str) -> Optional[dict]:
        partition_key = build_tenant_student_key(tenant_id, student_id)
        for record in self.records:
            if (
                record.get("tenant_id") == tenant_id
                and record.get("student_id") == student_id
                and record.get("tenant_student_key") == partition_key
                and record.get("id") == record_id
            ):
                return deepcopy(record)
        return None

    def list_records(self, tenant_id: str, student_id: str) -> List[dict]:
        partition_key = build_tenant_student_key(tenant_id, student_id)
        return [
            deepcopy(record)
            for record in self.records
            if record.get("tenant_id") == tenant_id
            and record.get("student_id") == student_id
            and record.get("tenant_student_key") == partition_key
        ]

    def create_record(self, tenant_id: str, student_id: str, record: dict) -> dict:
        stored = deepcopy(record)
        stored["tenant_id"] = tenant_id
        stored["student_id"] = student_id
        stored["tenant_student_key"] = build_tenant_student_key(tenant_id, student_id)
        self.records.append(stored)
        return deepcopy(stored)

    def update_record(self, tenant_id: str, student_id: str, record_id: str, updates: dict) -> Optional[dict]:
        partition_key = build_tenant_student_key(tenant_id, student_id)
        for index, record in enumerate(self.records):
            if (
                record.get("tenant_id") == tenant_id
                and record.get("student_id") == student_id
                and record.get("tenant_student_key") == partition_key
                and record.get("id") == record_id
            ):
                next_record = deepcopy(record)
                blocked = {"tenant_id", "student_id", "tenant_student_key"}
                next_record.update({key: value for key, value in updates.items() if key not in blocked})
                next_record["tenant_id"] = tenant_id
                next_record["student_id"] = student_id
                next_record["tenant_student_key"] = partition_key
                self.records[index] = next_record
                return deepcopy(next_record)
        return None

    def delete_record(self, tenant_id: str, student_id: str, record_id: str) -> bool:
        partition_key = build_tenant_student_key(tenant_id, student_id)
        for index, record in enumerate(self.records):
            if (
                record.get("tenant_id") == tenant_id
                and record.get("student_id") == student_id
                and record.get("tenant_student_key") == partition_key
                and record.get("id") == record_id
            ):
                del self.records[index]
                return True
        return False


class CosmosTenantAwareClinicalRecordRepository(TenantAwareClinicalRecordRepository):
    def __init__(self, helper=None):
        from cosmos_helper import CosmosDBHelper

        self.records = helper or CosmosDBHelper("clinical_records_v2", "/tenant_student_key")

    def get_record(self, tenant_id: str, student_id: str, record_id: str) -> Optional[dict]:
        partition_key = build_tenant_student_key(tenant_id, student_id)
        try:
            record = self.records.read_item(record_id, partition_key)
        except Exception:
            return None
        if record.get("tenant_id") != tenant_id or record.get("student_id") != student_id:
            return None
        return record

    def list_records(self, tenant_id: str, student_id: str) -> List[dict]:
        partition_key = build_tenant_student_key(tenant_id, student_id)
        query = (
            "SELECT * FROM c WHERE c.tenant_id = @tenant_id "
            "AND c.student_id = @student_id AND c.tenant_student_key = @tenant_student_key"
        )
        params = [
            {"name": "@tenant_id", "value": tenant_id},
            {"name": "@student_id", "value": student_id},
            {"name": "@tenant_student_key", "value": partition_key},
        ]
        return self.records.query_items(query, params)

    def create_record(self, tenant_id: str, student_id: str, record: dict) -> dict:
        item = deepcopy(record)
        item["tenant_id"] = tenant_id
        item["student_id"] = student_id
        item["tenant_student_key"] = build_tenant_student_key(tenant_id, student_id)
        return self.records.create_item(item)

    def update_record(self, tenant_id: str, student_id: str, record_id: str, updates: dict) -> Optional[dict]:
        current = self.get_record(tenant_id, student_id, record_id)
        if not current:
            return None
        blocked = {"tenant_id", "student_id", "tenant_student_key"}
        current.update({key: value for key, value in updates.items() if key not in blocked})
        current["tenant_id"] = tenant_id
        current["student_id"] = student_id
        partition_key = build_tenant_student_key(tenant_id, student_id)
        current["tenant_student_key"] = partition_key
        return self.records.upsert_item(current, partition_key)

    def delete_record(self, tenant_id: str, student_id: str, record_id: str) -> bool:
        current = self.get_record(tenant_id, student_id, record_id)
        if not current:
            return False
        partition_key = build_tenant_student_key(tenant_id, student_id)
        self.records.container.delete_item(item=record_id, partition_key=partition_key)
        return True
