from fastapi import APIRouter
from sqlalchemy import text

from app.database import DbSession

router = APIRouter()


@router.get("/health")
def health(db: DbSession):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return {
        "service": "training-api",
        "version": "0.1.0",
        "database": db_status,
    }
