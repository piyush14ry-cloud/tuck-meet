"""Main pages: landing, dashboard, preferences, and the matching trigger."""
import hmac

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from .extensions import db
from .forms import PreferencesForm
from .matching import run_matching
from .models import (
    ACTIVITIES,
    ACTIVITY_LABELS,
    BLOCKS,
    DAYS,
    Availability,
    ActivityPreference,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    matches = sorted(
        (m.match for m in current_user_matches()),
        key=lambda m: m.created_at,
        reverse=True,
    )
    return render_template(
        "dashboard.html",
        matches=matches[:10],
        activity_labels=ACTIVITY_LABELS,
        matchable=current_user.is_matchable,
    )


def current_user_matches():
    from .models import MatchMember
    return MatchMember.query.filter_by(user_id=current_user.id).all()


@main_bp.route("/preferences", methods=["GET", "POST"])
@login_required
def preferences():
    form = PreferencesForm()
    if form.validate_on_submit():
        # --- Availability: rebuild from posted checkboxes ---
        Availability.query.filter_by(user_id=current_user.id).delete()
        for day in DAYS:
            for block in BLOCKS:
                if request.form.get(f"avail-{day}-{block}"):
                    db.session.add(Availability(user_id=current_user.id, day=day, block=block))

        # --- Activity opt-ins ---
        ActivityPreference.query.filter_by(user_id=current_user.id).delete()
        for activity in ACTIVITIES:
            if request.form.get(f"activity-{activity}"):
                db.session.add(
                    ActivityPreference(user_id=current_user.id, activity=activity, enabled=True)
                )

        current_user.opted_in = bool(form.opted_in.data)
        db.session.commit()
        flash("Preferences saved.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template(
        "preferences.html",
        form=form,
        days=DAYS,
        blocks=BLOCKS,
        activities=ACTIVITIES,
        activity_labels=ACTIVITY_LABELS,
        selected_slots=current_user.availability_slots,
        selected_activities=current_user.active_activities,
        opted_in=current_user.opted_in,
    )


@main_bp.route("/tasks/run-matching", methods=["POST"])
def trigger_matching():
    """Trigger a matching run. Protected by a shared bearer token so it can be
    called by a scheduler (cron) without a logged-in session. Constant-time
    comparison avoids timing attacks.
    """
    expected = current_app.config["MATCHING_TRIGGER_TOKEN"]
    if not expected:
        abort(503, "Matching trigger is not configured.")
    provided = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not hmac.compare_digest(provided, expected):
        abort(403)
    result = run_matching()
    return jsonify(
        matches_created=result.created,
        people_matched=result.people_matched,
        details=result.details,
    )
