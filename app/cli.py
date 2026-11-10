import os

import click
from flask import current_app
from flask.cli import with_appcontext

from app.extensions import db
from app.models import Permission, Role, User
from app.utils.security import normalize_email, validate_password

PERMISSIONS = {
    "*": "All permissions. Reserved for administrators.",
    "dashboard.read": "View dashboard data.",
    "urls.analyze": "Submit URLs for analysis.",
    "incidents.read": "View incidents.",
    "incidents.update": "Update incident workflow.",
    "logs.read": "View Linux/security logs.",
    "logs.manage": "Manage log sources and ingestion.",
    "correlations.read": "View correlated security cases.",
    "users.read": "View users.",
    "users.create": "Create users.",
    "users.update": "Update users and account status.",
    "users.assign_roles": "Assign roles to users.",
    "rbac.read": "View roles and permissions.",
    "rbac.manage": "Create roles and manage permissions.",
    "audit.read": "View security audit logs.",
    "profile.read": "View own profile.",
}

ROLE_PERMISSIONS = {
    "admin": ["*"],
    "soc_analyst": [
        "dashboard.read",
        "urls.analyze",
        "incidents.read",
        "incidents.update",
        "logs.read",
        "correlations.read",
        "profile.read",
    ],
    "linux_admin": ["dashboard.read", "logs.read", "logs.manage", "profile.read"],
    "security_auditor": [
        "dashboard.read",
        "incidents.read",
        "logs.read",
        "correlations.read",
        "audit.read",
        "rbac.read",
        "profile.read",
    ],
    "viewer": ["dashboard.read", "incidents.read", "profile.read"],
}

ROLE_DESCRIPTIONS = {
    "admin": "Full CentinelaX administration.",
    "soc_analyst": "SOC analyst for investigation and triage.",
    "linux_admin": "Linux log and infrastructure administrator.",
    "security_auditor": "Read-only security and audit reviewer.",
    "viewer": "Read-only operational viewer.",
}


def _get_or_create_user(email, name, password, role_name):
    if not password:
        return None
    valid, message = validate_password(password)
    if not valid:
        raise click.ClickException(f"Password for {email} is invalid: {message}")

    user = User.query.filter_by(email=normalize_email(email)).first()
    if not user:
        user = User(email=normalize_email(email), full_name=name, is_active=True)
        user.set_password(password)
        db.session.add(user)
    role = Role.query.filter_by(name=role_name).one()
    if role not in user.roles:
        user.roles.append(role)
    return user


@click.command("bootstrap")
@with_appcontext
def bootstrap_command():
    """Create tables, baseline RBAC, and optional bootstrap accounts."""
    db.create_all()

    permission_by_code = {}
    for code, description in PERMISSIONS.items():
        permission = Permission.query.filter_by(code=code).first()
        if not permission:
            permission = Permission(code=code, description=description)
            db.session.add(permission)
        permission_by_code[code] = permission
    db.session.flush()

    for name, codes in ROLE_PERMISSIONS.items():
        role = Role.query.filter_by(name=name).first()
        if not role:
            role = Role(name=name, description=ROLE_DESCRIPTIONS[name], is_system=True)
            db.session.add(role)
        role.permissions = [permission_by_code[code] for code in codes]
    db.session.flush()

    admin = _get_or_create_user(
        os.getenv("SEED_ADMIN_EMAIL", "admin@centinelax.ai"),
        os.getenv("SEED_ADMIN_NAME", "CentinelaX Administrator"),
        os.getenv("SEED_ADMIN_PASSWORD", ""),
        "admin",
    )
    soc = _get_or_create_user(
        os.getenv("SEED_SOC_EMAIL", "soc@centinelax.ai"),
        os.getenv("SEED_SOC_NAME", "SOC Analyst"),
        os.getenv("SEED_SOC_PASSWORD", ""),
        "soc_analyst",
    )
    db.session.commit()

    click.echo("RBAC baseline created/updated.")
    click.echo(f"Admin account: {'created/updated' if admin else 'skipped (no password)'}")
    click.echo(f"SOC account: {'created/updated' if soc else 'skipped (no password)'}")
    click.echo(f"Database: {current_app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]}")


def register_cli(app):
    app.cli.add_command(bootstrap_command)
