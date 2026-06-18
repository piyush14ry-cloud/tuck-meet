"""Authentication: register, email verification, login, logout."""
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required, login_user, logout_user
from sqlalchemy import func

from .emailer import send_email
from .extensions import db, login_manager
from .forms import LoginForm, RegisterForm
from .models import User
from .tokens import generate_email_token, verify_email_token

auth_bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


def _send_verification(user: User) -> None:
    token = generate_email_token(user.email)
    link = url_for("auth.verify_email", token=token, _external=True)
    send_email(
        user.email,
        "Verify your Tuck Meet account",
        f"Hi {user.name},\n\nConfirm your email to activate Tuck Meet:\n{link}\n\n"
        f"This link expires in 3 days. If you didn't sign up, ignore this email.\n",
    )


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        # Case-insensitive uniqueness check.
        existing = User.query.filter(func.lower(User.email) == email).first()
        if existing:
            # Avoid leaking which emails exist: behave the same either way.
            flash("If that address is eligible, a verification email is on its way.", "info")
            return redirect(url_for("auth.login"))

        user = User(name=form.name.data.strip(), email=email)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        _send_verification(user)
        flash("Account created. Check your Tuck email to verify and activate it.", "success")
        return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)


@auth_bp.route("/verify/<token>")
def verify_email(token: str):
    email = verify_email_token(token)
    if not email:
        flash("That verification link is invalid or has expired.", "error")
        return redirect(url_for("auth.login"))
    user = User.query.filter(func.lower(User.email) == email).first()
    if user and not user.email_verified:
        user.email_verified = True
        db.session.commit()
        flash("Email verified. You can sign in now.", "success")
    else:
        flash("Email already verified. Please sign in.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter(func.lower(User.email) == email).first()
        # Generic error message - never reveal whether the email or the
        # password was the problem.
        if not user or not user.check_password(form.password.data):
            flash("Invalid email or password.", "error")
            return render_template("login.html", form=form)
        if not user.email_verified:
            flash("Please verify your email first - check your inbox.", "error")
            return render_template("login.html", form=form)

        login_user(user, remember=form.remember.data)
        next_url = request.args.get("next")
        # Prevent open-redirects: only allow same-site relative paths.
        if not next_url or not next_url.startswith("/"):
            next_url = url_for("main.dashboard")
        return redirect(next_url)
    return render_template("login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been signed out.", "info")
    return redirect(url_for("main.index"))
