from __future__ import annotations

from typing import List, Optional

from multitenancy_models import AuditEvent, sanitize_audit_details


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
