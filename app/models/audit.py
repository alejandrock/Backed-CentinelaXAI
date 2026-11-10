from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_email = db.Column(db.String(255), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(100), nullable=False, index=True)
    resource_id = db.Column(db.String(128), nullable=True)
    outcome = db.Column(db.String(32), nullable=False, index=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    request_id = db.Column(db.String(64), nullable=True, index=True)
    details = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    user = db.relationship("User", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "actorEmail": self.actor_email,
            "action": self.action,
            "resourceType": self.resource_type,
            "resourceId": self.resource_id,
            "outcome": self.outcome,
            "ipAddress": self.ip_address,
            "userAgent": self.user_agent,
            "requestId": self.request_id,
            "details": self.details,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
