# Dashboard — remaining work (handoff)

Status 2026-07-16: the Loopback React dashboard (`frontend/`) is complete, deployed,
and served same-origin by FastAPI. **The account/token management batch (former
items 1–3) shipped on 2026-07-16** — see "Done" at the bottom for the shapes.
What remains is the polish list.

## 1. Polish / smaller items

- **HR zones are fixed bpm boundaries** (120/140/155/170 in
  `frontend/src/components/charts.tsx` + `WorkoutDetail.tsx`). Derive from a
  per-user max HR (settings field, backend-less via localStorage, or a proper
  user preference endpoint).
- **Coach teaser wording:** the Overview teaser prints `continuity_hint`
  verbatim, which is LLM-directed text ("…call append_plan_note…"). Fine for
  the Notes screen (that's the point), odd on the Overview — consider a
  user-facing paraphrase there.
- **Topbar search** existed in the design but was omitted (would have been
  non-functional). If wanted: client-side search over workouts/plans/notes.
- **Route map tiles** are an external fetch (CARTO dark). Offline alternative:
  draw the GPS polyline standalone (no tiles) when the tile fetch fails.
- **PWA manifest** (add-to-home-screen on iPhone) — the dashboard is
  mobile-first and checked from a phone; cheap win.
- **E2E test in-repo:** verification currently lives in throwaway scripts
  (headless chromium from `~/.cache/ms-playwright`, temp CLI user, seed via
  API, screenshot, delete rows). Worth turning into a checked-in Playwright
  test. Gotcha discovered: screenshot only after an explicit settle delay —
  `networkidle` can fire before the post-login query burst begins.

## 2. Ops notes (for context)

- Container runs **production mode**: `ENVIRONMENT: PRODUCTION` is pinned in
  `docker-compose.yml`'s `environment:` block (overrides the env_file, which
  is deliberately untouched).
- Deploys are manual: `docker compose up -d --build` (watchtower instances are
  scoped elsewhere and never rebuild local images).
- The frontend builds **inside** the Docker image (Node stage in
  `backend/Dockerfile`, build context = repo root). No dist/ is committed.
- Wire casing is inconsistent per resource — read the warning in CLAUDE.md
  before touching `frontend/src/lib/types.ts` or backend schemas.
- Backend tests run **inside the container**: `docker compose exec app python
  -m pytest` (`python -m` matters — bare `pytest` can't import `app`).

## Done 2026-07-17 — admin dashboard split + monitoring

The admin (role `admin`) manages accounts and isn't an athlete, so the athlete
screens were hidden and the admin surface grew four monitoring features.

1. **Admin/athlete route split** — `AthleteOnly` guard in `App.tsx` redirects the
   seven athlete routes (incl. `/`) to `/users` for admins; `Layout.tsx` swaps to an
   admin nav (Users + System), drops the queue bell/polling. Athlete UX unchanged.
2. **Per-user token management** (Users screen) — expandable token list per member,
   `GET /api/admin/users/{id}/tokens`, `DELETE …/{tid}` (revoke one stolen device
   without deactivating the whole account). 404 on cross-user token id.
3. **Sync freshness** (Users screen) — `AdminUserOut` gained `lastWorkoutSyncAt`
   (last workout row's `created_at`) + `lastHealthDate` (newest health day).
   Metadata only, never content; admins have none so no line shows.
4. **Auth audit trail + System screen** — `auth_events` table
   (`models/auth_event.py`) recorded via `app/auth_events.py` on login
   success/fail/rate-limit, password change/reset, token create/revoke, user
   create/deactivate/reactivate. `GET /api/admin/events` (prunes >365d on read).
   New **System** screen (`/system`): backup-freshness card, DB size/counts/migration
   head (`GET /api/admin/system`), and the activity feed.
5. **Nightly Postgres backup** (host, outside the repo) — `training-api-backup.timer`
   → `~/.local/bin/training-api-backup` `pg_dump | gzip` to
   `/mnt/synology_backups/training-api/` (keeps 30). The app container mounts that dir
   **read-only** at `/backups` (`BACKUP_DIR` env) so System can report freshness.
   The DB had zero backups before this. Documented in the root ArdenCore CLAUDE.md.

Tests: `backend/tests/test_auth_admin.py` gained coverage for token list/revoke +
guards, the events feed (actor vs target), and system-status shape. `system_status`
guards the `alembic_version` read with `inspect(...).has_table` because the test
schema is built by `create_all`, not migrations.

## Done 2026-07-16 — account/token management (former items 1–3)

All camelCase on the wire, like the rest of the auth router.

1. **Admin user management** (`backend/app/routes/admin.py`, admin-role guard
   via `CurrentAdmin` in `app/auth.py`; Users screen fully wired):
   - `GET /api/admin/users` → `[{id, username, displayName, role, isActive,
     tokenCount, lastSeenAt}]`
   - `POST /api/admin/users` `{username, password, displayName?, role?}` — 409
     on duplicate; username is normalized (strip/lowercase)
   - `POST /api/admin/users/{id}/password` `{password}` → 204
   - `PATCH /api/admin/users/{id}` `{isActive?}` — deactivation **deletes all
     the user's tokens** (devices stop immediately); self-deactivation → 400
2. **Change password** — `POST /api/auth/password` `{currentPassword,
   newPassword}` → `{revokedTokens}`. Wrong current password is **400, never
   401** (the SPA wipes its token on any 401). Changing the password revokes
   every *other* token; the requesting session survives.
3. **Self-service tokens** — `POST /api/auth/tokens` `{name, expiresAt?}` →
   `{token, tokenId}`, raw token shown once (copy-once dialog in Settings).
   `expiresAt` must be timezone-aware ISO; naive datetimes are 422.

New passwords everywhere require **min 8 characters** (the CLI still allows
anything non-empty). Tests: `backend/tests/test_auth_admin.py` (the login rate
limiter is reset per-test in `conftest.py` — TestClient shares one client IP).
