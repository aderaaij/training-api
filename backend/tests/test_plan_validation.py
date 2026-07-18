"""Plan-soundness validation: pure-module unit tests + route integration.

Pure tests construct PlannedSession/HistoryRun directly and anchor all dates
relative to a fixed "today" so they are deterministic. Route tests exercise
the real create-queue → validation path via TestClient.
"""

from datetime import date, datetime, time, timedelta, timezone

from app.plan_validation import (
    HistoryRun,
    PlannedSession,
    estimate_easy_speed,
    extract_guardrails,
    extract_race_date,
    session_from_composition,
    validate_schedule,
)

TODAY = date(2026, 7, 15)  # a Wednesday
NEXT_MONDAY = date(2026, 7, 20)


def codes(warnings, severity=None):
    return [w["code"] for w in warnings if severity is None or w["severity"] == severity]


def history_weeks(km_per_week: list[float], runs_per_week: int = 3) -> list[HistoryRun]:
    """Fill the weeks immediately before NEXT_MONDAY, newest week last."""
    out = []
    for i, km in enumerate(reversed(km_per_week)):  # i=0 → last week
        monday = NEXT_MONDAY - timedelta(weeks=i + 1)
        per_run = km / runs_per_week
        for j in range(runs_per_week):
            out.append(HistoryRun(
                date=monday + timedelta(days=j * 2),
                distance_m=per_run * 1000,
                duration_s=per_run * 1000 / 3.0,  # 3 m/s ≈ 5:33/km
            ))
    return out


def week_of_runs(week_start: date, kms: list[float], hard_days: list[int] = ()) -> list[PlannedSession]:
    return [
        PlannedSession(
            date=week_start + timedelta(days=i * 2 % 7),
            title=f"run {km}k",
            distance_m=km * 1000,
            duration_s=km * 1000 / 3.0,
            hard=(i in hard_days),
        )
        for i, km in enumerate(kms)
    ]


# ── composition parsing ──


def test_distance_goal_easy_run():
    comp = {"blocks": [{"iterations": 1, "steps": [
        {"purpose": "work", "goal": {"type": "distance", "unit": "meters", "value": 8000}}]}]}
    s = session_from_composition(comp, TODAY, "easy 8k", easy_speed=3.0)
    assert s.distance_m == 8000 and not s.hard and not s.estimated


def test_time_goal_uses_easy_speed_and_flags_estimate():
    comp = {"warmup": {"purpose": "warmup", "goal": {"type": "time", "unit": "seconds", "value": 600}}}
    s = session_from_composition(comp, TODAY, "40min easy", easy_speed=3.0)
    assert s.distance_m == 600 * 3.0 and s.estimated


def test_interval_structure_is_hard():
    # "rest" is the legacy purpose term, "recovery" the current schema's — both count
    for rest_term in ("rest", "recovery"):
        comp = {"blocks": [{"iterations": 6, "steps": [
            {"purpose": "work", "goal": {"type": "time", "unit": "seconds", "value": 60}},
            {"purpose": rest_term, "goal": {"type": "time", "unit": "seconds", "value": 120}},
        ]}]}
        s = session_from_composition(comp, TODAY, "6x1min", easy_speed=3.0)
        assert s.hard
        assert s.duration_s == 6 * 180


def test_fast_pace_alert_is_hard():
    comp = {"blocks": [{"iterations": 1, "steps": [
        {"purpose": "work",
         "goal": {"type": "distance", "unit": "meters", "value": 6000},
         "alert": {"type": "speed", "min": 3.5, "max": 3.8}}]}]}
    s = session_from_composition(comp, TODAY, "tempo", easy_speed=3.0)
    assert s.hard and not s.estimated


def test_missing_composition():
    s = session_from_composition(None, TODAY, "mystery", easy_speed=3.0)
    assert not s.has_data and s.distance_m == 0


def test_estimate_easy_speed_median():
    hist = history_weeks([30, 30])
    assert estimate_easy_speed(hist) == 3.0
    assert estimate_easy_speed([]) is None


# ── metadata extraction ──


def test_extract_race_date_variants():
    assert extract_race_date({"goals": {"raceDate": "2026-10-04"}}) == date(2026, 10, 4)
    assert extract_race_date({"race_date": "2026-10-04T09:00:00Z"}) == date(2026, 10, 4)
    assert extract_race_date({"goals": "sub-50 10k"}) is None
    assert extract_race_date(None) is None


def test_extract_guardrails_variants():
    rails = extract_guardrails({"guardrails": {"maxSessionsPerWeek": 4, "max_weekly_km": 50}})
    assert rails == {"max_sessions_per_week": 4, "max_weekly_km": 50}
    assert extract_guardrails({"guardrails": "be sensible"}) == {}


# ── ramp rate ──


