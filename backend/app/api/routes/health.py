from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.database import get_db

router = APIRouter(tags=["system"])


@router.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok", "service": "formaprospect-cloud-api"}


@router.get("/ready", include_in_schema=False)
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}

