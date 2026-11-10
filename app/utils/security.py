import re

PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{12,128}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_password(password: str) -> tuple[bool, str]:
    if not isinstance(password, str) or not PASSWORD_RE.match(password):
        return (
            False,
            "Password must be 12-128 characters and include upper, lower, number and symbol.",
        )
    return True, ""


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(normalize_email(email)))
