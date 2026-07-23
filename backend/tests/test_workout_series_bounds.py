"""Bounded series reads: /summary date-range + limit, /heartrate downsampling,
/splits float rounding. The summary endpoint used to return every period back
to the first workout; the heartrate endpoint's length was bounded only by
workout duration."""

import uuid

from app.workout_summary import downsample_timed


def _post_workout(client, start: str, end: str, distance: float, hr: list | None = None, splits: list | None = None):
    payload = {
        "id": str(uuid.uuid4()),
        "activityType": "running",
        "startDate": start,
        "endDate": end,
        "duration": 1800.0,
        "totalDistance": distance,
    }
    if hr is not None:
        payload["heartRate"] = hr
    if splits is not None:
        payload["splits"] = splits
    resp = client.post("/api/workouts", json=payload)
    assert resp.status_code == 201
    return payload["id"]


class TestSummaryBounds:
    def _seed_three_months(self, client):
        _post_workout(client, "2026-05-05T06:00:00Z", "2026-05-05T06:30:00Z", 5000.123456789)
        _post_workout(client, "2026-06-05T06:00:00Z", "2026-06-05T06:30:00Z", 6000.0)
        _post_workout(client, "2026-07-05T06:00:00Z", "2026-07-05T06:30:00Z", 7000.0)

    def test_unbounded_by_default_newest_first(self, client_a):
        self._seed_three_months(client_a)
        rows = client_a.get("/api/workouts/summary", params={"period": "month"}).json()
        assert len(rows) == 3
        assert rows[0]["total_distance"] == 7000.0

    def test_limit_keeps_most_recent_rows(self, client_a):
        self._seed_three_months(client_a)
        rows = client_a.get("/api/workouts/summary", params={"period": "month", "limit": 2}).json()
        assert [r["total_distance"] for r in rows] == [7000.0, 6000.0]

    def test_date_range_filters(self, client_a):
        self._seed_three_months(client_a)
        rows = client_a.get(
            "/api/workouts/summary",
            params={"period": "month", "start_after": "2026-05-20T00:00:00Z", "start_before": "2026-06-20T00:00:00Z"},
        ).json()
        assert [r["total_distance"] for r in rows] == [6000.0]

    def test_aggregates_are_rounded(self, client_a):
        _post_workout(client_a, "2026-07-05T06:00:00Z", "2026-07-05T06:30:00Z", 5000.123456789)
        row = client_a.get("/api/workouts/summary", params={"period": "month"}).json()[0]
        assert row["total_distance"] == 5000.1
        assert row["avg_distance"] == 5000.1


class TestHeartrateDownsampling:
    def test_capped_series_bucket_averages(self, client_a):
        hr = [{"timestamp": f"2026-07-05T06:{i // 60:02d}:{i % 60:02d}Z", "value": 100 + i} for i in range(100)]
        wid = _post_workout(client_a, "2026-07-05T06:00:00Z", "2026-07-05T06:30:00Z", 5000, hr=hr)

        full = client_a.get(f"/api/workouts/{wid}/heartrate").json()
        assert len(full) == 100

        capped = client_a.get(f"/api/workouts/{wid}/heartrate", params={"max_samples": 20}).json()
        assert len(capped) == 20
        # Bucket 0 averages values 100..104 and keeps a real timestamp.
        assert capped[0]["value"] == 102.0
        assert capped[0]["timestamp"].startswith("2026-07-05T06:00")
        # Order and overall shape survive.
        assert [s["value"] for s in capped] == sorted(s["value"] for s in capped)

    def test_cap_above_length_is_a_noop(self, client_a):
        hr = [{"timestamp": "t", "value": 140}, {"timestamp": "t2", "value": 150}]
        wid = _post_workout(client_a, "2026-07-05T06:00:00Z", "2026-07-05T06:30:00Z", 5000, hr=hr)
        assert client_a.get(f"/api/workouts/{wid}/heartrate", params={"max_samples": 500}).json() == hr


class TestDownsampleTimedUnit:
    def test_non_dict_entries_pass_through_by_decimation(self):
        assert len(downsample_timed(list(range(10)), 3)) == 3

    def test_target_at_or_above_length_returns_input(self):
        samples = [{"value": 1}]
        assert downsample_timed(samples, 5) is samples


class TestSplitsRounding:
    def test_split_floats_rounded(self, client_a):
        splits = [{"distance": 1000.2151937251687, "duration": 393.09535348415375, "index": 1}]
        wid = _post_workout(client_a, "2026-07-05T06:00:00Z", "2026-07-05T06:30:00Z", 5000, splits=splits)
        assert client_a.get(f"/api/workouts/{wid}/splits").json() == [
            {"distance": 1000.22, "duration": 393.1, "index": 1}
        ]
