"""include_samples=false on workout detail: raw sample arrays swapped for a
compact samplesSummary, default behavior byte-for-byte unchanged."""

import uuid

from app.workout_summary import strip_samples


def _route_point(altitude: float, second: int = 0) -> dict:
    return {
        "latitude": 38.72,
        "longitude": -9.12,
        "altitude": altitude,
        "speed": 2.5,
        "course": 120.0,
        "timestamp": f"2026-07-23T06:03:{second:02d}Z",
        "horizontalAccuracy": 5.0,
        "verticalAccuracy": 2.0,
    }


class TestStripSamples:
    def test_summarizes_and_removes_sample_arrays(self):
        data = {
            "route": [_route_point(a, i) for i, a in enumerate([10.0, 10.5, 13.0, 12.9, 9.0])],
            "cadence": [{"value": v, "timestamp": "t"} for v in [160.0, 170.0]],
            "heartRate": [{"value": v, "timestamp": "t"} for v in [140, 150, 160]],
            "splits": [{"distance": 1000}],
            "metadata": {"indoor": False},
        }
        out = strip_samples(data)

        assert "route" not in out and "cadence" not in out and "heartRate" not in out
        assert out["splits"] == [{"distance": 1000}]
        assert out["metadata"] == {"indoor": False}

        summary = out["samplesSummary"]
        # 10 → 13 is +3 (above the 2 m hysteresis), 13 → 9 is −4; the ±0.5
        # wiggles are jitter and must not count.
        assert summary["route"] == {
            "count": 5,
            "elevationGainM": 3.0,
            "elevationLossM": 4.0,
            "altitudeMinM": 9.0,
            "altitudeMaxM": 13.0,
        }
        assert summary["cadence"] == {"count": 2, "avg": 165.0, "min": 160.0, "max": 170.0}
        assert summary["heartRate"] == {"count": 3, "avg": 150.0, "min": 140, "max": 160}

    def test_data_without_samples_is_unchanged(self):
        data = {"splits": [{"distance": 1000}], "metadata": {"indoor": True}}
        assert strip_samples(data) == data

    def test_input_dict_is_not_mutated(self):
        data = {"heartRate": [{"value": 140}]}
        strip_samples(data)
        assert data == {"heartRate": [{"value": 140}]}

    def test_legacy_heart_rate_samples_key(self):
        data = {"heartRateSamples": [{"value": 100}], "heartRate": [{"value": 120}]}
        out = strip_samples(data)
        assert "heartRateSamples" not in out and "heartRate" not in out
        # Both arrays are removed but the canonical key wins the summary.
        assert out["samplesSummary"]["heartRate"]["avg"] == 120.0

    def test_non_list_sample_value_left_alone(self):
        data = {"route": "corrupt"}
        assert strip_samples(data) == {"route": "corrupt"}

    def test_samples_without_numeric_values_still_counted(self):
        out = strip_samples({"heartRate": [{"timestamp": "t"}, "junk"]})
        assert out["samplesSummary"]["heartRate"] == {"count": 2}


def _create_workout(client) -> str:
    workout_id = str(uuid.uuid4())
    payload = {
        "id": workout_id,
        "activityType": "running",
        "startDate": "2026-07-23T06:00:00Z",
        "endDate": "2026-07-23T06:45:00Z",
        "duration": 2700.0,
        "totalDistance": 6435.0,
        "route": [_route_point(a, i) for i, a in enumerate([70.0, 74.0, 71.0])],
        "cadence": [{"value": 165.0, "timestamp": "2026-07-23T06:01:00Z"}],
        "heartRate": [{"value": 145, "timestamp": "2026-07-23T06:01:00Z"}],
        "splits": [{"distance": 1000, "duration": 400}],
    }
    resp = client.post("/api/workouts", json=payload)
    assert resp.status_code == 201
    return workout_id


class TestWorkoutDetailIncludeSamples:
    def test_default_keeps_full_arrays(self, client_a):
        workout_id = _create_workout(client_a)
        data = client_a.get(f"/api/workouts/{workout_id}").json()["data"]
        assert len(data["route"]) == 3
        assert "samplesSummary" not in data

    def test_include_samples_false_summarizes(self, client_a):
        workout_id = _create_workout(client_a)
        body = client_a.get(f"/api/workouts/{workout_id}", params={"include_samples": False}).json()

        data = body["data"]
        assert "route" not in data and "cadence" not in data and "heartRate" not in data
        assert data["splits"] == [{"distance": 1000, "duration": 400}]
        assert data["samplesSummary"]["route"]["count"] == 3
        assert data["samplesSummary"]["route"]["elevationGainM"] == 4.0
        assert data["samplesSummary"]["heartRate"]["max"] == 145
        # Top-level fields are untouched by the flag.
        assert body["total_distance"] == 6435.0

        # The compact read must not have persisted anything: a default read
        # afterwards still returns the full arrays.
        data_again = client_a.get(f"/api/workouts/{workout_id}").json()["data"]
        assert len(data_again["route"]) == 3
        assert "samplesSummary" not in data_again
