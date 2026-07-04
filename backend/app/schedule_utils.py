"""Pure helpers for expanding a recurring weekly schedule into dated sessions.

The schedule lives on ``plan.metadata["schedule"]`` (see schemas.PlanSchedule)
and is stored with camelCase keys, matching how the API speaks to the app.
"""

from datetime import date, datetime, timedelta

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
WEEKDAY_INDEX = {d: i for i, d in enumerate(WEEKDAYS)}


def _as_date(value) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def resolve_sessions(schedule: dict | None) -> list[dict]:
    """Expand a stored schedule into concrete dated sessions across the cycle.

    Weeks are anchored to the Monday of the week containing ``startDate``;
    occurrences before ``startDate`` (in week 0) are dropped. Returns a list of
    ``{date, weekday, title, routineId}`` dicts sorted by date.
    """
    if not schedule:
        return []
    start = _as_date(schedule.get("startDate"))
    if start is None:
        return []
    try:
        weeks = int(schedule.get("weeks", 0))
    except (TypeError, ValueError):
        weeks = 0
    days = schedule.get("days") or {}
    if weeks < 1 or not days:
        return []

    anchor_monday = start - timedelta(days=start.weekday())
    sessions: list[dict] = []
    for week in range(weeks):
        week_monday = anchor_monday + timedelta(days=7 * week)
        for weekday, ref in days.items():
            idx = WEEKDAY_INDEX.get(weekday)
            if idx is None:
                continue
            day = week_monday + timedelta(days=idx)
            if day < start:
                continue
            ref = ref or {}
            sessions.append({
                "date": day,
                "weekday": weekday,
                "title": ref.get("title") or weekday.capitalize(),
                "routineId": ref.get("routineId"),
            })
    sessions.sort(key=lambda s: s["date"])
    return sessions


def cycle_end_date(schedule: dict | None) -> date | None:
    """The date of the last session in the cycle, or None."""
    sessions = resolve_sessions(schedule)
    return sessions[-1]["date"] if sessions else None


def to_local_date(value) -> date | None:
    """Coerce a datetime/date/ISO-string to a calendar date."""
    if isinstance(value, datetime):
        return value.date()
    return _as_date(value)
