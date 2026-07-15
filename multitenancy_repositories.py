from __future__ import annotations

from copy import deepcopy
from typing import Dict, Iterable, List, Optional

from multitenancy_models import MultitenantUser, Tenant


class TenantRepository:
    def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        raise NotImplementedError

    def get_by_code(self, code: str) -> Optional[Tenant]:
        raise NotImplementedError


class UserRepository:
    def get_by_id(self, tenant_id: str, user_id: str) -> Optional[MultitenantUser]:
        raise NotImplementedError

    def get_by_username(self, tenant_id: str, username: str) -> Optional[MultitenantUser]:
        raise NotImplementedError


class InMemoryTenantRepository(TenantRepository):
    def __init__(self, tenants: Iterable[Tenant]):
        self.by_id = {tenant.id: tenant for tenant in tenants}
        self.by_code = {tenant.code.upper(): tenant for tenant in tenants}

    def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        return self.by_id.get(tenant_id)

    def get_by_code(self, code: str) -> Optional[Tenant]:
        return self.by_code.get(code.strip().upper())


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
        from cosmos_helper import CosmosDBHelper

        self.students = helper or CosmosDBHelper("students_v2", "/tenant_id")

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
