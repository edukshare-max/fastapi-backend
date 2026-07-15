from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from multitenancy_models import AuditEvent, sanitize_audit_details
from multitenancy_repositories import build_tenant_month_key


class InMemoryAuditLogger:
    def __init__(self) -> None:
        self.events: List[AuditEvent] = []

    def record(
        self,
        *,
        tenant_id: Optional[str],
        actor_user_id: Optional[str],
        session_id: Optional[str],
        action: str,
        result: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_id=session_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
            details=sanitize_audit_details(details),
        )
        self.events.append(event)
        return event


class CosmosAuditLogger:
    def __init__(self, helper=None) -> None:
        from cosmos_helper import CosmosDBHelper

        self.audit_logs = helper or CosmosDBHelper("audit_logs_v2", "/tenant_month_key")

    def record(
        self,
        *,
        tenant_id: Optional[str],
        actor_user_id: Optional[str],
        session_id: Optional[str],
        action: str,
        result: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> dict:
        occurred_at_utc = datetime.now(timezone.utc)
        tenant_month_key = build_tenant_month_key(tenant_id or "platform", occurred_at_utc)
        item = {
            "id": f"{tenant_month_key}|{occurred_at_utc.isoformat()}|{action}",
            "tenant_id": tenant_id,
            "tenant_month_key": tenant_month_key,
            "actor_user_id": actor_user_id,
            "session_id": session_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "occurred_at_utc": occurred_at_utc.isoformat(),
            "result": result,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "correlation_id": correlation_id,
            "details": sanitize_audit_details(details),
        }
        return self.audit_logs.create_item(item)
