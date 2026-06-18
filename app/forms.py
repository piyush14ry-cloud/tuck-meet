"""WTForms definitions. Flask-WTF adds CSRF protection automatically and
server-side validation runs on every submit (never trust the client)."""
from flask import current_app
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    ValidationError,
)


class _DomainRestricted:
    """Reject any email outside the configured Tuck domain."""

    def __call__(self, form, field):
        domain = current_app.config["ALLOWED_EMAIL_DOMAIN"]
        value = (field.data or "").strip().lower()
        if not value.endswith("@" + domain):
            raise ValidationError(f"Please use your @{domain} email address.")


class RegisterForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Tuck email", validators=[DataRequired(), Email(), _DomainRestricted()])
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=12, max=128,
                    message="Use at least 12 characters.")],
    )
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    email = StringField("Tuck email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Keep me signed in")
    submit = SubmitField("Sign in")


class PreferencesForm(FlaskForm):
    """Availability + activity opt-ins are rendered/validated manually in the
    view because they are dynamic checkbox grids; this form just carries CSRF
    and the opt-in master switch."""
    opted_in = BooleanField("I'm open to being matched")
    submit = SubmitField("Save preferences")
