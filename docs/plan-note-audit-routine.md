# Plan-Note Audit Routine — Concept

A weekly remote agent (Anthropic cloud, scheduled via `/schedule`) that
audits the `plan_note` table to keep continuity context healthy.

Status: **not yet created**. Decisions parked below.

## What it should do

1. **Auto-fix stale `life_context` notes.** Any `kind: "life_context"` note
   older than ~7 days that lacks `expires_at` and references temporal
   wording ("this week", "today", a date that has passed, "while I'm in
   X") → PATCH with a sensible `expires_at`.
2. **Flag likely duplicates.** Soft-match note summaries; surface pairs
   that look like the same fact stored twice (LLM judgment, no DB rule).
3. **Flag stale high-importance notes.** Any `importance: 3` note with
   `updated_at` > 30 days ago → surface for the user to confirm it's
   still load-bearing.
4. **Output a summary.** See "Reporting" below — currently undecided.

## Connectivity (remote agent → training-api)

The remote agent runs in Anthropic's cloud, **cannot** reach
`localhost:8001`. Two options:

| Option | How | Tradeoff |
|--------|-----|----------|
| Tailscale Funnel (existing) | `curl https://ardencore.tail38e03e.ts.net:8443/api/plan-notes ...` with `Authorization: Bearer <key>` | API key sits in the routine prompt config on Anthropic's side. Acceptable for a personal homelab key, but worth a deliberate decision. |
| MCP via mcp-auth-proxy + Cloudflare Tunnel | Set up `training-mcp.arden.nl` like the Todoist pattern (see `/home/arden/CLAUDE.md`) | Cleaner: no API key in prompt, OAuth-gated, agent uses MCP tools directly. More setup. |

Lean: **Funnel for v1**, migrate to MCP later if other routines need it too.

## Reporting (where the audit summary goes)

Open question. Three options considered:

- **Self-write a `plan_note`** (`kind: "observation"`, `importance: 1`,
  `expires_at: +14 days`). Next LLM conversation surfaces it via
  `get_plan_context`. Self-contained, no new surface. Slight risk: clutters
  notes if the audit is noisy.
- **Email via Gmail MCP** (already connected). Immediate, doesn't pollute
  notes. Risk: ignored inbox, no LLM-side signal.
- **Both** — email for immediacy, observation note for in-conversation
  surfacing. Likely overkill at v1.

Decision deferred — skipping reporting wiring on first build.

## Proposed config (when revived)

- **Schedule**: `0 18 * * 0` (Sunday 18:00 UTC, end of training week)
- **Model**: `claude-sonnet-4-6`
- **Sources**: none (pure API calls, no code to read)
- **MCP connections**: none for v1 (Gmail if reporting goes that route)
- **Environment**: Default

## Prompt sketch

The remote agent starts with zero context, so the prompt is the whole
brief. Rough shape:

```
You are auditing the plan_note table on Arden's training API.

API base:   https://ardencore.tail38e03e.ts.net:8443
Auth:       Authorization: Bearer <KEY>
Endpoints:  GET    /api/plan-notes (filters: kind, since_days, include_expired, limit)
            GET    /api/plan-notes/context
            PATCH  /api/plan-notes/{id}  (body: {expiresAt, summary, body, importance})

Tasks:
  1. Fetch all non-expired notes (GET /api/plan-notes?limit=200&include_expired=false).
  2. For every life_context note older than 7 days without expires_at:
       - Read summary + body for temporal cues (specific dates, "this week",
         "today", "while I'm in X").
       - If a sensible expiry can be inferred, PATCH the note to set expiresAt.
       - Otherwise leave it but include in the summary.
  3. Find note pairs whose summaries describe the same fact (semantic match,
     not string match). List them.
  4. List importance=3 notes whose updated_at > 30 days ago.
  5. [Reporting decision pending — TBD when revived.]

Be conservative on auto-PATCH: when in doubt, leave the note and report it.
```

## Open questions to resolve before creating

- [ ] Reporting surface (note / email / both / log-only)
- [ ] Funnel vs MCP path
- [ ] Should the audit also detect notes that contradict each other (a
      newer note overrides an older one) and propose archiving the old
      one?
- [ ] Add a `last_referenced_at` column to `plan_note` so "haven't been
      referenced lately" becomes a real signal instead of a `updated_at`
      proxy?
