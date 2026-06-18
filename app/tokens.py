"""Signed, expiring tokens for email verification (no DB row needed).

Uses itsdangerous with the app SECRET_KEY, so tokens can't be forged without
the server secret and they expire on their own.
"""
from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_SALT = "tuckmeet-email-verify"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=_SALT)


def generate_email_token(email: str) -> str:
    return _serializer().dumps(email.lower())


def verify_email_token(token: str, max_age_seconds: int = 60 * 60 * 24 * 3) -> str | None:
    """Return the email if the token is valid and unexpired, else None."""
    try:
        return _serializer().loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
