# Training API

Personal workout tracking API with Apple Watch integration queue, training plans, health metrics, and a web dashboard.

## Tech Stack

- **Backend:** FastAPI (Python 3.13) with Uvicorn
- **Database:** PostgreSQL 16 with SQLAlchemy 2.0 ORM, Alembic migrations
- **Package manager:** uv
- **MCP Server:** FastMCP 2.0 (in `mcp/`)
- **Infrastructure:** Docker Compose (`docker-compose.yml`)

## Project Structure

```
backend/
  app/
    main.py              # FastAPI app entry point
    auth.py              # Bearer token auth
    config.py            # Pydantic-settings
    database.py          # SQLAlchemy setup
    models/              # ORM models
    routes/              # API route handlers
    schemas/             # Pydantic request/response schemas
    templates/           # Jinja2 dashboard templates
    static/              # Dashboard assets
  migrations/            # Alembic migrations
  Dockerfile             # Multi-stage build with uv
mcp/
  app/
    main.py              # FastMCP server entry point
    config.py            # MCP settings
    tools/               # MCP tool routers (workouts, queue, actions, feedback, health, plans)
    services/            # HTTP client for backend API
```

## Development

```bash
make up                          # Start containers (postgres + app)
make down                        # Stop containers
make build                       # Rebuild images
make logs                        # Tail logs
make migrate                     # Run Alembic migrations
make create_migration m="desc"   # Create new migration
```

The API runs on port **8001**. Auth is via `Authorization: Bearer <API_KEY>` header. The `/health` and `/dashboard` endpoints are unauthenticated.

## Database

Models live in `backend/app/models/`. Key tables:
- **Workout** - recorded workouts with splits, heart rate, JSONB metadata
- **WorkoutQueue** - structured workouts queued for Apple Watch sync (status: pending/fetched/synced/completed)
- **Plan** - training plans with JSONB metadata (goals, guardrails, phases)
- **PlanNote** - cross-conversation continuity notes (decisions, preferences, life context). LLM reads via `get_plan_context`, writes via `append_plan_note`.
- **DailyHealthMetrics** - daily HealthKit data (sleep, HR, HRV, weight, VO2Max, etc.)
- **WorkoutAction** - edit/delete actions for on-device workouts
- **WorkoutFeedback** - missed workout feedback
- **WorkoutInventory** - current on-device workout snapshot

When adding/changing models, create a migration with `make create_migration m="description"`. Migrations auto-run on container startup.

## MCP Server

The MCP server (`mcp/`) exposes training data to Claude via FastMCP. It talks to the backend API over HTTP.

- Runs as a separate systemd service (`training-mcp`) on port **8590** via supergateway
- Config: `~/.config/systemd/user/training-mcp.service`
- Env: `mcp/config/.env` (needs `TRAINING_API_URL` and `TRAINING_API_KEY`)

## Deployment

Managed via Docker Compose. The backend container auto-runs migrations on startup.

```bash
docker compose up -d --build     # Deploy changes
docker compose logs -f backend   # Check logs
```

Exposed via Tailscale Funnel at `https://ardencore.tail38e03e.ts.net:8443` for iPhone app access.
