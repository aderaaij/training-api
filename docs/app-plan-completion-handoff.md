# iOS App Handoff — Plan Completion (celebrate, feedback, next-block nudge)

**Audience:** whoever updates the iOS app (running app) to add the plan wrap-up flow.
**Server status:** deployed and live on the Training API (`:8001`, Tailscale Funnel `https://ardencore.tail38e03e.ts.net:8443`). No further backend work required.
**TL;DR for the app:** when a plan's server-computed **`finishable`** flag turns true, show a **celebration screen** (stats + optional 1–5 rating + optional free-text feedback). Submitting calls **`POST /api/plans/{id}/complete`**. The response tells you whether another plan of the same activity is already active: if yes, show "**Next up: {name}**"; if no, nudge "**no {activity} plan lined up — talk to your coach to shape the next block**". The feedback text is automatically stored as a plan note the coach LLM reads at the start of its next conversation — the app never has to deliver it anywhere.

> The web dashboard already implements this exact flow (banner + modal). Use it as the visual/copy reference: `frontend/src/components/PlanCelebration.tsx`. Completing from either surface is equivalent — same endpoint.

---

## 1. Concepts

- **Plans never auto-complete.** The server computes a `finishable` signal; a human confirms. Until someone confirms, the plan stays `active` and the flag stays true on every read.
- **`finishable`** = plan is `active` **and** has started **and** (its `end_date` is in the past **or** every queued run is retired — `completed`/`skipped` — with **at least one actually completed**; a fully-skipped plan never celebrates).
- **`progress`** = run counts derived from the Apple Watch queue (`runs_total / runs_completed / runs_skipped / runs_remaining`). Strength plans schedule via `metadata.schedule`, not the queue, so their progress is all zeros and they become finishable via `end_date` only.
- **Feedback loop:** `feedback`/`rating` land in `plan.metadata.completion` *and* as a **`kind:"feedback"` plan note** attached to the plan. The coach LLM sees that note via `get_plan_context`, so the next "plan my next block" conversation already knows how this one went.

---

## 2. Detecting a finishable plan

**`GET /api/plans?status=active`** — the existing endpoint; `PlanRead` now carries two new fields (⚠️ **snake_case**, like all plan reads):

```jsonc
{
  "id": "61f97830-…",
  "name": "Return to Run",
  "activity_type": "running",
  "status": "active",
  "start_date": "2026-06-20",
  "end_date": "2026-07-16",
  "description": "…",
  "metadata": { /* … */ },
  "created_at": "…", "updated_at": "…",
  "progress": {                       // NEW — queue-derived run counts
    "runs_total": 12,
    "runs_completed": 11,
    "runs_skipped": 1,
    "runs_remaining": 0
  },
  "finishable": true                  // NEW — offer the wrap-up flow
}
```

**When to check:** the natural trigger is right after the app syncs a workout that completes a queue item (the final run of a plan) — that's the moment a same-day celebration feels earned. Also check on app foreground/plan-screen load; `finishable` is recomputed on every read, so a plan whose window quietly lapsed (e.g. a strength block) gets picked up too.

---

## 3. Completing the plan

**`POST /api/plans/{id}/complete`**

```jsonc
// request — both fields optional; {} is valid
{
  "feedback": "Loved the progression, long runs felt hard.",  // string | null
  "rating": 4                                                  // int 1–5 | null (422 outside range)
}
```

```jsonc
// response 200
{
  "plan": { /* PlanRead as §2 — status now "completed", finishable false,
               metadata.completion = {"completed_on":"2026-07-16","rating":4,"feedback":"…"} */ },
  "next_plan": { /* PlanRead of another ALREADY-ACTIVE plan of the same
                    activity_type (soonest start first), or null */ }
}
```

Side effects on the server:
1. `status` → `"completed"` (one-way; a second call returns **400**).
2. `metadata.completion` stamped (`completed_on` always; `rating`/`feedback` only if provided).
3. If `feedback` or `rating` was given: a `kind:"feedback"` plan note is created (summary `Plan wrap-up: {name} — rated N/5`, body = feedback text) — this is what the coach reads.

Errors: **400** plan isn't `active` (someone completed it via the dashboard/coach first — refresh your plan list and drop the celebration), **404** not your plan, **422** bad rating.

---

## 4. Success-state logic (the nudge)

Branch on `next_plan` in the response:

- **`next_plan != null`** → same activity is already covered. Show "**Next up: {next_plan.name}**, starts {next_plan.start_date}". No action needed from the user.
- **`next_plan == null`** → nothing lined up. Show the nudge: "**No {activity} plan lined up yet — start a conversation with your coach to shape the next block.**" If they gave feedback, reassure them it's already saved for the coach.

`next_plan` counts only plans with `status == "active"` whose `end_date` hasn't passed — a future `start_date` is fine (the coach creates follow-up blocks as `active` before they start, e.g. "Return to Run Phase 2").

---

## 5. Auth & base URL

- Base: `https://ardencore.tail38e03e.ts.net:8443` (same as today).
- Header: `Authorization: Bearer <API_KEY>` (same key the app already uses).

