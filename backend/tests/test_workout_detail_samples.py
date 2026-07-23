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


class TestStripEventsAndRounding:
    """The stripped view also prunes redundant HealthKit events and rounds
    float noise — activities carry mis-scoped copies of the top-level events,
    and segment events duplicate what activities/splits already encode."""

    def test_activity_event_copies_dropped(self):
        data = {
            "activities": [
                {
                    "events": [{"type": "segment", "startDate": "a", "endDate": "b", "metadata": {}}],
                    "duration": 180.00056099891663,
                    "metadata": {"WOIntervalStepKeyPath": "0.0.0"},
                },
                "junk",
            ]
        }
        out = strip_samples(data)
        assert "events" not in out["activities"][0]
        assert out["activities"][0]["metadata"] == {"WOIntervalStepKeyPath": "0.0.0"}
        assert out["activities"][1] == "junk"

    def test_segment_events_pruned_pause_resume_kept(self):
        data = {
            "events": [
                {"type": "segment", "startDate": "a", "endDate": "b", "metadata": {}},
                {"type": "pause", "startDate": "c", "endDate": "c"},
                {"type": "segment", "startDate": "d", "endDate": "e", "metadata": {}},
                {"type": "resume", "startDate": "f", "endDate": "f"},
            ]
        }
        assert [e["type"] for e in strip_samples(data)["events"]] == ["pause", "resume"]

    def test_empty_event_metadata_dropped(self):
        out = strip_samples({"events": [{"type": "pause", "metadata": {}, "startDate": "c"}]})
        assert out["events"] == [{"type": "pause", "startDate": "c"}]

    def test_floats_rounded_throughout(self):
        data = {
            "splits": [{"distance": 1000.2151937251687, "index": 1}],
            "activities": [{"totalDistance": 431.8716320564927}],
        }
        out = strip_samples(data)
        assert out["splits"][0] == {"distance": 1000.22, "index": 1}
        assert out["activities"][0] == {"totalDistance": 431.87}

    def test_whole_number_int_promoted_among_float_siblings(self):
        # Swift's JSONEncoder writes a whole-number double without the
        # fraction, so an exactly-60 s step arrives as int 60 while its
        # siblings round to 60.0 — the field must keep one JSON type.
        data = {"activities": [{"duration": 59.999801993370056}, {"duration": 60}]}
        durations = [a["duration"] for a in strip_samples(data)["activities"]]
        assert durations == [60.0, 60.0]
        assert all(type(d) is float for d in durations)

    def test_consistently_int_fields_stay_int(self):
        data = {"splits": [{"index": 1, "distance": 1000}, {"index": 2, "distance": 1000}]}
        out = strip_samples(data)
        assert out["splits"] == data["splits"]
        assert all(type(s["index"]) is int and type(s["distance"]) is int for s in out["splits"])

    def test_input_not_mutated_by_pruning(self):
        data = {"activities": [{"events": [1], "duration": 1.005}], "events": [{"type": "segment"}]}
        strip_samples(data)
        assert data == {"activities": [{"events": [1], "duration": 1.005}], "events": [{"type": "segment"}]}


def _create_workout(client) -> str:
    workout_id = str(uuid.uuid4())
    payload = {
        "id": workout_id,
        "activityType": "running",
        "startDate": "2026-07-23T06:00:00Z",
        "endDate": "2026-07-23T06:45:00Z",
        "duration": 2656.854385972023,
        "totalDistance": 6435.324887804791,
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
        # The root float columns are rounded along with the blob.
        assert body["duration"] == 2656.85
        assert body["total_distance"] == 6435.32

        # The compact read must not have persisted anything: a default read
        # afterwards still returns the full arrays and full precision.
        again = client_a.get(f"/api/workouts/{workout_id}").json()
        assert len(again["data"]["route"]) == 3
        assert "samplesSummary" not in again["data"]
        assert again["total_distance"] == 6435.324887804791
