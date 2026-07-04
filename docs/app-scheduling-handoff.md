# iOS App Handoff — Workout Scheduling (runs + Hevy strength cycles)

**Audience:** whoever updates the iOS app (running app) to display the new schedule.
**Server status:** deployed and live on the Training API (`:8001`, Tailscale Funnel `https://ardencore.tail38e03e.ts.net:8443`). No further backend work required for the app to consume this.
**TL;DR for the app:** add a **combined agenda / calendar** that shows *runs* (as today) **plus** a new *strength* row type that just names a Hevy routine per day. Strength sessions are **display-only** — never send them to WorkoutKit / the watch.

---

## 1. Concepts

There are now **two kinds** of scheduled things:

| | **Run** (unchanged) | **Strength session** (new) |
|---|---|---|
| Source | `GET /api/workouts/queue` (Apple Watch queue) | A `Plan`'s recurring cadence (`plan.metadata.schedule`) |
| Goes to Apple Watch? | **Yes** (WorkoutKit composition) | **No** — plan marker only |
| Detail | Full interval composition | Just a **Hevy routine reference**: `title` + `routineId` |
| "Done" tracking | queue item status | auto-matched to an incoming `traditionalStrength` HealthKit workout on that date |

A **strength cycle** = a `Plan` with `activityType: "strength"`, a goal/description, an `endDate`, and a weekly cadence in `metadata.schedule` like *"Tue = Legs, Thu = Upper Push, for 6 weeks."* The cadence is created by the user talking to Claude (which pulls the real routine IDs from the Hevy MCP and writes them here). **The app does not need to talk to Hevy** — it only displays `title`/`routineId` that are already stored.

> **The app is primarily a consumer/display of the schedule.** Creation/editing lives with the LLM for v1 (it needs the Hevy routine list). Editing from the app is possible later (see §6) but not required.

---

## 2. The one endpoint that does everything: unified calendar

**`GET /api/schedule/calendar?from=YYYY-MM-DD&to=YYYY-MM-DD`**
Merges runs + strength into one date-sorted list, with conflict flags. Defaults: `from`=today, `to`=today+28d. This is the **recommended primary feed** for a combined "upcoming" view.

```jsonc
{
  "from": "2026-07-06",
  "to": "2026-07-12",
  "entries": [
    {
      "date": "2026-07-07",
      "kind": "run",                       // "run" | "strength"
      "title": "W3 · Easy 35 min",
      "activityType": "running",
      "status": "pending",                 // run only: pending/fetched/synced/completed
      "planId": "61f97830-…",
      "planName": null,                     // populated for strength; null for runs
      "routineId": null,                    // strength only: the Hevy routine id
      "completed": false,                   // run: status==completed; strength: a traditionalStrength workout exists that day
      "conflict": true                      // a run AND a strength session share this date
    },
    {
      "date": "2026-07-07",
      "kind": "strength",
      "title": "Legs",
      "activityType": "strength",
      "status": null,
      "planId": "2f950c04-…",
      "planName": "Strength Block",
      "routineId": "hevy-legs-uuid",
      "completed": false,
      "conflict": true
    }
    // …
  ]
}
```

- **All camelCase.** Entries are sorted by `(date, kind)`.
- `conflict: true` on *both* entries of a colliding day. Show a small ⚠ indicator; don't hide either — the user/LLM decides.
- Auth required (see §5).

---

## 3. Per-plan schedule (for a plan-detail screen)

**`GET /api/plans/{planId}/schedule`** → the plan's cadence expanded to concrete dates, with conflicts. Use this on a strength-plan detail page (the calendar in §2 is better for the combined agenda).