def test_ramp_within_band_is_clean():
    warnings, weeks = validate_schedule(
        week_of_runs(NEXT_MONDAY, [10, 12, 14]),  # 36 km vs 30 baseline = 1.2x
        history_weeks([30, 30, 30, 30]),
        today=TODAY,
    )
    assert "ramp_rate" not in codes(warnings)
    assert weeks[0]["baseline_km"] == 30.0 and weeks[0]["ratio"] == 1.2


def test_ramp_warn_and_critical():
    warnings, _ = validate_schedule(
        week_of_runs(NEXT_MONDAY, [13, 14, 14]),  # 41 km = 1.37x
        history_weeks([30, 30, 30, 30]),
        today=TODAY,
    )
    assert "ramp_rate" in codes(warnings, "warn")

    warnings, _ = validate_schedule(
        week_of_runs(NEXT_MONDAY, [16, 17, 17]),  # 50 km = 1.67x
        history_weeks([30, 30, 30, 30]),
        today=TODAY,
    )
    assert "ramp_rate" in codes(warnings, "critical")


def test_volume_without_history_baseline():
    warnings, _ = validate_schedule(
        week_of_runs(NEXT_MONDAY, [15, 15, 15]), [], today=TODAY)
    assert "volume_without_baseline" in codes(warnings, "critical")  # 45 km, no history

    warnings, _ = validate_schedule(
        week_of_runs(NEXT_MONDAY, [5, 5, 5]), [], today=TODAY)
    assert codes(warnings) == []  # small beginner week, nothing to flag


# ── down weeks, long run, spacing, rest days ──


def test_missing_down_week():
    planned = []
    for i, km in enumerate([40, 44, 48, 52, 56, 60]):
        planned += week_of_runs(NEXT_MONDAY + timedelta(weeks=i), [km / 4] * 4)
    warnings, _ = validate_schedule(planned, history_weeks([38, 38, 38, 38]), today=TODAY)
    assert "missing_down_week" in codes(warnings)


def test_down_week_resets_streak():
    planned = []
    for i, km in enumerate([40, 44, 48, 30, 50, 54]):
        planned += week_of_runs(NEXT_MONDAY + timedelta(weeks=i), [km / 4] * 4)
    warnings, _ = validate_schedule(planned, history_weeks([38, 38, 38, 38]), today=TODAY)
    assert "missing_down_week" not in codes(warnings)


def test_long_run_share():
    warnings, weeks = validate_schedule(
        week_of_runs(NEXT_MONDAY, [10, 12, 18]),  # 18 of 40 km = 45%
        history_weeks([36, 36, 36, 36]),
        today=TODAY,
    )
    assert "long_run_share" in codes(warnings, "warn")
    assert weeks[0]["longest_km"] == 18.0


def test_hard_day_spacing_warn_and_critical():
    planned = week_of_runs(NEXT_MONDAY, [8, 8, 8])
    planned[0].hard = True
    planned.append(PlannedSession(date=NEXT_MONDAY + timedelta(days=1), title="tempo",
                                  distance_m=8000, duration_s=2400, hard=True))
    warnings, _ = validate_schedule(planned, history_weeks([30, 30, 30, 30]), today=TODAY)
    assert "hard_day_spacing" in codes(warnings, "warn")

    planned.append(PlannedSession(date=NEXT_MONDAY + timedelta(days=2), title="more",
                                  distance_m=8000, duration_s=2400, hard=True))
    warnings, _ = validate_schedule(planned, history_weeks([30, 30, 30, 30]), today=TODAY)
    assert "hard_day_spacing" in codes(warnings, "critical")


def test_no_rest_day():
    planned = [PlannedSession(date=NEXT_MONDAY + timedelta(days=i), title=f"d{i}",
                              distance_m=5000, duration_s=1500) for i in range(7)]
    warnings, _ = validate_schedule(planned, history_weeks([30, 30, 30, 30]), today=TODAY)
    assert "no_rest_day" in codes(warnings)


# ── guardrails, taper, strength, sanity ──


def test_guardrail_breaches_are_critical():
    planned = [PlannedSession(date=NEXT_MONDAY + timedelta(days=i), title=f"d{i}",
                              distance_m=9000, duration_s=2700) for i in range(5)]
    warnings, _ = validate_schedule(
        planned, history_weeks([40, 40, 40, 40]), today=TODAY,
        guardrails={"max_sessions_per_week": 4, "max_weekly_km": 40},
    )
    breaches = [w for w in warnings if w["code"] == "guardrail_breach"]
    assert len(breaches) == 2 and all(w["severity"] == "critical" for w in breaches)


