import uuid

from flask import Flask, g
from flask_cors import CORS
from flask_jwt_extended import get_jwt
from werkzeug.middleware.proxy_fix import ProxyFix

from app.cli import register_cli
from app.config import Config
from app.extensions import db, jwt, migrate
from app.logging_config import configure_logging
from app.models import RevokedToken
from app.routes import BLUEPRINTS
from app.utils.responses import error


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    config_object.init_app(app)

    if app.config.get("TRUST_PROXY"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    if app.config.get("CORS_ORIGINS"):
        CORS(
            app,
            origins=app.config["CORS_ORIGINS"],
            supports_credentials=True,
            allow_headers=["Content-Type", "X-CSRF-TOKEN", "X-Request-ID"],
        )

    configure_logging(app)

    @app.before_request
    def request_context():
        from flask import request

        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    @app.after_request
    def security_headers(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)

    register_cli(app)
    _register_jwt_handlers()
    _register_error_handlers(app)
    return app


def _register_jwt_handlers():
    @jwt.token_in_blocklist_loader
    def token_in_blocklist(_header, payload):
        return db.session.get(RevokedToken, payload.get("jti")) is not None

    @jwt.unauthorized_loader
    def unauthorized(reason):
        return error(401, "UNAUTHORIZED", reason)

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return error(422, "INVALID_TOKEN", reason)

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return error(401, "TOKEN_EXPIRED", "Authentication token has expired.")

    @jwt.revoked_token_loader
    def revoked_token(_header, _payload):
        return error(401, "TOKEN_REVOKED", "Authentication token has been revoked.")

    @jwt.needs_fresh_token_loader
    def fresh_token(_header, _payload):
        return error(401, "FRESH_TOKEN_REQUIRED", "Fresh authentication is required.")


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(_exc):
        return error(404, "NOT_FOUND", "Resource not found.")

    @app.errorhandler(405)
    def method_not_allowed(_exc):
        return error(405, "METHOD_NOT_ALLOWED", "HTTP method not allowed.")

    @app.errorhandler(500)
    def internal_error(_exc):
        db.session.rollback()
        app.logger.exception("Unhandled application error")
        return error(500, "INTERNAL_SERVER_ERROR", "Unexpected server error.")
