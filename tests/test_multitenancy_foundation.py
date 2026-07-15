import unittest
from datetime import timedelta

from fastapi import HTTPException
from jose import jwt

from auth_service import ALGORITHM, AuthService, SECRET_KEY
from multitenancy_audit import InMemoryAuditLogger
from multitenancy_auth import InstitutionalAuthService, GENERIC_LOGIN_ERROR
from multitenancy_files import assert_file_belongs_to_tenant, build_tenant_file_path
from multitenancy_models import (
    InstitutionalLoginRequest,
    MultitenantUser,
    Tenant,
    TenantStatus,
    permissions_for_roles,
)
from multitenancy_repositories import (
    InMemoryTenantAwareStudentRepository,
    InMemoryTenantRepository,
    InMemoryUserRepository,
)


class MiniResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


class MiniClient:
    def __init__(self, auth_service, students):
        self.auth_service = auth_service
        self.students = students

    def post(self, path, json=None, headers=None):
        try:
            if path == "/auth/login":
                token = self.auth_service.login(InstitutionalLoginRequest(**json))
                return MiniResponse(200, token.model_dump())
            if path == "/students":
                context = self._context(headers)
                self._require(context, "students.write")
                return MiniResponse(201, self.students.create_student(context.tenant_id, json))
        except HTTPException as exc:
            return MiniResponse(exc.status_code, {"detail": exc.detail})
        raise AssertionError(f"Unhandled POST {path}")

    def get(self, path, headers=None):
        try:
            context = self._context(headers)
            self._require(context, "students.read")
            if path == "/students":
                return MiniResponse(200, self.students.list_students(context.tenant_id))
            if path.startswith("/students/"):
                student_id = path.rsplit("/", 1)[-1]
                student = self.students.get_student(context.tenant_id, student_id)
                return MiniResponse(200, student) if student else MiniResponse(404, {"detail": "Recurso no encontrado"})
            if path.startswith("/tenants/"):
                parts = path.strip("/").split("/")
                url_tenant_id, student_id = parts[1], parts[3]
                if url_tenant_id != context.tenant_id:
                    return MiniResponse(404, {"detail": "Recurso no encontrado"})
                student = self.students.get_student(context.tenant_id, student_id)
                return MiniResponse(200, student) if student else MiniResponse(404, {"detail": "Recurso no encontrado"})
        except HTTPException as exc:
            return MiniResponse(exc.status_code, {"detail": exc.detail})
        raise AssertionError(f"Unhandled GET {path}")

    def patch(self, path, headers=None, json=None):
        try:
            context = self._context(headers)
            self._require(context, "students.write")
            student_id = path.rsplit("/", 1)[-1]
            student = self.students.update_student(context.tenant_id, student_id, json)
            return MiniResponse(200, student) if student else MiniResponse(404, {"detail": "Recurso no encontrado"})
        except HTTPException as exc:
            return MiniResponse(exc.status_code, {"detail": exc.detail})

    def delete(self, path, headers=None):
        try:
            context = self._context(headers)
            self._require(context, "students.write")
            student_id = path.rsplit("/", 1)[-1]
            deleted = self.students.delete_student(context.tenant_id, student_id)
            return MiniResponse(204, None) if deleted else MiniResponse(404, {"detail": "Recurso no encontrado"})
        except HTTPException as exc:
            return MiniResponse(exc.status_code, {"detail": exc.detail})

    def _context(self, headers):
        token = (headers or {}).get("Authorization", "").replace("Bearer ", "", 1)
        return self.auth_service.context_from_token(token)

    @staticmethod
    def _require(context, permission):
        if permission not in context.permissions:
            raise HTTPException(status_code=403, detail="Permiso insuficiente")


