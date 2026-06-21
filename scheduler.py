"""
scheduler.py — Conflict-free interview scheduling engine.

Implements collision detection (any two interviews within a 2-hour window
are flagged) and a next-available-slot suggestion algorithm constrained to
business hours (09:00-18:00, Mon-Fri).
"""

from __future__ import annotations

from datetime import datetime, timedelta, time
from typing import List, Optional, Tuple

from models import Application

COLLISION_WINDOW = timedelta(hours=2)
BUSINESS_START = time(9, 0)
BUSINESS_END = time(18, 0)
SLOT_STEP = timedelta(minutes=30)


def detect_collision(
    candidate: datetime,
    applications: List[Application],
    exclude_id: Optional[str] = None,
) -> Optional[Application]:
    """Return the first conflicting Application, or None if the slot is clear."""
    for app in applications:
        if app.id == exclude_id or app.interview_datetime is None:
            continue
        delta = abs(candidate - app.interview_datetime)
        if delta < COLLISION_WINDOW:
            return app
    return None


def _is_business_hours(dt: datetime) -> bool:
    return dt.weekday() < 5 and BUSINESS_START <= dt.time() <= BUSINESS_END


def _next_business_day_start(dt: datetime) -> datetime:
    nxt = (dt + timedelta(days=1)).replace(
        hour=BUSINESS_START.hour, minute=0, second=0, microsecond=0
    )
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return nxt


def suggest_next_slot(
    candidate: datetime,
    applications: List[Application],
    exclude_id: Optional[str] = None,
    max_lookahead_days: int = 7,
) -> datetime:
    """
    Walk forward in SLOT_STEP increments from the requested time until a
    collision-free, business-hours slot is found.
    """
    probe = candidate
    deadline = candidate + timedelta(days=max_lookahead_days)

    while probe < deadline:
        if not _is_business_hours(probe):
            probe = _next_business_day_start(probe)
            continue

        if probe.time() > BUSINESS_END:
            probe = _next_business_day_start(probe)
            continue

        if detect_collision(probe, applications, exclude_id) is None:
            return probe

        probe += SLOT_STEP

    return probe


def validate_and_schedule(
    candidate: datetime,
    applications: List[Application],
    exclude_id: Optional[str] = None,
) -> Tuple[bool, Optional[Application], Optional[datetime]]:
    """
    Returns (is_clear, conflicting_application_or_None, suggested_slot_or_None).
    """
    conflict = detect_collision(candidate, applications, exclude_id)
    if conflict is None:
        return True, None, None
    suggestion = suggest_next_slot(candidate, applications, exclude_id)
    return False, conflict, suggestion
