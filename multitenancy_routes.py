from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from multitenancy_auth import (
    InstitutionalAuthService,
    get_current_tenant_context,
    get_multitenant_auth_service,
    require_tenant_permission,
)
from multitenancy_models import InstitutionalLoginRequest, TenantContext, TokenResponse
from multitenancy_repositories import TenantAwareStudentRepository


def create_multitenancy_router(students_repository: TenantAwareStudentRepository) -> APIRouter:
    router = APIRouter()

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

    @router.get("/students")
    async def list_students(
        context: TenantContext = Depends(require_tenant_permission("students.read")),
    ):
        return students_repository.list_students(context.tenant_id)

    @router.get("/students/{student_id}")
    async def get_student(
        student_id: str,
        context: TenantContext = Depends(require_tenant_permission("students.read")),
    ):
        student = students_repository.get_student(context.tenant_id, student_id)
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado")
        return student

    @router.post("/students", status_code=status.HTTP_201_CREATED)
    async def create_student(
        payload: dict,
        context: TenantContext = Depends(require_tenant_permission("students.write")),
    ):
        return students_repository.create_student(context.tenant_id, payload)

    @router.patch("/students/{student_id}")
    async def update_student(
        student_id: str,
        payload: dict,
        context: TenantContext = Depends(require_tenant_permission("students.write")),
    ):
        student = students_repository.update_student(context.tenant_id, student_id, payload)
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado")
        return student

    @router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_student(
        student_id: str,
        context: TenantContext = Depends(require_tenant_permission("students.write")),
    ):
        if not students_repository.delete_student(context.tenant_id, student_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado")
        return None

    @router.get("/tenants/{tenant_id}/students/{student_id}")
    async def get_student_with_tenant_in_url(
        tenant_id: str,
        student_id: str,
        context: TenantContext = Depends(require_tenant_permission("students.read")),
    ):
        if tenant_id != context.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado")
        student = students_repository.get_student(context.tenant_id, student_id)
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado")
        return student

    return router