---

## 6. Suggested Swift models (Codable)

```swift
struct PlanProgress: Codable {
    let runsTotal, runsCompleted, runsSkipped, runsRemaining: Int
    enum CodingKeys: String, CodingKey {
        case runsTotal = "runs_total", runsCompleted = "runs_completed"
        case runsSkipped = "runs_skipped", runsRemaining = "runs_remaining"
    }
}

// additions to the existing snake_case Plan model:
//   let progress: PlanProgress?
//   let finishable: Bool

struct PlanCompleteRequest: Codable {
    let feedback: String?
    let rating: Int?          // 1...5
}

struct PlanCompleteResponse: Codable {
    let plan: Plan
    let nextPlan: Plan?
    enum CodingKeys: String, CodingKey { case plan, nextPlan = "next_plan" }
}
```

---

## 7. Behavior / UI recommendations

1. **Make it a moment.** Full-screen celebration (confetti/haptics), plan name, stats: `runs_completed` sessions (+ `runs_skipped` skipped if > 0) and week count (derive from `start_date`–`end_date`). The dashboard shows: trophy, "Plan complete!", stats row, star rating, one textarea.
2. **Rating + feedback are optional** — a bare `{}` complete is valid. Don't gate the button on either.
3. **Offer "Not now".** Dismissal is free: the flag is server-computed, so the celebration re-offers on the next check until the plan is actually completed. No local snooze state needed (add one if re-prompting feels naggy).
4. **Feedback placeholder should say who reads it** — e.g. "What worked, what didn't? Your coach reads this when shaping the next block." That's the honest contract and it prompts better answers.
5. **Window-passed plans** (`end_date` in the past, runs left over) get the same flow — frame it as "wrap up" rather than "perfect score"; show completed count, not remaining.
6. **After completing**, refresh the plans list (and calendar if shown) — the plan drops out of `status=active` everywhere.

---

## 8. Edge cases / gotchas

- **Casing:** plan reads are **snake_case** (`activity_type`, `next_plan`, `runs_total`…). The complete request keys (`feedback`, `rating`) are single words — no trap.
- **Strength plans:** `progress` is all zeros (their sessions are Hevy workouts, not queue items) and they become finishable only once `end_date` passes. Completed-session counts for them would need schedule-vs-workout matching server-side — not built; ask if the app wants it.
- **Open-ended plans** (`end_date: null`) become finishable only via the all-runs-done path.
- **Race with other surfaces:** the dashboard (and the coach via MCP `update_plan`) can also complete a plan. Handle the 400 by refreshing, not erroring.
- **`GET /api/plans/{id}` also carries `progress`/`finishable`** — handy for a plan-detail screen; `POST/PATCH` responses don't (defaults `null`/`false`), so don't read the flag off a create/update response.
- **Don't derive `finishable` client-side** from progress/dates — the rule lives server-side and may get smarter; trust the flag.

---

## 9. Open questions for the app dev / Arden

1. **Discovery UX:** banner/badge on the plan screen (dashboard's approach), or auto-present the celebration right after the final run's workout summary? Auto-present feels great same-day but needs the "sync completed the last queue item" trigger.
2. **Local notification?** If the app checks plans on a background refresh, a "🎉 You finished {plan}" notification is possible app-side. Server push doesn't exist (and isn't planned).
3. Should the **watch** get any of this, or iPhone-only? (Recommendation: iPhone-only.)

---

## 10. Quick manual test (server side)

```bash
K=<API_KEY>; BASE=https://ardencore.tail38e03e.ts.net:8443
# throwaway plan that ended yesterday + one completed run
PID=$(curl -s -X POST "$BASE/api/plans" -H "Authorization: Bearer $K" -H 'Content-Type: application/json' \
  -d '{"name":"tmp-finish","activityType":"running","startDate":"2026-06-01","endDate":"2026-07-15"}' | jq -r .id)
QID=$(curl -s -X POST "$BASE/api/queue" -H "Authorization: Bearer $K" -H 'Content-Type: application/json' \
  -d "{\"activityType\":\"running\",\"title\":\"tmp run\",\"planId\":\"$PID\",\"scheduledDate\":\"2026-07-10T08:00:00+00:00\"}" | jq -r .id)
curl -s -X PATCH "$BASE/api/queue/$QID/status" -H "Authorization: Bearer $K" -H 'Content-Type: application/json' -d '{"status":"completed"}' > /dev/null
curl -s "$BASE/api/plans/$PID" -H "Authorization: Bearer $K" | jq '{finishable, progress}'      # → finishable: true
curl -s -X POST "$BASE/api/plans/$PID/complete" -H "Authorization: Bearer $K" -H 'Content-Type: application/json' \
  -d '{"feedback":"test","rating":5}' | jq '{status:.plan.status, next_plan:.next_plan}'
# cleanup — ⚠ deleting a plan SET-NULLs its queue items, so delete the run too:
curl -s -X DELETE "$BASE/api/queue/$QID" -H "Authorization: Bearer $K"
curl -s -X DELETE "$BASE/api/plans/$PID" -H "Authorization: Bearer $K"
```
