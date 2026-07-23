"""Compact views of the HealthKit-derived Workout.data blob.

A GPS run stores ~600 kB of raw route/cadence/heart-rate samples. Consumers
that reason about a workout rather than chart it (the MCP feeding an LLM)
request `include_samples=false` on the detail endpoint and get the output of
`strip_samples` instead: the arrays replaced by a small `samplesSummary`,
redundant event copies pruned, and float noise rounded away.
The dashboard keeps the default full payload for its route map and charts.
"""

# ≈ typical GPS verticalAccuracy; altitude moves smaller than this are jitter
# and would inflate a summed elevation gain several-fold over 2000 points.
_ELEVATION_HYSTERESIS_M = 2.0


def _numbers(values: list) -> list[float]:
    return [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]


def round_floats(value, ndigits: int = 2):
    """Recursively round floats in a JSON-shaped structure. HealthKit floats
    serialize at full double precision (distance: 1000.2151937251687); at
    metres/seconds/bpm scale, two decimals loses nothing."""
    if isinstance(value, float):
        return round(value, ndigits)
    if isinstance(value, list):
        return _uniform_number_types([round_floats(v, ndigits) for v in value])
    if isinstance(value, dict):
        return {k: round_floats(v, ndigits) for k, v in value.items()}
    return value


def _uniform_number_types(items: list) -> list:
    """Promote ints to floats under keys that hold a float in any sibling dict.
    Swift's JSONEncoder drops the fraction on whole-number doubles, so an
    exactly-60-second step arrives as 60 amid 60.0 siblings — one field, two
    JSON types once the floats are rounded."""
    float_keys = {
        k
        for item in items
        if isinstance(item, dict)
        for k, v in item.items()
        if isinstance(v, float)
    }
    if not float_keys:
        return items
    return [
        {k: float(v) if k in float_keys and type(v) is int else v for k, v in item.items()}
        if isinstance(item, dict)
        else item
        for item in items
    ]


def downsample_timed(samples: list, target: int) -> list:
    """Reduce a timed sample array ({timestamp, value}) to ~target entries by
    averaging `value` over evenly-sized buckets; each bucket keeps its middle
    sample's other fields (timestamp). Non-dict entries pass through by
    decimation. A three-hour run's HR series stays chart-shaped at any cap."""
    if target <= 0 or len(samples) <= target:
        return samples
    n = len(samples)
    out = []
    for i in range(target):
        bucket = samples[i * n // target : (i + 1) * n // target]
        mid = bucket[len(bucket) // 2]
        if isinstance(mid, dict):
            values = _numbers([s.get("value") for s in bucket if isinstance(s, dict)])
            entry = dict(mid)
            if values:
                entry["value"] = round(sum(values) / len(values), 1)
            out.append(entry)
        else:
            out.append(mid)
    return out


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
    """Return a copy of a workout data blob compacted for reasoning (LLM)
    consumers: the sample arrays removed with a `samplesSummary` key in their
    place (camelCase, matching the HealthKit-derived keys it sits alongside),
    redundant events pruned, and floats rounded to 2 decimals.

    Event pruning: HealthKit `segment` events carry no metadata, overlap each
    other, and duplicate the interval structure already properly encoded in
    `activities` (WOIntervalStepKeyPath) and `splits` — dropped. Pause/resume
    events are real information — kept. Each activity also carries an `events`
    array of copies of the top-level events matched by start date (often
    mis-scoped past the activity's end) — dropped wholesale."""
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

    activities = out.get("activities")
    if isinstance(activities, list):
        out["activities"] = [
            {k: v for k, v in a.items() if k != "events"} if isinstance(a, dict) else a
            for a in activities
        ]

    events = out.get("events")
    if isinstance(events, list):
        out["events"] = [
            {k: v for k, v in e.items() if not (k == "metadata" and not v)}
            if isinstance(e, dict)
            else e
            for e in events
            if not (isinstance(e, dict) and e.get("type") == "segment")
        ]

    return round_floats(out)
