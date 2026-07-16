# Design Brief — Training Dashboard (React)

**For:** Claude Design
**Backend:** training-api (FastAPI, port 8001, `https://ardencore.tail38e03e.ts.net:8443`)
**Date:** 2026-07-16

## 1. Context & goal

training-api is a self-hosted personal training platform: an iOS app syncs Apple Watch / HealthKit workouts and daily health metrics in; an LLM (via MCP) acts as a training coach that builds plans, queues structured workouts to the watch, and keeps continuity notes between conversations.

The old server-rendered dashboard was **disabled for security** (it was unauthenticated and publicly reachable through Tailscale Funnel). This React app is its replacement: a **login-first, per-user dashboard**. The backend already has full multi-user support — username/password login, per-device revocable API tokens, and every table scoped by `user_id`.

**Deployment model matters for the design:** this is a self-hosted household instance (1–6 people, e.g. a family), not SaaS. No orgs, no billing, no open registration — an admin creates accounts.

Real data volume today (single user, ~18 months): 662 workouts across 10 activity types (running 417, flexibility 146, strength 76, walking 12, snowboarding 4, cycling 2, elliptical 2, rowing 1, mixedCardio 1, other 1), 111 days of health metrics, 3 plans, 36 queued watch workouts, 5 missed-workout feedback entries, 4 LLM plan notes. Design for these magnitudes: hundreds of workouts, dozens of notes — not millions of rows.

## 2. Roles: admin view vs user view

**Recommendation: one app with a role-gated admin section — not two separate apps.**

- Every user (including the admin) gets the same personal dashboard over *their own* data. The API enforces per-user scoping; there are no cross-user read endpoints, by design.
- `role: "admin"` unlocks one extra nav area: **User management** (create user, reset password, deactivate, see token counts). Admin work here is account administration, **not** looking at other people's training or health data — household privacy is a feature, and the backend doesn't offer cross-user data reads anyway.
- The login response includes `user.role`, so gating is trivial.

So: "admin view" = user view + a Users screen. Don't design admin dashboards full of other members' health charts — that data path doesn't (and shouldn't) exist.

## 3. Screen inventory

### Shared / user screens

**S1. Login**
`POST /api/auth/login` `{username, password, deviceName?}` → `{token, tokenId, user: {id, username, displayName, role}}`. Rate-limited 5/min; single indistinguishable error message for all failure modes ("Invalid username or password") — design for that one error state. No registration, no password reset link (admin resets passwords). Send a `deviceName` like "Web dashboard". Any 401 anywhere in the app → clear token, return here.

**S2. Overview / Today**
The landing screen. Suggested composition:
- Next up: upcoming sessions from `GET /api/schedule/calendar` (defaults to today → +28d), with conflict badges.
- Active plan snapshot: name, current phase, progress through `startDate → endDate`.
- Recent workouts (last 5–7) with effort scores.
- Latest health metrics tiles: sleep, resting HR, HRV, weight.
- Attention items: pending watch-queue items, unacknowledged missed-workout feedback.