```jsonc
{
  "planId": "2f950c04-…",
  "schedule": {                            // null if the plan has no cadence
    "startDate": "2026-07-06",
    "weeks": 6,
    "days": {                              // weekday -> routine ref (keys: mon..sun)
      "tue": { "title": "Legs", "routineId": "hevy-legs-uuid" },
      "thu": { "title": "Upper Push", "routineId": "hevy-push-uuid" }
    },
    "time": "07:00",                       // optional default time of day
    "timezone": "Europe/Lisbon"            // optional
  },
  "sessions": [                            // fully expanded, sorted by date
    { "date": "2026-07-07", "weekday": "tue", "title": "Legs",
      "routineId": "hevy-legs-uuid", "conflict": true,
      "conflictsWith": ["W3 · Easy 35 min"] },
    { "date": "2026-07-21", "weekday": "tue", "title": "Legs",
      "routineId": "hevy-legs-uuid", "conflict": false, "conflictsWith": [] }
    // …
  ],
  "warnings": [
    "2026-07-07 'Legs' overlaps scheduled run(s): W3 · Easy 35 min"
  ]
}
```

---

## 4. Existing endpoints you'll still use (casing note!)

These are **unchanged** but relevant. ⚠️ **Casing differs from §2/§3** — plan/queue *reads* are **snake_case**; only the new scheduling endpoints and the workout composition are camelCase. Use explicit `CodingKeys`.

