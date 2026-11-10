from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from config.database import get_session
from schemas.stats_schema import OpeningStatsRead
from utils.stats import opening_stats

router = APIRouter(tags=["stats"])


@router.get("/openings/{opening_id}/stats", response_model=OpeningStatsRead)
def get_opening_stats(opening_id: int, session: Session = Depends(get_session)):
    try:
        return opening_stats(session, opening_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))