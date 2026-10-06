from fastapi import APIRouter, Response
from sqlalchemy import text
from sqlmodel import Session

from app.core import database

router = APIRouter(tags=["meta"])


@router.get("/health")
def health(response: Response) -> dict[str, str]:
    """Readiness check that actually touches the database (unified R28-OPS-2):
    returns 503 when the DB is unreachable so Render and uptime monitors see it."""
    try:
        with Session(database.engine) as s:
            s.exec(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    if not db_ok:
        response.status_code = 503
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unavailable",
        "service": "campus-events-api",
    }