- **`GET /api/workouts/queue`** → array of run **compositions** (camelCase: `displayName`, `activityType`, `scheduledDate`, `blocks`, `warmup`, `cooldown`, `id`). Unchanged; still the source for pushing runs to the watch.
- **`GET /api/plans?status=active`** and **`GET /api/plans/{id}`** → `PlanRead`, **snake_case**: `activity_type`, `start_date`, `end_date`, `created_at`, `updated_at`, plus `metadata` (whose nested `schedule` is **camelCase** — same shape as §3's `schedule`). Use this for the "plan + goal + until-when" card. For strength cycles, `activity_type == "strength"` and `end_date` is the cycle end.

Example `GET /api/plans/{id}` (abridged):
```jsonc
{
  "id": "2f950c04-…", "name": "Strength Block", "activity_type": "strength",
  "status": "active", "start_date": "2026-07-06", "end_date": "2026-08-16",
  "description": "6-week push/pull/legs block",
  "metadata": { "schedule": { "startDate": "2026-07-06", "weeks": 6,
      "days": { "tue": {"title":"Legs","routineId":"hevy-legs-uuid"}, "thu": {…} },
      "time": "07:00", "timezone": "Europe/Lisbon" } },
  "created_at": "2026-07-03T13:06:25Z", "updated_at": "2026-07-03T13:06:25Z"
}
```

---

## 5. Auth & base URL

- Base: `https://ardencore.tail38e03e.ts.net:8443` (same as today).
- Header: `Authorization: Bearer <API_KEY>` (same key the app already uses). All `/api/*` require it; `/health` and `/dashboard` don't.

---

## 6. Suggested Swift models (Codable)

```swift
enum ScheduleKind: String, Codable { case run, strength }

struct CalendarEntry: Codable, Identifiable {
    var id: String { "\(date)-\(kind.rawValue)-\(title)" }
    let date: String            // "YYYY-MM-DD" (local calendar day; see §7)
    let kind: ScheduleKind
    let title: String
    let activityType: String?
    let status: String?         // runs: pending/fetched/synced/completed
    let planId: String?
    let planName: String?       // strength only
    let routineId: String?      // strength only — Hevy routine id
    let completed: Bool
    let conflict: Bool
}

struct CalendarResponse: Codable {
    let from: String
    let to: String
    let entries: [CalendarEntry]
}

// Cadence (as seen in plan.metadata.schedule and the schedule endpoint)
struct RoutineRef: Codable { let title: String; let routineId: String? }
struct PlanSchedule: Codable {
    let startDate: String
    let weeks: Int
    let days: [String: RoutineRef]   // "mon".."sun"
    let time: String?
    let timezone: String?
}
```
(Decode §2/§3 with default keys; decode `PlanRead` with snake_case `CodingKeys`.)

---

## 7. Behavior / UI recommendations

1. **Combined agenda:** drive an "upcoming" list/calendar from `GET /api/schedule/calendar`. Render `kind == run` as today's run cell; add a new **strength** cell that shows `title` (e.g. "Legs") + a Hevy glyph.
2. **Never** enqueue `kind == strength` to WorkoutKit / the watch. It's informational.
3. **Completed:** show a ✓ when `completed == true` (works for both kinds).
4. **Conflict:** show a subtle ⚠ when `conflict == true`. Optional: a settings note that the user can ask Claude to move one.
5. **Cycle horizon (solves the original pain):** on the plan card for a strength cycle, show `end_date` and a "**N days left / cycle ended — plan the next one**" chip. Compute from `end_date` (or the last `sessions[].date`). This is the cue to go back to Claude and build the next Hevy routine + cycle.
6. **Opening the routine in Hevy:** `routineId` is the Hevy API routine id. There is **no guaranteed public per-routine URL/deep-link** — treat "open in Hevy" as best-effort (a generic Hevy universal link / app launch) or just display the name. Flagging this as an open question, not a blocker. (See §9.)

---

## 8. Edge cases / gotchas

- **Timezone:** run `scheduled_date` is stored **UTC**; the calendar buckets runs by their **UTC** date. A run scheduled late-evening local could show on the next day, and same-day conflict detection is UTC-based. Fine for current use; can be made tz-aware server-side if it bites (say the word).
- **Multiple active plans:** you can have an active *running* plan and an active *strength* plan simultaneously. `GET /api/plans?status=active` returns both; the calendar already merges them.
- **Strength sessions are not queue items** — don't expect them in `/api/workouts/queue` or with a queue UUID. Their identity is `(planId, date)`.
- **Empty schedule:** a plan may have no `schedule` (then `metadata.schedule` is absent and the schedule endpoint returns `"schedule": null`).

---

## 9. Open questions for the app dev / Arden

1. **Should the app *edit* schedules, or display only for v1?** Editing needs the Hevy routine list; recommended v1 = display-only, creation via Claude. If you want app editing, the API supports it: `PUT /api/plans/{id}/schedule` with body `{startDate, weeks, days:{weekday:{title,routineId}}, time?, timezone?}` (weekday keys validated `mon..sun`; returns the same resolved shape as §3). You'd still need a routine picker fed with Hevy routine ids.
2. **Hevy deep-link:** is there a routine URL scheme you want to try, or just show the name?
3. **Combined vs separate views:** one merged agenda (recommended), or keep runs where they are and add a separate "Strength" tab?

---

## 10. Quick manual test (server side)

```bash
K=<API_KEY>; BASE=https://ardencore.tail38e03e.ts.net:8443
# see the merged calendar
curl -s "$BASE/api/schedule/calendar" -H "Authorization: Bearer $K" | jq
# create a throwaway strength cycle to eyeball the shapes
PID=$(curl -s -X POST "$BASE/api/plans" -H "Authorization: Bearer $K" -H 'Content-Type: application/json' \
  -d '{"name":"tmp","activityType":"strength","startDate":"2026-07-06","endDate":"2026-08-16"}' | jq -r .id)
curl -s -X PUT "$BASE/api/plans/$PID/schedule" -H "Authorization: Bearer $K" -H 'Content-Type: application/json' \
  -d '{"startDate":"2026-07-06","weeks":6,"days":{"tue":{"title":"Legs","routineId":"x"},"thu":{"title":"Push","routineId":"y"}}}' | jq
curl -s -X DELETE "$BASE/api/plans/$PID" -H "Authorization: Bearer $K"   # cleanup
```

The web dashboard's **Schedule** tab (`/dashboard/schedule`, no auth on LAN) shows the same merged calendar — useful as a visual reference for what the app should render.
