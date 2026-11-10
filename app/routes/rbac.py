from flask import Blueprint, request

from app.extensions import db
from app.models import Permission, Role
from app.services.audit import write_audit
from app.utils.authz import current_user, permission_required
from app.utils.responses import error, success

bp = Blueprint("rbac", __name__, url_prefix="/api/v1")


@bp.get("/roles")
@permission_required("rbac.read")
def list_roles():
    return success([role.to_dict() for role in Role.query.order_by(Role.name).all()])


@bp.post("/roles")
@permission_required("rbac.manage")
def create_role():
    actor = current_user()
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip().lower()
    description = (payload.get("description") or "").strip()
    permission_codes = payload.get("permissions") or []
    if not name:
        return error(400, "VALIDATION_ERROR", "Role name is required.")
    if Role.query.filter_by(name=name).first():
        return error(409, "CONFLICT", "Role already exists.")

    permissions = (
        Permission.query.filter(Permission.code.in_(permission_codes)).all()
        if permission_codes
        else []
    )
    if len(permissions) != len(set(permission_codes)):
        return error(400, "VALIDATION_ERROR", "One or more permissions do not exist.")

    role = Role(name=name, description=description, permissions=permissions)
    db.session.add(role)
    db.session.flush()
    write_audit(
        action="role.create",
        resource_type="role",
        resource_id=role.id,
        outcome="SUCCESS",
        user=actor,
        details={"name": role.name, "permissions": sorted(permission_codes)},
    )
    db.session.commit()
    return success(role.to_dict(), "Role created.", 201)


@bp.put("/roles/<int:role_id>/permissions")
@permission_required("rbac.manage")
def set_role_permissions(role_id):
    actor = current_user()
    role = db.session.get(Role, role_id)
    if not role:
        return error(404, "NOT_FOUND", "Role not found.")
    if role.name == "admin":
        return error(409, "CONFLICT", "The admin role permission set is protected.")

    payload = request.get_json(silent=True) or {}
    codes = payload.get("permissions")
    if not isinstance(codes, list):
        return error(400, "VALIDATION_ERROR", "permissions must be an array.")
    permissions = Permission.query.filter(Permission.code.in_(codes)).all() if codes else []
    if len(permissions) != len(set(codes)):
        return error(400, "VALIDATION_ERROR", "One or more permissions do not exist.")

    role.permissions = permissions
    write_audit(
        action="role.permissions.update",
        resource_type="role",
        resource_id=role.id,
        outcome="SUCCESS",
        user=actor,
        details={"name": role.name, "permissions": sorted(codes)},
    )
    db.session.commit()
    return success(role.to_dict(), "Role permissions updated.")


@bp.get("/permissions")
@permission_required("rbac.read")
def list_permissions():
    return success([p.to_dict() for p in Permission.query.order_by(Permission.code).all()])
