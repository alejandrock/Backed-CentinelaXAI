import uuid
from datetime import datetime, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.extensions import db
from app.models.rbac import user_roles

ph = PasswordHasher()


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(160), nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime(timezone=True), nullable=True)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)
    password_changed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    roles = db.relationship("Role", secondary=user_roles, lazy="selectin", back_populates="users")

    def set_password(self, password: str) -> None:
        self.password_hash = ph.hash(password)
        self.password_changed_at = utcnow()

    def verify_password(self, password: str) -> bool:
        try:
            ok = ph.verify(self.password_hash, password)
            if ok and ph.check_needs_rehash(self.password_hash):
                self.password_hash = ph.hash(password)
            return ok
        except (VerifyMismatchError, InvalidHashError):
            return False

    def permission_codes(self) -> set[str]:
        return {p.code for role in self.roles for p in role.permissions}

    def has_permission(self, code: str) -> bool:
        perms = self.permission_codes()
        return "*" in perms or code in perms

    def to_dict(self, include_permissions: bool = True):
        data = {
            "id": self.id,
            "email": self.email,
            "fullName": self.full_name,
            "isActive": self.is_active,
            "roles": sorted(role.name for role in self.roles),
            "lastLoginAt": self.last_login_at.isoformat() if self.last_login_at else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
        if include_permissions:
            data["permissions"] = sorted(self.permission_codes())
        return data
