from fastapi import APIRouter, Depends, FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.auth import get_current_user
from app.rate_limit import limiter
from app.routes import actions, auth, feedback, health, health_metrics, inventory, plan_notes, plans, queue, schedule, workouts

app = FastAPI(title="Training API", version="0.1.0")

# Rate limiting (used by /api/auth/login)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# The server-rendered dashboard is DISABLED. It was unauthenticated and served
# personal data (health metrics, workouts, plans) over the public Tailscale
# Funnel, and is being replaced by a separate authenticated frontend. The routes
# and templates remain in app/routes/dashboard.py + app/templates/ for reference
# — do NOT re-mount without auth, it would re-expose that data. See
# docs/multi-user-plan.md (Phase 3).


@app.get("/", include_in_schema=False)
def root():
    return {"service": "training-api", "status": "ok"}


# Health endpoint — no auth
app.include_router(health.router, prefix="/api", tags=["health"])

# Auth endpoints — login is public; me/revoke self-enforce via CurrentUser
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

# Authenticated routes
api_router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])
api_router.include_router(queue.workout_queue_router, prefix="/workouts/queue", tags=["queue"])
api_router.include_router(actions.router, prefix="/workouts/actions", tags=["actions"])
api_router.include_router(feedback.router, prefix="/workouts/feedback", tags=["feedback"])
api_router.include_router(inventory.router, prefix="/workouts/inventory", tags=["inventory"])
api_router.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
api_router.include_router(queue.router, prefix="/queue", tags=["queue"])
api_router.include_router(health_metrics.router, prefix="/health/metrics", tags=["health-metrics"])
api_router.include_router(plans.router, prefix="/plans", tags=["plans"])
api_router.include_router(plan_notes.router, prefix="/plan-notes", tags=["plan-notes"])
api_router.include_router(schedule.router, prefix="/schedule", tags=["schedule"])
app.include_router(api_router)
