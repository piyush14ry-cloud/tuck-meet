"""The matching engine.

Runs daily (default 5:00 PM). For every opted-in, verified student it looks
for others who:
    1. opted into the same activity, and
    2. share at least one availability block (day + time-of-day),
    3. and have NOT been paired within the re-match cooldown window.

Coffee / walk / eating-out form pairs (2 people). Small-group meals form
groups of up to 4. Intro emails are then sent to each new match.

The algorithm is deterministic given its inputs (sorted by id), which keeps
it easy to test and to reason about during a security/privacy review.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from .extensions import db
from .emailer import send_email
from .models import (
    ACTIVITY_LABELS,
    Match,
    MatchMember,
    PairHistory,
    User,
    utcnow,
)

log = logging.getLogger("tuckmeet.matching")

GROUP_SIZES = {
    "coffee": 2,
    "walk": 2,
    "eating_out": 2,
    "small_group_meal": 4,
}


@dataclass
class MatchResult:
    created: int = 0
    people_matched: int = 0
    details: list[str] = field(default_factory=list)


def _recent_pairs(cooldown_days: int) -> set[tuple[int, int]]:
    """Return the set of (smaller_id, larger_id) pairs matched recently."""
    cutoff = utcnow() - timedelta(days=cooldown_days)
    rows = PairHistory.query.filter(PairHistory.matched_at >= cutoff).all()
    return {PairHistory.key(r.user_a_id, r.user_b_id) for r in rows}


def _form_groups(
    user_ids: list[int],
    size: int,
    blocked: set[tuple[int, int]],
) -> list[list[int]]:
    """Greedily build groups of `size` whose members are not mutually blocked.

    Inputs are pre-sorted for determinism. A simple, auditable heuristic -
    deliberately not a complex optimizer.
    """
    remaining = list(user_ids)
    groups: list[list[int]] = []

    while len(remaining) >= size:
        seed = remaining.pop(0)
        group = [seed]
        i = 0
        while i < len(remaining) and len(group) < size:
            cand = remaining[i]
            if all(PairHistory.key(cand, m) not in blocked for m in group):
                group.append(cand)
                remaining.pop(i)
            else:
                i += 1
        if len(group) == size:
            groups.append(group)
        # If we couldn't fill a group, the seed simply waits for next run.
    return groups


def run_matching(cooldown_days: int | None = None, send: bool = True) -> MatchResult:
    from flask import current_app

    if cooldown_days is None:
        cooldown_days = current_app.config["REMATCH_COOLDOWN_DAYS"]

    blocked = _recent_pairs(cooldown_days)
    result = MatchResult()

    users = [u for u in User.query.order_by(User.id).all() if u.is_matchable]
    by_id = {u.id: u for u in users}

    # Bucket eligible users by (activity, day, block).
    buckets: dict[tuple[str, str, str], list[int]] = {}
    for u in users:
        for activity in sorted(u.active_activities):
            for (day, block) in u.availability_slots:
                buckets.setdefault((activity, day, block), []).append(u.id)

    # Track who has already been placed this run so nobody is double-booked.
    placed: set[int] = set()

    for (activity, day, block) in sorted(buckets):
        size = GROUP_SIZES.get(activity, 2)
        candidates = sorted(uid for uid in buckets[(activity, day, block)] if uid not in placed)
        if len(candidates) < size:
            continue

        groups = _form_groups(candidates, size, blocked)
        for group in groups:
            if any(uid in placed for uid in group):
                continue
            placed.update(group)

            match = Match(activity=activity, day=day, block=block)
            db.session.add(match)
            db.session.flush()  # assign match.id

            for uid in group:
                db.session.add(MatchMember(match_id=match.id, user_id=uid))

            # Record every pair in the group for the cooldown.
            for a in range(len(group)):
                for b in range(a + 1, len(group)):
                    ka, kb = PairHistory.key(group[a], group[b])
                    db.session.add(PairHistory(user_a_id=ka, user_b_id=kb))
                    blocked.add((ka, kb))

            result.created += 1
            result.people_matched += len(group)
            names = ", ".join(by_id[uid].name for uid in group)
            result.details.append(f"{ACTIVITY_LABELS[activity]} ({day} {block}): {names}")

            if send:
                _notify_group(match, [by_id[uid] for uid in group])

    db.session.commit()
    log.info("Matching run complete: %s matches, %s people", result.created, result.people_matched)
    return result


def _notify_group(match: Match, members: list[User]) -> None:
    label = ACTIVITY_LABELS[match.activity]
    for person in members:
        others = [m for m in members if m.id != person.id]
        intro_lines = "\n".join(f"  - {o.name} ({o.email})" for o in others)
        body = (
            f"Hi {person.name},\n\n"
            f"You opted into Tuck Meet, and we found a low-pressure match for a "
            f"{label.lower()} around {match.day} {match.block}.\n\n"
            f"Say hello to:\n{intro_lines}\n\n"
            f"There's no obligation - reach out if it works, or skip it if this "
            f"week is busy. You can update your availability or opt out any time "
            f"from your Tuck Meet dashboard.\n\n"
            f"- Tuck Meet"
        )
        send_email(person.email, f"Tuck Meet: a {label.lower()} match", body)
