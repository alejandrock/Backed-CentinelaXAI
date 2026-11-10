import pytest

from app import create_app
from app.cli import PERMISSIONS
from app.extensions import db
from app.models import Permission, Role, User


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {}
    JWT_SECRET_KEY = "test-jwt-secret"
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_ACCESS_COOKIE_NAME = "cx_access_token"
    JWT_REFRESH_COOKIE_NAME = "cx_refresh_token"
    JWT_ACCESS_CSRF_COOKIE_NAME = "cx_csrf_access"
    JWT_REFRESH_CSRF_COOKIE_NAME = "cx_csrf_refresh"
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_ACCESS_TOKEN_EXPIRES = False
    JWT_REFRESH_TOKEN_EXPIRES = False
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCK_MINUTES = 15
    TRUST_PROXY = False
    CORS_ORIGINS = []

    @classmethod
    def init_app(cls, app):
        pass


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        permissions = {}
        for code, description in PERMISSIONS.items():
            p = Permission(code=code, description=description)
            db.session.add(p)
            permissions[code] = p
        db.session.flush()

        admin_role = Role(name="admin", description="Admin", permissions=[permissions["*"]])
        soc_role = Role(
            name="soc_analyst",
            description="SOC",
            permissions=[permissions["dashboard.read"], permissions["profile.read"]],
        )
        db.session.add_all([admin_role, soc_role])
        db.session.flush()

        admin = User(email="admin@centinelax.ai", full_name="Admin")
        admin.set_password("Strong!Admin123")
        admin.roles.append(admin_role)
        soc = User(email="soc@centinelax.ai", full_name="SOC")
        soc.set_password("Strong!Soc12345")
        soc.roles.append(soc_role)
        db.session.add_all([admin, soc])
        db.session.commit()

        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