class MultitenancyFoundationTest(unittest.TestCase):
    def setUp(self):
        self.audit = InMemoryAuditLogger()
        self.tenants = InMemoryTenantRepository(
            [
                Tenant(id="cres", code="CRES-INTERNAL", name="CRES", status=TenantStatus.ACTIVE),
                Tenant(
                    id="loyola",
                    code="LOYOLA-DEMO-2026",
                    name="LOYOLA",
                    status=TenantStatus.TRIAL,
                    plan="demo",
                ),
                Tenant(id="blocked", code="BLOCKED-2026", name="Blocked", status=TenantStatus.SUSPENDED),
            ]
        )
        password_hash = AuthService.hash_password("Correcta123")
        self.users = InMemoryUserRepository(
            [
                MultitenantUser(
                    id="user-loyola-admin",
                    tenant_id="loyola",
                    username="direccion.salud",
                    password_hash=password_hash,
                    roles=["tenant_admin"],
                    permissions=[],
                ),
                MultitenantUser(
                    id="user-cres-admin",
                    tenant_id="cres",
                    username="direccion.salud",
                    password_hash=password_hash,
                    roles=["tenant_admin"],
                    permissions=[],
                ),
                MultitenantUser(
                    id="user-blocked-admin",
                    tenant_id="blocked",
                    username="direccion.salud",
                    password_hash=password_hash,
                    roles=["tenant_admin"],
                    permissions=[],
                ),
                MultitenantUser(
                    id="user-disabled",
                    tenant_id="loyola",
                    username="desactivado",
                    password_hash=password_hash,
                    active=False,
                    roles=["tenant_admin"],
                    permissions=[],
                ),
                MultitenantUser(
                    id="user-auditor",
                    tenant_id="loyola",
                    username="auditor",
                    password_hash=password_hash,
                    roles=["auditor"],
                    permissions=[],
                ),
            ]
        )
        self.students = InMemoryTenantAwareStudentRepository(
            [
                {"id": "student-loyola-1", "tenant_id": "loyola", "matricula": "A001", "nombre": "Demo Loyola"},
                {"id": "student-cres-1", "tenant_id": "cres", "matricula": "A001", "nombre": "Demo CRES"},
            ]
        )
        self.auth_service = InstitutionalAuthService(self.tenants, self.users, self.audit)
        self.client = MiniClient(self.auth_service, self.students)

    def login(self, username="direccion.salud", code="LOYOLA-DEMO-2026", password="Correcta123"):
        response = self.client.post(
            "/auth/login",
            json={"institution_code": code, "username": username, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["access_token"]

    def headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_loyola_user_can_read_loyola_student(self):
        token = self.login()
        response = self.client.get("/students/student-loyola-1", headers=self.headers(token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tenant_id"], "loyola")

    def test_loyola_user_cannot_read_modify_delete_or_discover_cres_student(self):
        token = self.login()
        headers = self.headers(token)
        read_response = self.client.get("/students/student-cres-1", headers=headers)
        update_response = self.client.patch("/students/student-cres-1", headers=headers, json={"nombre": "x"})
        delete_response = self.client.delete("/students/student-cres-1", headers=headers)
        url_tamper_response = self.client.get("/tenants/cres/students/student-cres-1", headers=headers)
        for response in [read_response, update_response, delete_response, url_tamper_response]:
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["detail"], "Recurso no encontrado")

    def test_body_tenant_id_does_not_override_authenticated_tenant(self):
        token = self.login()
        response = self.client.post(
            "/students",
            headers=self.headers(token),
            json={"id": "new-student", "tenant_id": "cres", "matricula": "A002"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["tenant_id"], "loyola")

    def test_url_tenant_id_does_not_enable_cross_tenant_access(self):
        token = self.login()
        response = self.client.get("/tenants/cres/students/student-loyola-1", headers=self.headers(token))
        self.assertEqual(response.status_code, 404)

    def test_suspended_tenant_jwt_is_rejected(self):
        user = self.users.get_by_id("blocked", "user-blocked-admin")
        token = self.auth_service.create_token(
            user=user,
            roles=user.roles,
            permissions=permissions_for_roles(user.roles),
            expires_delta=timedelta(minutes=5),
        )
        response = self.client.get("/students/student-loyola-1", headers=self.headers(token))
        self.assertEqual(response.status_code, 403)

    def test_disabled_user_is_rejected(self):
        user = self.users.get_by_id("loyola", "user-disabled")
        token = self.auth_service.create_token(
            user=user,
            roles=user.roles,
            permissions=permissions_for_roles(user.roles),
            expires_delta=timedelta(minutes=5),
        )
        response = self.client.get("/students/student-loyola-1", headers=self.headers(token))
        self.assertEqual(response.status_code, 401)

    def test_insufficient_permission_returns_403(self):
        token = self.login(username="auditor")
        response = self.client.post(
            "/students",
            headers=self.headers(token),
            json={"id": "blocked-write", "matricula": "A003"},
        )
        self.assertEqual(response.status_code, 403)

    def test_repository_operations_receive_tenant_id(self):
        token = self.login()
        self.client.get("/students/student-loyola-1", headers=self.headers(token))
        self.client.get("/students", headers=self.headers(token))
        self.assertIn(("get_student", "loyola", "student-loyola-1"), self.students.calls)
        self.assertIn(("list_students", "loyola"), self.students.calls)

    def test_login_emits_correct_tenant(self):
        response = self.client.post(
            "/auth/login",
            json={
                "institution_code": "LOYOLA-DEMO-2026",
                "username": "direccion.salud",
                "password": "Correcta123",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = jwt.decode(response.json()["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
        self.assertEqual(payload["tenant_id"], "loyola")
        self.assertEqual(payload["sub"], "user-loyola-admin")
        self.assertIn("session_id", payload)
        self.assertNotIn("password", payload)
        self.assertNotIn("clinical_notes", payload)

    def test_audit_logs_do_not_store_passwords_or_clinical_notes(self):
        self.client.post(
            "/auth/login",
            json={
                "institution_code": "LOYOLA-DEMO-2026",
                "username": "direccion.salud",
                "password": "Incorrecta123",
            },
        )
        self.audit.record(
            tenant_id="loyola",
            actor_user_id="user-loyola-admin",
            session_id="session",
            action="clinical_record.read",
            result="success",
            details={"password": "secret", "clinical_notes": "private", "resource_id": "student-loyola-1"},
        )
        serialized = "\n".join(event.model_dump_json() for event in self.audit.events)
        self.assertNotIn("Incorrecta123", serialized)
        self.assertNotIn("private", serialized)
        self.assertIn("[redacted]", serialized)

    def test_institution_codes_and_users_are_not_enumerable(self):
        missing_institution = self.client.post(
            "/auth/login",
            json={"institution_code": "NO-EXISTE", "username": "direccion.salud", "password": "Correcta123"},
        )
        missing_user = self.client.post(
            "/auth/login",
            json={"institution_code": "LOYOLA-DEMO-2026", "username": "noexiste", "password": "Correcta123"},
        )
        wrong_password = self.client.post(
            "/auth/login",
            json={"institution_code": "LOYOLA-DEMO-2026", "username": "direccion.salud", "password": "bad"},
        )
        self.assertEqual(missing_institution.status_code, 401)
        self.assertEqual(missing_user.status_code, 401)
        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(missing_institution.json()["detail"], GENERIC_LOGIN_ERROR)
        self.assertEqual(missing_user.json()["detail"], GENERIC_LOGIN_ERROR)
        self.assertEqual(wrong_password.json()["detail"], GENERIC_LOGIN_ERROR)

    def test_no_global_student_query_for_institutional_role(self):
        token = self.login()
        response = self.client.get("/students", headers=self.headers(token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual({student["tenant_id"] for student in response.json()}, {"loyola"})

    def test_files_are_limited_to_tenant_prefix(self):
        path = build_tenant_file_path("loyola", "students", "student-loyola-1", "../evidence.pdf")
        self.assertEqual(path, "tenants/loyola/students/student-loyola-1/evidence.pdf")
        self.assertTrue(assert_file_belongs_to_tenant(path, "loyola"))
        self.assertFalse(assert_file_belongs_to_tenant(path, "cres"))

    def test_same_matricula_can_exist_in_cres_and_loyola_without_collision(self):
        loyola = self.students.get_student_by_matricula("loyola", "A001")
        cres = self.students.get_student_by_matricula("cres", "A001")
        self.assertEqual(loyola["id"], "student-loyola-1")
        self.assertEqual(cres["id"], "student-cres-1")

    def test_token_tenant_tampering_is_rejected(self):
        token = self.login()
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        payload["tenant_id"] = "cres"
        tampered = jwt.encode(payload, "wrong-secret", algorithm=ALGORITHM)
        response = self.client.get("/students/student-loyola-1", headers=self.headers(tampered))
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
