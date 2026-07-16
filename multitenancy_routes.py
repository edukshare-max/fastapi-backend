from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from multitenancy_auth import (
    InstitutionalAuthService,
    get_current_tenant_context,
    get_multitenant_auth_service,
    require_tenant_permission,
)
from multitenancy_models import (
    ChangeTemporaryPasswordRequest,
    InstitutionResolveRequest,
    InstitutionResolveResponse,
    InstitutionalLoginRequest,
    RefreshTokenRequest,
    TenantContext,
    TokenResponse,
)
from multitenancy_repositories import TenantAwareStudentRepository


def _require_module(service: InstitutionalAuthService, context: TenantContext, module: str) -> None:
    tenant = service.tenants.get_by_id(context.tenant_id)
    if not tenant or module not in tenant.enabled_modules:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Modulo no contratado")


def create_multitenancy_router(students_repository: TenantAwareStudentRepository) -> APIRouter:
    router = APIRouter()

    @router.post("/public/institution/resolve", response_model=InstitutionResolveResponse)
    async def resolve_institution(
        payload: InstitutionResolveRequest,
        service: InstitutionalAuthService = Depends(get_multitenant_auth_service),
    ):
        tenant = service.tenants.get_by_code(payload.institution_code)
        if not tenant or not tenant.is_login_enabled():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institucion no disponible")
        return InstitutionResolveResponse(
            institution_id=tenant.id,
            display_name=tenant.name,
            status=tenant.status.value,
            branding=tenant.branding,
            enabled_modules=tenant.enabled_modules,
            demo=tenant.plan == "demo" or bool(tenant.branding.get("demo")),
        )

    @router.post("/auth/login", response_model=TokenResponse)
    async def institutional_login(
        payload: InstitutionalLoginRequest,
        request: Request,
        service: InstitutionalAuthService = Depends(get_multitenant_auth_service),
    ):
        return service.login(
            payload,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            correlation_id=request.headers.get("x-correlation-id"),
        )

    @router.post("/auth/refresh", response_model=TokenResponse)
    async def refresh_token(
        payload: RefreshTokenRequest,
        service: InstitutionalAuthService = Depends(get_multitenant_auth_service),
    ):
        return service.refresh(payload)

    @router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
    async def logout(
        context: TenantContext = Depends(get_current_tenant_context),
        service: InstitutionalAuthService = Depends(get_multitenant_auth_service),
    ):
        service.logout(context)
        return None

    @router.post("/auth/change-temporary-password", status_code=status.HTTP_204_NO_CONTENT)
    async def change_temporary_password(
        payload: ChangeTemporaryPasswordRequest,
        context: TenantContext = Depends(get_current_tenant_context),
        service: InstitutionalAuthService = Depends(get_multitenant_auth_service),
    ):
        service.change_temporary_password(context, payload)
        return None

    @router.get("/me")
    async def me(context: TenantContext = Depends(get_current_tenant_context)):
        return context.dict()

    @router.get("/students")
    async def list_students(
        context: TenantContext = Depends(require_tenant_permission("students.read")),
        service: InstitutionalAuthService = Depends(get_multitenant_auth_service),
    ):
        _require_module(service, context, "students")
        return students_repository.list_students(context.tenant_id)

    @router.get("/students/{student_id}")
    async def get_student(
        student_id: str,
        context: TenantContext = Depends(require_tenant_permission("students.read")),
        service: InstitutionalAuthService = Depends(get_multitenant_auth_service),
    ):
        _require_module(service, context, "students")
        student = students_repository.get_student(context.tenant_id, student_id)
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado")
        return student

    @router.post("/students", status_code=status.HTTP_201_CREATED)
    async def create_student(
        payload: dict,
        context: TenantContext = Depends(require_tenant_permission("students.write")),
        service: InstitutionalAuthService = Depends(get_multitenant_auth_service),
    ):
        _require_module(service, context, "students")
        return students_repository.create_student(context.tenant_id, payload)

    @router.patch("/students/{student_id}")
    async def update_student(
        student_id: str,
        payload: dict,
        context: TenantContext = Depends(require_tenant_permission("students.write")),
        service: InstitutionalAuthService = Depends(get_multitenant_auth_service),
    ):
        _require_module(service, context, "students")
        student = students_repository.update_student(context.tenant_id, student_id, payload)
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado")
        return student

    @router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_student(
        student_id: str,
        context: TenantContext = Depends(require_tenant_permission("students.write")),
        service: InstitutionalAuthService = Depends(get_multitenant_auth_service),
    ):
        _require_module(service, context, "students")
        if not students_repository.delete_student(context.tenant_id, student_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado")
        return None

    @router.get("/appointments")
    async def list_appointments(
        context: TenantContext = Depends(require_tenant_permission("appointments.read")),
        service: InstitutionalAuthService = Depends(get_multitenant_auth_service),
    ):
        _require_module(service, context, "appointments")
        return [
            {
                "id": f"{context.tenant_id}-appointment-demo",
                "tenant_id": context.tenant_id,
                "status": "scheduled",
                "student_id": "demo",
            }
        ]

    @router.get("/audit")
    async def list_audit(
        context: TenantContext = Depends(require_tenant_permission("audit.read")),
        service: InstitutionalAuthService = Depends(get_multitenant_auth_service),
    ):
        _require_module(service, context, "audit")
        return [
            event.dict()
            for event in service.audit_logger.events
            if event.tenant_id == context.tenant_id
        ]

    @router.get("/tenants/{tenant_id}/students/{student_id}")
    async def get_student_with_tenant_in_url(
        tenant_id: str,
        student_id: str,
        context: TenantContext = Depends(require_tenant_permission("students.read")),
        service: InstitutionalAuthService = Depends(get_multitenant_auth_service),
    ):
        _require_module(service, context, "students")
        if tenant_id != context.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado")
        student = students_repository.get_student(context.tenant_id, student_id)
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado")
        return student

    return router


def create_multitenancy_health_router(required_containers: list[str]) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health():
        return {"status": "ok"}

    @router.get("/ready")
    async def ready(request: Request):
        settings = getattr(request.app.state, "multitenant_staging_settings", None)
        if settings is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Staging no configurado")
        return {
            "status": "ready",
            "environment": settings.app_env,
            "database": settings.cosmos_database_name,
            "multitenant_routes": settings.enable_multitenant_routes,
            "legacy_routes": settings.enable_legacy_routes,
            "containers_configured": sorted(required_containers),
            "production_database": False,
        }

    return router
