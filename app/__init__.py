"""Application factory for Tuck Meet."""
import logging

import click
from flask import Flask

from .extensions import csrf, db, login_manager
from config import Config, validate


def create_app(config_object: type[Config] = Config) -> Flask:
    validate(config_object)

    app = Flask(__name__)
    app.config.from_object(config_object)

    logging.basicConfig(level=logging.INFO)

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Blueprints
    from .auth import auth_bp
    from .main import main_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    _register_security_headers(app)
    _register_cli(app)

    with app.app_context():
        db.create_all()

    return app


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def set_secure_headers(resp):
        # Conservative defaults; the app serves only its own first-party assets.
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        if app.config.get("SESSION_COOKIE_SECURE"):
            resp.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return resp


def _register_cli(app: Flask) -> None:
    @app.cli.command("run-matching")
    def run_matching_cmd():
        """Run the matching engine once (used by the daily 5 PM job)."""
        from .matching import run_matching
        result = run_matching()
        click.echo(f"Created {result.created} matches for {result.people_matched} people.")
        for line in result.details:
            click.echo(f"  - {line}")

    @app.cli.command("make-admin")
    @click.argument("email")
    def make_admin_cmd(email):
        """Grant admin to an existing user by email."""
        from .models import User
        user = User.query.filter(User.email == email.lower()).first()
        if not user:
            click.echo("No such user.")
            return
        user.is_admin = True
        db.session.commit()
        click.echo(f"{email} is now an admin.")