def test_taper_checks():
    race = NEXT_MONDAY + timedelta(weeks=4, days=5)  # Saturday of week 5
    planned = []
    for i, km in enumerate([50, 55, 60, 58]):  # final full week ≈ peak → no taper
        planned += week_of_runs(NEXT_MONDAY + timedelta(weeks=i), [km / 4] * 4)
    planned.append(PlannedSession(date=race - timedelta(days=1), title="strides... hard",
                                  distance_m=5000, duration_s=1500, hard=True))
    warnings, _ = validate_schedule(
        planned, history_weeks([48, 48, 48, 48]), today=TODAY, race_date=race)
    assert "no_taper" in codes(warnings)
    assert "hard_near_race" in codes(warnings)


def test_strength_collision():
    planned = week_of_runs(NEXT_MONDAY, [8, 8, 8], hard_days=[1])
    hard_date = planned[1].date
    warnings, _ = validate_schedule(
        planned, history_weeks([30, 30, 30, 30]), today=TODAY,
        strength_dates={hard_date - timedelta(days=1)},
    )
    assert "strength_collision" in codes(warnings, "info")


def test_sanity_double_and_past():
    planned = [
        PlannedSession(date=NEXT_MONDAY, title="am", distance_m=5000, duration_s=1500),
        PlannedSession(date=NEXT_MONDAY, title="pm", distance_m=5000, duration_s=1500),
        PlannedSession(date=TODAY - timedelta(days=3), title="stale", distance_m=5000, duration_s=1500),
    ]
    warnings, _ = validate_schedule(planned, history_weeks([30, 30, 30, 30]), today=TODAY)
    assert "double_day" in codes(warnings, "info")
    assert "past_scheduled" in codes(warnings, "info")


def test_warnings_sorted_by_severity():
    planned = week_of_runs(NEXT_MONDAY, [20, 20, 20])  # 60 km, no history
    planned.append(PlannedSession(date=TODAY - timedelta(days=1), title="stale",
                                  distance_m=1000, duration_s=300))
    warnings, _ = validate_schedule(planned, [], today=TODAY)
    severities = [w["severity"] for w in warnings]
    assert severities == sorted(severities, key=("critical", "warn", "info").index)


# ── route integration ──


def _iso(d: date) -> str:
    return datetime.combine(d, time(7, 0), tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _run_payload(km: float, on: date, plan_id=None, title="easy run"):
    return {
        "activityType": "running",
        "title": title,
        "planId": plan_id,
        "workoutData": {
            "scheduledDate": _iso(on),
            "activityType": "running",
            "blocks": [{"iterations": 1, "steps": [
                {"purpose": "work", "goal": {"type": "distance", "unit": "meters", "value": km * 1000}}]}],
        },
    }


def test_batch_create_returns_validation_envelope(client_a):
    plan = client_a.post("/api/plans", json={
        "name": "10k block", "activityType": "running",
        "startDate": date.today().isoformat(),
        "metadata": {"guardrails": {"max_weekly_km": 30}},
    }).json()

    monday = date.today() + timedelta(days=7 - date.today().weekday())
    r = client_a.post("/api/queue/batch", json=[
        _run_payload(15, monday, plan["id"]),
        _run_payload(15, monday + timedelta(days=2), plan["id"]),
        _run_payload(15, monday + timedelta(days=4), plan["id"]),
    ])
    assert r.status_code == 201
    body = r.json()
    assert len(body["items"]) == 3
    assert "guardrail_breach" in [w["code"] for w in body["validation"]]  # 45 > 30 cap
    # 45 km with no recorded history also trips the absolute check
    assert "volume_without_baseline" in [w["code"] for w in body["validation"]]


def test_single_create_keeps_item_shape_plus_validation(client_a):
    r = client_a.post("/api/queue", json=_run_payload(5, date.today() + timedelta(days=3)))
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "easy run" and body["status"] == "pending"  # item shape intact
    assert isinstance(body["validation"], list)


def test_validate_endpoint_returns_weeks(client_a):
    plan = client_a.post("/api/plans", json={
        "name": "block", "activityType": "running",
        "startDate": date.today().isoformat(),
        "metadata": {"goals": {"race_date": (date.today() + timedelta(weeks=2)).isoformat()}},
    }).json()
    monday = date.today() + timedelta(days=7 - date.today().weekday())
    client_a.post("/api/queue/batch", json=[
        _run_payload(8, monday, plan["id"]),
        _run_payload(10, monday + timedelta(days=3), plan["id"], title="long run"),
    ])

    r = client_a.post(f"/api/plans/{plan['id']}/validate")
    assert r.status_code == 200
    body = r.json()
    assert body["plan_id"] == plan["id"]
    assert body["weeks"] and body["weeks"][0]["planned_km"] == 18.0


def test_validate_is_tenant_scoped(client_a, client_b):
    plan = client_a.post("/api/plans", json={
        "name": "mine", "activityType": "running",
        "startDate": date.today().isoformat(),
    }).json()
    assert client_b.post(f"/api/plans/{plan['id']}/validate").status_code == 404
