from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)

from app.extensions import db
from app.models import RevokedToken, User
from app.services.audit import write_audit
from app.utils.responses import error, success
from app.utils.security import normalize_email, validate_password

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


def _utcnow():
    return datetime.now(timezone.utc)


def _is_locked(user: User) -> bool:
    if not user.locked_until:
        return False
    locked_until = user.locked_until
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return locked_until > _utcnow()


def _revoke_payload(payload: dict, user_id: str):
    jti = payload.get("jti")
    if not jti or db.session.get(RevokedToken, jti):
        return
    exp = payload.get("exp")
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else _utcnow()
    db.session.add(
        RevokedToken(
            jti=jti,
            token_type=payload.get("type", "unknown"),
            user_id=user_id,
            expires_at=expires_at,
        )
    )


@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = normalize_email(payload.get("email"))
    password = payload.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user:
        write_audit(
            action="auth.login",
            resource_type="session",
            outcome="FAILURE",
            actor_email=email or None,
            details={"reason": "invalid_credentials"},
        )
        db.session.commit()
        return error(401, "UNAUTHORIZED", "Invalid email or password.")

    if not user.is_active:
        write_audit(
            action="auth.login",
            resource_type="session",
            outcome="FAILURE",
            user=user,
            details={"reason": "inactive_account"},
        )
        db.session.commit()
        return error(403, "FORBIDDEN", "User account is inactive.")

    if _is_locked(user):
        write_audit(
            action="auth.login",
            resource_type="session",
            outcome="FAILURE",
            user=user,
            details={"reason": "account_locked"},
        )
        db.session.commit()
        return error(423, "LOCKED", "Account temporarily locked after failed logins.")

    if not user.verify_password(password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= current_app.config["MAX_LOGIN_ATTEMPTS"]:
            user.locked_until = _utcnow() + timedelta(
                minutes=current_app.config["LOGIN_LOCK_MINUTES"]
            )
            user.failed_login_attempts = 0
        write_audit(
            action="auth.login",
            resource_type="session",
            outcome="FAILURE",
            user=user,
            details={"reason": "invalid_credentials"},
        )
        db.session.commit()
        return error(401, "UNAUTHORIZED", "Invalid email or password.")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = _utcnow()
    access_token = create_access_token(identity=user.id, fresh=True)
    refresh_token = create_refresh_token(identity=user.id)

    write_audit(
        action="auth.login",
        resource_type="session",
        outcome="SUCCESS",
        user=user,
    )
    db.session.commit()

    response, status = success({"user": user.to_dict()}, "Login successful.")
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response, status


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return error(403, "FORBIDDEN", "User account is inactive or unavailable.")

    old_refresh = get_jwt()
    _revoke_payload(old_refresh, user.id)

    access_token = create_access_token(identity=user.id, fresh=False)
    refresh_token = create_refresh_token(identity=user.id)
    write_audit(
        action="auth.refresh",
        resource_type="session",
        outcome="SUCCESS",
        user=user,
    )
    db.session.commit()

    response, status = success({"user": user.to_dict()}, "Session refreshed.")
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response, status


@bp.post("/logout")
@jwt_required()
def logout():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    _revoke_payload(get_jwt(), user_id)

    refresh_raw = request.cookies.get(current_app.config["JWT_REFRESH_COOKIE_NAME"])
    if refresh_raw:
        try:
            refresh_payload = decode_token(refresh_raw, allow_expired=True)
            _revoke_payload(refresh_payload, user_id)
        except Exception:
            pass

    if user:
        write_audit(
            action="auth.logout",
            resource_type="session",
            outcome="SUCCESS",
            user=user,
        )
    db.session.commit()

    response, status = success(message="Logout successful.")
    unset_jwt_cookies(response)
    return response, status


@bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, get_jwt_identity())
    if not user or not user.is_active:
        return error(403, "FORBIDDEN", "User account is inactive or unavailable.")
    return success(user.to_dict())


@bp.post("/change-password")
@jwt_required(fresh=True)
def change_password():
    user = db.session.get(User, get_jwt_identity())
    if not user or not user.is_active:
        return error(403, "FORBIDDEN", "User account is inactive or unavailable.")

    payload = request.get_json(silent=True) or {}
    current_password = payload.get("currentPassword") or ""
    new_password = payload.get("newPassword") or ""

    if not user.verify_password(current_password):
        write_audit(
            action="auth.change_password",
            resource_type="user",
            resource_id=user.id,
            outcome="FAILURE",
            user=user,
            details={"reason": "invalid_current_password"},
        )
        db.session.commit()
        return error(401, "UNAUTHORIZED", "Current password is invalid.")

    valid, message = validate_password(new_password)
    if not valid:
        return error(400, "VALIDATION_ERROR", message)

    user.set_password(new_password)
    write_audit(
        action="auth.change_password",
        resource_type="user",
        resource_id=user.id,
        outcome="SUCCESS",
        user=user,
    )
    db.session.commit()
    return success(message="Password changed successfully.")
