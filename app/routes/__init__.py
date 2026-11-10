from app.routes.audit import bp as audit_bp
from app.routes.auth import bp as auth_bp
from app.routes.health import bp as health_bp
from app.routes.rbac import bp as rbac_bp
from app.routes.users import bp as users_bp

BLUEPRINTS = [health_bp, auth_bp, users_bp, rbac_bp, audit_bp]
