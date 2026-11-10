from app.models import AuditLog


def test_failed_login_creates_audit_entry(app, client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@centinelax.ai", "password": "wrong"},
    )
    assert response.status_code == 401

    with app.app_context():
        entry = AuditLog.query.filter_by(action="auth.login", outcome="FAILURE").first()
        assert entry is not None
        assert entry.actor_email == "admin@centinelax.ai"
