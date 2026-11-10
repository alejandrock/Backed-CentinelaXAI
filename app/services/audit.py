from flask import g, request

from app.extensions import db
from app.models import AuditLog


def write_audit(
    *,
    action: str,
    resource_type: str,
    outcome: str,
    user=None,
    actor_email: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
):
    entry = AuditLog(
        user_id=getattr(user, "id", None),
        actor_email=actor_email or getattr(user, "email", None),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        outcome=outcome,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip(),
        user_agent=(request.user_agent.string or "")[:512],
        request_id=getattr(g, "request_id", None),
        details=details or {},
    )
    db.session.add(entry)
    return entry
