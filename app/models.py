"""Database models for Tuck Meet.

Design notes (privacy by design):
  * We store the minimum needed: a verified Tuck email, a display name, a
    password hash, coarse availability, and activity opt-ins.
  * No chat messages, no profiles, no social graph, no location data.
  * Passwords are never stored in plaintext - only a salted hash.
"""
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Coarse, low-pressure availability blocks. Kept deliberately simple so we
# never need anyone's calendar or precise location.
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
BLOCKS = ["morning", "afternoon", "evening"]

# The activity types a student can opt into.
ACTIVITIES = ["coffee", "walk", "eating_out", "small_group_meal"]
ACTIVITY_LABELS = {
    "coffee": "Coffee",
    "walk": "Walk",
    "eating_out": "Eating out",
    "small_group_meal": "Small-group meal",
}


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # Master switch: only opted-in, verified users are ever matched.
    opted_in = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    availability = db.relationship(
        "Availability", backref="user", cascade="all, delete-orphan", lazy="selectin"
    )
    preferences = db.relationship(
        "ActivityPreference", backref="user", cascade="all, delete-orphan", lazy="selectin"
    )

    # --- Password helpers ---
    def set_password(self, raw: str) -> None:
        # pbkdf2:sha256 with a per-user salt, provided by Werkzeug.
        self.password_hash = generate_password_hash(raw, method="pbkdf2:sha256:600000")

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    # --- Convenience ---
    @property
    def availability_slots(self) -> set[tuple[str, str]]:
        return {(a.day, a.block) for a in self.availability}

    @property
    def active_activities(self) -> set[str]:
        return {p.activity for p in self.preferences if p.enabled}

    @property
    def is_matchable(self) -> bool:
        return (
            self.email_verified
            and self.opted_in
            and bool(self.active_activities)
            and bool(self.availability_slots)
        )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Availability(db.Model):
    __tablename__ = "availability"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    day = db.Column(db.String(3), nullable=False)    # one of DAYS
    block = db.Column(db.String(10), nullable=False)  # one of BLOCKS

    __table_args__ = (
        db.UniqueConstraint("user_id", "day", "block", name="uq_avail_slot"),
    )


class ActivityPreference(db.Model):
    __tablename__ = "activity_preferences"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    activity = db.Column(db.String(20), nullable=False)  # one of ACTIVITIES
    enabled = db.Column(db.Boolean, default=True, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "activity", name="uq_activity_pref"),
    )


class Match(db.Model):
    __tablename__ = "matches"
    id = db.Column(db.Integer, primary_key=True)
    activity = db.Column(db.String(20), nullable=False)
    day = db.Column(db.String(3), nullable=False)
    block = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    members = db.relationship(
        "MatchMember", backref="match", cascade="all, delete-orphan", lazy="selectin"
    )


class MatchMember(db.Model):
    __tablename__ = "match_members"
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user = db.relationship("User")


class PairHistory(db.Model):
    """Records that two users were matched, to enforce a re-match cooldown.

    user_a_id is always the smaller id, so each pair is stored once.
    """
    __tablename__ = "pair_history"
    id = db.Column(db.Integer, primary_key=True)
    user_a_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_b_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    matched_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    __table_args__ = (
        db.Index("ix_pair", "user_a_id", "user_b_id"),
    )

    @staticmethod
    def key(a_id: int, b_id: int) -> tuple[int, int]:
        return (a_id, b_id) if a_id < b_id else (b_id, a_id)
