import unittest

from fastapi import HTTPException
from jose import jwt

from auth_service import ALGORITHM, AuthService, SECRET_KEY
from multitenancy_auth import InstitutionalAuthService, GENERIC_LOGIN_ERROR
from multitenancy_files import build_tenant_file_path, assert_file_belongs_to_tenant
from multitenancy_models import (
    ChangeTemporaryPasswordRequest,
    InstitutionResolveRequest,
    InstitutionalLoginRequest,
    RefreshTokenRequest,
    TenantStatus,
)
from multitenancy_seed import build_staging_students, build_staging_tenants, build_staging_users


class StagingClient:
    def __init__(self, service, students):
        self.service = service
        self.students = students

    def resolve(self, code):
        tenant = self.service.tenants.get_by_code(code)
        if not tenant or not tenant.is_login_enabled():
            return 404, {"detail": "Institucion no disponible"}
        return 200, {
            "institution_id": tenant.id,
            "display_name": tenant.name,
            "status": tenant.status.value,
            "branding": tenant.branding,
            "enabled_modules": tenant.enabled_modules,
            "demo": tenant.plan == "demo" or bool(tenant.branding.get("demo")),
        }

    def login(self, code, username, password):
        try:
            token = self.service.login(
                InstitutionalLoginRequest(institution_code=code, username=username, password=password)
            )
            return 200, token.model_dump()
        except HTTPException as exc:
            return exc.status_code, {"detail": exc.detail}

    def context(self, token):
        return self.service.context_from_token(token)

    def refresh(self, refresh_token):
        try:
            token = self.service.refresh(RefreshTokenRequest(refresh_token=refresh_token))
            return 200, token.model_dump()
        except HTTPException as exc:
            return exc.status_code, {"detail": exc.detail}

    def logout(self, token):
        try:
            self.service.logout(self.context(token))
            return 204, None
        except HTTPException as exc:
            return exc.status_code, {"detail": exc.detail}

    def change_temporary_password(self, token, current, new):
        try:
            self.service.change_temporary_password(
                self.context(token),
                ChangeTemporaryPasswordRequest(current_password=current, new_password=new),
            )
            return 204, None
        except HTTPException as exc:
            return exc.status_code, {"detail": exc.detail}

    def get_student(self, token, student_id, tenant_query=None):
        try:
            context = self.context(token)
            if "students.read" not in context.permissions:
                return 403, {"detail": "Permiso insuficiente"}
            if tenant_query and tenant_query != context.tenant_id:
                tenant_query = context.tenant_id
            student = self.students.get_student(context.tenant_id, student_id)
            return (200, student) if student else (404, {"detail": "Recurso no encontrado"})
        except HTTPException as exc:
            return exc.status_code, {"detail": exc.detail}

    def patch_student(self, token, student_id, payload):
        try:
            context = self.context(token)
            if "students.write" not in context.permissions:
                return 403, {"detail": "Permiso insuficiente"}
            student = self.students.update_student(context.tenant_id, student_id, payload)
            return (200, student) if student else (404, {"detail": "Recurso no encontrado"})
        except HTTPException as exc:
            return exc.status_code, {"detail": exc.detail}

    def delete_student(self, token, student_id):
        try:
            context = self.context(token)
            if "students.write" not in context.permissions:
                return 403, {"detail": "Permiso insuficiente"}
            deleted = self.students.delete_student(context.tenant_id, student_id)
            return (204, None) if deleted else (404, {"detail": "Recurso no encontrado"})
        except HTTPException as exc:
            return exc.status_code, {"detail": exc.detail}

    def appointments(self, token):
        try:
            context = self.context(token)
            tenant = self.service.tenants.get_by_id(context.tenant_id)
            if "appointments" not in tenant.enabled_modules:
                return 403, {"detail": "Modulo no contratado"}
            if "appointments.read" not in context.permissions:
                return 403, {"detail": "Permiso insuficiente"}
            return 200, [{"tenant_id": context.tenant_id}]
        except HTTPException as exc:
            return exc.status_code, {"detail": exc.detail}


class MultitenantStagingIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tenants = build_staging_tenants()
        self.users = build_staging_users(AuthService.hash_password("TemporalDemo123!"))
        self.students = build_staging_students()
        self.audit = __import__("multitenancy_audit").InMemoryAuditLogger()
        self.service = InstitutionalAuthService(self.tenants, self.users, self.audit)
        self.client = StagingClient(self.service, self.students)

    def login_loyola(self):
        status, body = self.client.login("LOYOLA-DEMO-2026", "admin.loyola", "TemporalDemo123!")
        self.assertEqual(status, 200, body)
        return body

    def login_cres(self):
        status, body = self.client.login("CRES-STAGING-2026", "admin.cres", "TemporalDemo123!")
        self.assertEqual(status, 200, body)
        return body

    def test_loyola_resolves_institution_code(self):
        status, body = self.client.resolve("LOYOLA-DEMO-2026")
        self.assertEqual(status, 200)
        self.assertEqual(body["institution_id"], "loyola-demo")
        self.assertTrue(body["demo"])

    def test_invalid_code_does_not_reveal_partial_existence(self):
        status, body = self.client.resolve("LOYOLA")
        self.assertEqual(status, 404)
        self.assertEqual(body["detail"], "Institucion no disponible")

    def test_loyola_login_uses_own_user(self):
        body = self.login_loyola()
        payload = jwt.decode(body["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
        self.assertEqual(payload["tenant_id"], "loyola-demo")

    def test_cres_staging_login_uses_own_user(self):
        body = self.login_cres()
        payload = jwt.decode(body["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
        self.assertEqual(payload["tenant_id"], "cres-staging")

    def test_loyola_cannot_read_cres_student(self):
        token = self.login_loyola()["access_token"]
        status, _ = self.client.get_student(token, "cres-staging-student-001")
        self.assertEqual(status, 404)

    def test_loyola_cannot_modify_cres_student(self):
        token = self.login_loyola()["access_token"]
        status, _ = self.client.patch_student(token, "cres-staging-student-001", {"nombre": "No"})
        self.assertEqual(status, 404)

    def test_loyola_cannot_delete_cres_student(self):
        token = self.login_loyola()["access_token"]
        status, _ = self.client.delete_student(token, "cres-staging-student-001")
        self.assertEqual(status, 404)

    def test_loyola_cannot_access_cres_attachment(self):
        loyola_path = build_tenant_file_path("loyola-demo", "students", "loyola-demo-student-001", "demo.pdf")
        cres_path = build_tenant_file_path("cres-staging", "students", "cres-staging-student-001", "demo.pdf")
        self.assertTrue(assert_file_belongs_to_tenant(loyola_path, "loyola-demo"))
        self.assertFalse(assert_file_belongs_to_tenant(cres_path, "loyola-demo"))

    def test_body_tenant_change_is_ignored(self):
        token = self.login_loyola()["access_token"]
        status, body = self.client.patch_student(
            token,
            "loyola-demo-student-001",
            {"tenant_id": "cres-staging", "nombre": "Paciente Ficticio Editado"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["tenant_id"], "loyola-demo")

    def test_query_tenant_change_is_ignored(self):
        token = self.login_loyola()["access_token"]
        status, body = self.client.get_student(token, "loyola-demo-student-001", tenant_query="cres-staging")
        self.assertEqual(status, 200)
        self.assertEqual(body["tenant_id"], "loyola-demo")

    def test_tampered_token_is_rejected(self):
        token = self.login_loyola()["access_token"]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        payload["tenant_id"] = "cres-staging"
        tampered = jwt.encode(payload, "wrong-secret", algorithm=ALGORITHM)
        status, _ = self.client.get_student(tampered, "loyola-demo-student-001")
        self.assertEqual(status, 401)

    def test_reused_refresh_token_is_rejected(self):
        refresh = self.login_loyola()["refresh_token"]
        status, rotated = self.client.refresh(refresh)
        self.assertEqual(status, 200)
        self.assertNotEqual(rotated["refresh_token"], refresh)
        status, _ = self.client.refresh(refresh)
        self.assertEqual(status, 401)

    def test_suspended_tenant_loses_access(self):
        token = self.login_loyola()["access_token"]
        tenant = self.tenants.get_by_id("loyola-demo")
        tenant.status = TenantStatus.SUSPENDED
        self.tenants.save(tenant)
        status, _ = self.client.get_student(token, "loyola-demo-student-001")
        self.assertEqual(status, 403)

    def test_locked_account_loses_access(self):
        for _ in range(5):
            self.client.login("LOYOLA-DEMO-2026", "admin.loyola", "wrong")
        status, body = self.client.login("LOYOLA-DEMO-2026", "admin.loyola", "TemporalDemo123!")
        self.assertEqual(status, 401)
        self.assertEqual(body["detail"], GENERIC_LOGIN_ERROR)

    def test_temporary_password_requires_change(self):
        body = self.login_loyola()
        self.assertTrue(body["requires_password_change"])
        status, _ = self.client.change_temporary_password(
            body["access_token"],
            "TemporalDemo123!",
            "NuevaTemporalDemo123!",
        )
        self.assertEqual(status, 204)

    def test_logout_revokes_session(self):
        token = self.login_loyola()["access_token"]
        status, _ = self.client.logout(token)
        self.assertEqual(status, 204)
        status, _ = self.client.get_student(token, "loyola-demo-student-001")
        self.assertEqual(status, 401)

    def test_two_schools_can_use_same_matricula(self):
        loyola = self.students.get_student_by_matricula("loyola-demo", "STG-001")
        cres = self.students.get_student_by_matricula("cres-staging", "STG-001")
        self.assertNotEqual(loyola["id"], cres["id"])

    def test_uncontracted_module_returns_403(self):
        token = self.login_loyola()["access_token"]
        tenant = self.tenants.get_by_id("loyola-demo")
        tenant.enabled_modules = ["students"]
        self.tenants.save(tenant)
        status, _ = self.client.appointments(token)
        self.assertEqual(status, 403)

    def test_logs_do_not_contain_passwords_or_full_tokens(self):
        self.client.login("LOYOLA-DEMO-2026", "admin.loyola", "bad-password")
        token = self.login_loyola()["access_token"]
        serialized = "\n".join(event.model_dump_json() for event in self.audit.events)
        self.assertNotIn("bad-password", serialized)
        self.assertNotIn(token, serialized)

    def test_no_cres_api_fallback_configuration_is_present(self):
        status, body = self.client.resolve("LOYOLA-DEMO-2026")
        self.assertEqual(status, 200)
        self.assertNotIn("database", body)
        self.assertNotIn("container", body)


if __name__ == "__main__":
    unittest.main()
