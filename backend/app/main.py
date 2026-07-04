from fastapi import APIRouter, Depends, FastAPI

from fastapi.responses import RedirectResponse

from app.auth import verify_api_key
from app.routes import actions, dashboard, feedback, health, health_metrics, inventory, plan_notes, plans, queue, schedule, workouts

app = FastAPI(title="Training API", version="0.1.0")

# Dashboard — no auth (local network only)
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])


@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/dashboard")


# Health endpoint — no auth
app.include_router(health.router, prefix="/api", tags=["health"])

# Authenticated routes
api_router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])
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
