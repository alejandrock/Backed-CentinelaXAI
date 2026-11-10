from datetime import datetime

from flask import Blueprint, request

from app.extensions import db
from app.models import AuditLog
from app.utils.authz import permission_required
from app.utils.responses import success

bp = Blueprint("audit", __name__, url_prefix="/api/v1/audit-logs")


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@bp.get("")
@permission_required("audit.read")
def list_audit_logs():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("perPage", 50, type=int), 1), 200)

    query = AuditLog.query
    if action := request.args.get("action"):
        query = query.filter(AuditLog.action == action)
    if outcome := request.args.get("outcome"):
        query = query.filter(AuditLog.outcome == outcome.upper())
    if actor_email := request.args.get("actorEmail"):
        query = query.filter(AuditLog.actor_email == actor_email.strip().lower())
    if date_from := _parse_iso(request.args.get("from")):
        query = query.filter(AuditLog.created_at >= date_from)
    if date_to := _parse_iso(request.args.get("to")):
        query = query.filter(AuditLog.created_at <= date_to)

    query = query.order_by(AuditLog.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return success(
        {
            "items": [entry.to_dict() for entry in pagination.items],
            "page": page,
            "perPage": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        }
    )