**S3. Calendar / Schedule**
`GET /api/schedule/calendar?from=&to=` merges two session types onto one timeline: **runs** (from the watch queue, with status) and **strength sessions** (expanded from the active plan's weekly schedule, referencing Hevy routines by title). Each entry carries a `conflict: bool` flag when a run and strength session share a date — conflicts are *warned, never blocked* (deliberate product decision; render as a warning treatment, not an error). Month/week views; past dates should show what actually happened (completed queue items, matched strength workouts).

**S4. Workouts (list)**
`GET /api/workouts?activityType=&startAfter=&startBefore=&planWorkoutId=&limit=&offset=` (max 200/page, offset pagination). Filterable by activity type (10 types) and date range. Each row: activity type (iconography per type), date, duration, distance, energy, source app, effort score. Source matters to the user: workouts arrive from Apple Health/Watch, Strava, Hevy, Garmin, and Bend — show a source badge. `GET /api/workouts/summary` provides period aggregates (count, total/avg distance & duration, energy) for a stats header or trends strip.

**S5. Workout detail — "everything we have"**
The deep view. Data available per workout:
- Core: activity type, start/end, duration, total distance, energy burned, source, `effortScore` and `estimatedEffortScore` (both 1–10; actual vs LLM-estimated — show side by side when both exist), link to the plan/queue item that scheduled it (`planWorkoutId`).
- `data` JSONB — keys observed in real data: `splits`, `heartRate`, `route`, `cadence`, `events`, `activities`, `metadata`. Dedicated endpoints exist for the two big ones: `GET /api/workouts/{id}/splits` and `GET /api/workouts/{id}/heartrate`.
- Suggested layout: header stats → heart-rate trace over time (with zone bands) → splits table/bar chart (pace per km) → cadence chart → route map → raw metadata accordion at the bottom.
- **Route map caveat:** self-hosted app; map tiles are an external dependency. Either draw the GPS polyline standalone (no tiles) or use OSM tiles and accept the external fetch — flag the choice.
- **Strength workouts (Hevy) have no set/rep detail here** — they arrive via HealthKit as duration + HR + energy only. Exercise-level detail lives in Hevy. Design the strength detail view around HR/duration/effort, and don't promise sets/reps.
- Workouts are hard-deletable (`DELETE /api/workouts/{id}`) — destructive action, confirm.

**S6. Plans — current, historical, future**
`GET /api/plans?status=&activityType=` and `GET /api/plans/{id}`. Plan: name, activity type, status, startDate, endDate?, description, metadata JSONB, created/updated. Statuses in real data: `active`, `archived` (treat unknown statuses gracefully — it's a free string).
- **Current** = status `active` (there can be more than one — e.g. a running plan and a strength plan concurrently; today there are 2 active).
- **Historical** = `archived`/`completed` or endDate in the past.
- **Future** = startDate after today.
- Suggested: a plans timeline/list segmented into these three groups, plus a rich plan-detail page.

Plan detail renders `metadata`, whose real keys are: `goals`, `guardrails`, `phases`, `athlete_context`, `background`, `schedule`. These are LLM-authored structured content: render **phases** as a horizontal timeline with the current phase highlighted, **goals** as a checklist-style card, **guardrails** as warning-styled callouts, **athlete_context/background** as prose. **schedule** is the weekly strength cadence: `{startDate, weeks, days: {mon: {title, routineId}, ...}, time, timezone}` — render as a week grid. `GET /api/plans/{id}/schedule` returns it already expanded into concrete dated `sessions` with conflict flags and `warnings`. `GET /api/plans/{id}/workouts` lists the queue items generated from the plan. Keys inside metadata are open-ended — the renderer needs a graceful fallback for unknown keys (labelled JSON/definition-list display), since the LLM may add new ones.

**S7. Notes & LLM continuity — be precise about what this is**
What's stored is **not chat transcripts**. The LLM coach persists distilled **plan notes** (via the MCP tool `append_plan_note`), and reads them back at the start of each conversation. This screen is the full record of LLM "communication":
- Note anatomy: `kind` ∈ {`decision`, `preference`, `constraint`, `life_context`, `observation`, `blocker`}, `summary` (≤280 chars), optional long-form `body`, `importance` 1–3, optional `conversationId` (which chat it came from), optional `expiresAt` (notes can be temporary — e.g. "traveling until Aug 3"), optional link to a plan, timestamps.
- List/filter: `GET /api/plan-notes?planId=&kind=&conversationId=&sinceDays=&includeExpired=&limit=` — default sort is importance desc, then recency. Filters by kind, plan, expiry.
- **"What Claude sees" panel** — the standout feature of this screen: `GET /api/plan-notes/context` returns exactly the payload the LLM receives at conversation start: the resolved active plan + ranked non-expired notes + a `continuityHint` string ("Continuity is fresh…" / "Last note was N days ago…"). Render this as an inspectable "this is what your coach currently knows about you" view. It builds trust and makes stale/wrong notes visible.
- Users can edit and delete notes (`PATCH`/`DELETE /api/plan-notes/{id}`) — correcting the LLM's memory is a first-class action. Kind and importance are editable; expired notes should be visually distinct.
- Group/badge by kind with distinct colors; importance as a 1–3 weight indicator.

**S8. Health trends**
`GET /api/health/metrics?startDate=&endDate=` (startDate required) → one row per day: `sleepDuration` + `sleepStages` (JSONB), `restingHeartRate`, `hrvSdnn`, `weight`, `vo2Max`, `steps`, `activeEnergyBurned`, `bodyFatPercentage`, `leanBodyMass`, `respiratoryRate`, `spo2`. All nullable — sparse data is the norm (a metric may exist only some days). Time-series charts with range picker (30/90/365d); sleep stages as a stacked breakdown; recovery-oriented pairing (RHR + HRV together) is a natural grouping. 111 days exist today.

**S9. Watch queue & feedback**
- Queue: `GET /api/queue?status=&limit=&offset=` — structured workouts the LLM queued for the Apple Watch. Lifecycle: `pending` → `fetched`/`synced` → `completed`. Show title, activity, scheduled date, status, plan link; `workout_data` JSONB holds the structured intervals (renderable as a step list). Items are editable/deletable — but the primary author is the LLM; the dashboard is mostly for inspection and pruning.
- Missed-workout feedback: `GET /api/workouts/feedback` — when a scheduled workout was missed, the app records `reason`, optional `reasonNote`, `action` (e.g. rescheduled → `newDate`), `acknowledgedAt`, `dismissed`. Design as an inbox: unacknowledged items surface on the Overview.

**S10. Settings — profile, devices & tokens**
`GET /api/auth/me` → user + token list (`id`, `name`, `createdAt`, `lastUsedAt`, `expiresAt` — hashes never exposed). This is the security screen:
- Device/token list: name ("Arden's iPhone", "training-mcp", "Web dashboard"), created, last used, expiry (null = long-lived device token). Revoke = `DELETE /api/auth/tokens/{id}`. Revoking the *current* session's token (its id came back as `tokenId` at login) = logout.
- Logout button = revoke own token + clear local state.
- Change password — **backend endpoint does not exist yet** (see §5). Design it; mark it backend-pending.
- Create token (for hooking up a personal MCP without logging in on that device) — **backend-pending** (today: CLI or login only).

### Admin screens (role = admin)

**S11. User management**
List users (username, display name, role, active, created, token count/last-seen), create user (username + password + display name + role), reset password, deactivate/reactivate. **All of this is CLI-only today (`python -m app.cli create-user` etc.) — the HTTP endpoints are planned (multi-user plan, Phase 3.5) but not built.** Design the screens now; the API contract can mirror the CLI verbs (`POST /api/admin/users`, `POST /api/admin/users/{id}/password`, `PATCH /api/admin/users/{id}`). Deactivation kills all the user's sessions (their tokens stop authenticating) — say so in the confirm dialog. No self-service registration exists by design; user creation is this screen.

## 4. API contract essentials

- Auth: `Authorization: Bearer <token>` on every request. Tokens are opaque (`tapi_…`), long-lived, revocable. On 401: wipe local auth state, go to login.
- JSON is **camelCase** on the wire (requests and responses).
- List endpoints paginate with `limit` (max 200) + `offset`; no total counts are returned — design pagination as "load more"/infinite rather than numbered pages.
- `/api/health` is the only unauthenticated data endpoint (liveness). Everything else requires auth.
- IDs are UUIDs throughout.
- Errors: FastAPI-style `{detail: "..."}`; 404 is used for both "not found" and "not yours" (deliberate — don't design flows that distinguish them).

## 5. Known backend gaps (design anyway, flag as pending)

1. **Admin user-management HTTP endpoints** — CLI-only today (S11).
2. **Change-password endpoint** (S10).
3. **Create-token endpoint** for self-service token minting (S10) — today a token is only minted by login or CLI.
4. **CORS / hosting decision** — the API currently serves no SPA and sets no CORS headers. Either the React build gets served by the FastAPI container (same origin — recommended, keeps the Funnel setup unchanged) or CORS must be added. Assume same-origin.
5. **Auth storage** — the backend plan sketches an HttpOnly-cookie variant for browser use; not implemented. Assume bearer token held by the SPA for v1.

## 6. Design constraints & feel

- **Mobile-first responsive**: this is checked from a phone as often as a laptop. Calendar and workout detail must work at 390px.
- Personal, warm, data-dense but calm — a private training journal, not an enterprise analytics tool. Dark mode expected (it's a fitness app checked at 6am and 11pm).
- Chart-heavy: HR traces, pace splits, health trends, calendar. Consistent chart language across screens.
- Empty states matter: a fresh family-member account has zero workouts, zero plans, zero notes. Every screen needs a genuine empty state that explains how data arrives (install the iOS app and log in; the LLM coach creates plans).
- Trust and transparency are themes: the Notes screen ("what Claude knows"), token management, and visible source attribution on every workout all exist so the user can audit what the system stores and does.
