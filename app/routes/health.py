from flask import Blueprint
from sqlalchemy import text

from app.extensions import db
from app.utils.responses import error, success

bp = Blueprint("health", __name__, url_prefix="/api/v1/health")


@bp.get("/live")
def live():
    return success({"service": "centinelax-auth-api", "status": "UP"})


@bp.get("/ready")
def ready():
    try:
        db.session.execute(text("SELECT 1"))
        return success({"database": "UP", "status": "READY"})
    except Exception:
        return error(503, "SERVICE_UNAVAILABLE", "Database is not ready.")
