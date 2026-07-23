"""Compact summaries for the per-second sample arrays inside Workout.data.

A GPS run stores ~600 kB of raw route/cadence/heart-rate samples. Consumers
that reason about a workout rather than chart it (the MCP feeding an LLM)
request `include_samples=false` on the detail endpoint and get the output of
`strip_samples` instead: the arrays replaced by a small `samplesSummary`.
The dashboard keeps the default full payload for its route map and charts.
"""

# ≈ typical GPS verticalAccuracy; altitude moves smaller than this are jitter
# and would inflate a summed elevation gain several-fold over 2000 points.
_ELEVATION_HYSTERESIS_M = 2.0


def _numbers(values: list) -> list[float]:
    return [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]


def _stats(samples: list) -> dict:
    out: dict = {"count": len(samples)}
    values = _numbers([s.get("value") for s in samples if isinstance(s, dict)])
    if values:
        out["avg"] = round(sum(values) / len(values), 1)
        out["min"] = round(min(values), 1)
        out["max"] = round(max(values), 1)
    return out


def _route_summary(points: list) -> dict:
    out: dict = {"count": len(points)}
    altitudes = _numbers([p.get("altitude") for p in points if isinstance(p, dict)])
    if altitudes:
        gain = loss = 0.0
        reference = altitudes[0]
        for altitude in altitudes[1:]:
            delta = altitude - reference
            if delta >= _ELEVATION_HYSTERESIS_M:
                gain += delta
                reference = altitude
            elif delta <= -_ELEVATION_HYSTERESIS_M:
                loss -= delta
                reference = altitude
        out["elevationGainM"] = round(gain, 1)
        out["elevationLossM"] = round(loss, 1)
        out["altitudeMinM"] = round(min(altitudes), 1)
        out["altitudeMaxM"] = round(max(altitudes), 1)
    return out


def strip_samples(data: dict) -> dict:
    """Return a copy of a workout data blob with the sample arrays removed
    and a `samplesSummary` key in their place (camelCase, matching the
    HealthKit-derived keys it sits alongside). Data without sample arrays
    is returned unchanged, with no summary key."""
    out = dict(data)
    summary: dict = {}
    for key, name, summarize in (
        ("route", "route", _route_summary),
        ("cadence", "cadence", _stats),
        ("heartRate", "heartRate", _stats),
        ("heartRateSamples", "heartRate", _stats),  # legacy key, same content
    ):
        value = out.get(key)
        if isinstance(value, list):
            del out[key]
            if name not in summary:
                summary[name] = summarize(value)
    if summary:
        out["samplesSummary"] = summary
    return out
