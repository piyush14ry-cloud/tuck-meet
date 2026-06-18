"""Tests for the matching engine - the core, security-relevant logic."""
from app.extensions import db
from app.matching import run_matching
from app.models import (
    ActivityPreference,
    Availability,
    Match,
    PairHistory,
    User,
)


def make_user(name, email, activities, slots, verified=True, opted_in=True):
    u = User(name=name, email=email, email_verified=verified, opted_in=opted_in)
    u.set_password("longenoughpw1")
    db.session.add(u)
    db.session.flush()
    for a in activities:
        db.session.add(ActivityPreference(user_id=u.id, activity=a, enabled=True))
    for (day, block) in slots:
        db.session.add(Availability(user_id=u.id, day=day, block=block))
    db.session.commit()
    return u


def test_pairs_two_users_with_shared_slot_and_activity(app, db):
    with app.app_context():
        make_user("A", "a@tuck.dartmouth.edu", ["coffee"], [("Mon", "morning")])
        make_user("B", "b@tuck.dartmouth.edu", ["coffee"], [("Mon", "morning")])
        result = run_matching(send=False)
        assert result.created == 1
        assert result.people_matched == 2
        assert Match.query.count() == 1


def test_no_match_without_shared_slot(app, db):
    with app.app_context():
        make_user("A", "a@tuck.dartmouth.edu", ["coffee"], [("Mon", "morning")])
        make_user("B", "b@tuck.dartmouth.edu", ["coffee"], [("Tue", "evening")])
        result = run_matching(send=False)
        assert result.created == 0


def test_no_match_without_shared_activity(app, db):
    with app.app_context():
        make_user("A", "a@tuck.dartmouth.edu", ["coffee"], [("Mon", "morning")])
        make_user("B", "b@tuck.dartmouth.edu", ["walk"], [("Mon", "morning")])
        result = run_matching(send=False)
        assert result.created == 0


def test_unverified_or_optedout_users_are_skipped(app, db):
    with app.app_context():
        make_user("A", "a@tuck.dartmouth.edu", ["coffee"], [("Mon", "morning")], verified=False)
        make_user("B", "b@tuck.dartmouth.edu", ["coffee"], [("Mon", "morning")], opted_in=False)
        result = run_matching(send=False)
        assert result.created == 0


def test_cooldown_prevents_immediate_rematch(app, db):
    with app.app_context():
        make_user("A", "a@tuck.dartmouth.edu", ["coffee"], [("Mon", "morning")])
        make_user("B", "b@tuck.dartmouth.edu", ["coffee"], [("Mon", "morning")])
        run_matching(send=False)
        assert PairHistory.query.count() == 1
        # Second run on the same day should not re-pair them.
        result = run_matching(send=False)
        assert result.created == 0


def test_small_group_meal_forms_group_of_four(app, db):
    with app.app_context():
        for i in range(4):
            make_user(f"U{i}", f"u{i}@tuck.dartmouth.edu",
                      ["small_group_meal"], [("Wed", "evening")])
        result = run_matching(send=False)
        assert result.created == 1
        assert result.people_matched == 4


def test_stub_email_sent_on_match(app, db):
    with app.app_context():
        make_user("A", "a@tuck.dartmouth.edu", ["coffee"], [("Mon", "morning")])
        make_user("B", "b@tuck.dartmouth.edu", ["coffee"], [("Mon", "morning")])
        # send=True exercises the stub email path (writes to ./outbox).
        result = run_matching(send=True)
        assert result.created == 1
