from flask import Blueprint, request

from app.extensions import db
from app.models import Role, User
from app.services.audit import write_audit
from app.utils.authz import current_user, permission_required
from app.utils.responses import error, success
from app.utils.security import normalize_email, valid_email, validate_password

bp = Blueprint("users", __name__, url_prefix="/api/v1/users")


@bp.get("")
@permission_required("users.read")
def list_users():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("perPage", 20, type=int), 1), 100)
    query = User.query.order_by(User.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return success(
        {
            "items": [u.to_dict() for u in pagination.items],
            "page": page,
            "perPage": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        }
    )


@bp.post("")
@permission_required("users.create")
def create_user():
    actor = current_user()
    payload = request.get_json(silent=True) or {}
    email = normalize_email(payload.get("email"))
    full_name = (payload.get("fullName") or "").strip()
    password = payload.get("password") or ""
    role_names = payload.get("roles") or []

    if not valid_email(email) or not full_name:
        return error(400, "VALIDATION_ERROR", "A valid email and fullName are required.")
    valid, message = validate_password(password)
    if not valid:
        return error(400, "VALIDATION_ERROR", message)
    if User.query.filter_by(email=email).first():
        return error(409, "CONFLICT", "A user with that email already exists.")

    roles = Role.query.filter(Role.name.in_(role_names)).all() if role_names else []
    if len(roles) != len(set(role_names)):
        return error(400, "VALIDATION_ERROR", "One or more roles do not exist.")

    user = User(email=email, full_name=full_name, is_active=bool(payload.get("isActive", True)))
    user.set_password(password)
    user.roles = roles
    db.session.add(user)
    db.session.flush()
    write_audit(
        action="user.create",
        resource_type="user",
        resource_id=user.id,
        outcome="SUCCESS",
        user=actor,
        details={"targetEmail": user.email, "roles": sorted(role_names)},
    )
    db.session.commit()
    return success(user.to_dict(), "User created.", 201)


@bp.get("/<user_id>")
@permission_required("users.read")
def get_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return error(404, "NOT_FOUND", "User not found.")
    return success(user.to_dict())


@bp.patch("/<user_id>")
@permission_required("users.update")
def update_user(user_id):
    actor = current_user()
    user = db.session.get(User, user_id)
    if not user:
        return error(404, "NOT_FOUND", "User not found.")

    payload = request.get_json(silent=True) or {}
    if "fullName" in payload:
        full_name = (payload.get("fullName") or "").strip()
        if not full_name:
            return error(400, "VALIDATION_ERROR", "fullName cannot be empty.")
        user.full_name = full_name
    if "isActive" in payload:
        user.is_active = bool(payload["isActive"])

    write_audit(
        action="user.update",
        resource_type="user",
        resource_id=user.id,
        outcome="SUCCESS",
        user=actor,
        details={"targetEmail": user.email, "fields": sorted(payload.keys())},
    )
    db.session.commit()
    return success(user.to_dict(), "User updated.")


@bp.put("/<user_id>/roles")
@permission_required("users.assign_roles")
def set_user_roles(user_id):
    actor = current_user()
    user = db.session.get(User, user_id)
    if not user:
        return error(404, "NOT_FOUND", "User not found.")

    payload = request.get_json(silent=True) or {}
    role_names = payload.get("roles")
    if not isinstance(role_names, list):
        return error(400, "VALIDATION_ERROR", "roles must be an array.")
    roles = Role.query.filter(Role.name.in_(role_names)).all() if role_names else []
    if len(roles) != len(set(role_names)):
        return error(400, "VALIDATION_ERROR", "One or more roles do not exist.")

    user.roles = roles
    write_audit(
        action="user.roles.update",
        resource_type="user",
        resource_id=user.id,
        outcome="SUCCESS",
        user=actor,
        details={"targetEmail": user.email, "roles": sorted(role_names)},
    )
    db.session.commit()
    return success(user.to_dict(), "User roles updated.")
