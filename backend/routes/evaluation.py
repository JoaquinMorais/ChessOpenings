from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from config.database import get_session
from config.settings import settings
from models.opening import Opening
from schemas.evaluation_schema import EvaluationStatusRead, JobRead
from utils.evaluation_jobs import (
    JobNotFound,
    JobNotRunning,
    cancel_job,
    evaluation_status,
    get_job_status,
)

router = APIRouter(tags=["evaluation"])


@router.get(
    "/openings/{opening_id}/evaluation-status",
    response_model=EvaluationStatusRead,
)
def get_evaluation_status(
    opening_id: int,
    session: Session = Depends(get_session),
):
    opening = session.get(Opening, opening_id)
    if not opening:
        raise HTTPException(status_code=404, detail="La apertura no existe.")
    total, missing, running, job_id = evaluation_status(session, opening_id)
    return EvaluationStatusRead(
        total=total,
        missing=missing,
        running=running,
        job_id=job_id,
        evaluator=settings.evaluator,
    )


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: str):
    status = get_job_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="El job no existe.")
    return JobRead(**status)


@router.post("/jobs/{job_id}/cancel", response_model=JobRead)
def cancel_evaluation_job(job_id: str):
    try:
        status = cancel_job(job_id)
    except JobNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except JobNotRunning as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return JobRead(**status)
