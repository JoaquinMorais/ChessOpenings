from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from config.database import get_session
from models.training import TrainingSession
from schemas.training_schema import (
    TrainingAnswerCreate,
    TrainingAnswerRead,
    TrainingSessionCreate,
    TrainingSessionRead,
)
from utils.training_service import (
    TrainingAnswerError,
    TrainingConflictError,
    TrainingNotFoundError,
    create_training_session,
    get_training_session,
    submit_training_answer,
)

router = APIRouter(prefix="/training/sessions", tags=["training"])


def _to_read(training_session: TrainingSession) -> TrainingSessionRead:
    state = training_session.state or {}
    return TrainingSessionRead(
        id=training_session.id,
        opening_id=training_session.opening_id,
        started_at=training_session.started_at,
        finished_at=training_session.finished_at,
        questions_total=training_session.questions_total,
        first_try_correct=training_session.first_try_correct,
        step=state.get("last_step"),
    )


@router.post("", response_model=TrainingSessionRead, status_code=201)
def create_session(
    payload: TrainingSessionCreate, session: Session = Depends(get_session)
):
    try:
        training_session, _ = create_training_session(session, payload.opening_id)
    except TrainingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except TrainingConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return _to_read(training_session)


@router.get("/{session_id}", response_model=TrainingSessionRead)
def get_session_endpoint(session_id: int, session: Session = Depends(get_session)):
    try:
        training_session = get_training_session(session, session_id)
    except TrainingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _to_read(training_session)


@router.post("/{session_id}/answer", response_model=TrainingAnswerRead)
def answer_session(
    session_id: int,
    payload: TrainingAnswerCreate,
    session: Session = Depends(get_session),
):
    try:
        result, step = submit_training_answer(
            session, session_id, payload.node_id, payload.move
        )
    except TrainingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except TrainingConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except TrainingAnswerError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return TrainingAnswerRead(
        correct=result["correct"],
        correct_move_san=result["correct_move_san"],
        correct_move_uci=result["correct_move_uci"],
        next_step=step,
    )