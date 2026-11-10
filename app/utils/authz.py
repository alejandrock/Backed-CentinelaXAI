from functools import wraps

from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import User
from app.utils.responses import error


def current_user():
    identity = get_jwt_identity()
    if not identity:
        return None
    return db.session.get(User, identity)


def permission_required(permission: str):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user or not user.is_active:
                return error(403, "FORBIDDEN", "User account is inactive or unavailable.")
            if not user.has_permission(permission):
                return error(403, "FORBIDDEN", f"Missing permission: {permission}")
            return fn(*args, **kwargs)

        return wrapped

    return decorator
