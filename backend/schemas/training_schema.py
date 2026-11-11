from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel

from schemas.node_schema import Evaluation


class TrainingSessionCreate(BaseModel):
    opening_id: int
    mode: Literal["full", "weak"] = "full"
    from_node_id: Optional[int] = None


class TrainingAnswerCreate(BaseModel):
    node_id: int
    move: str
    hint_used: bool = False


class TrainingSessionRead(BaseModel):
    id: int
    opening_id: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    questions_total: int
    first_try_correct: int
    step: Optional[Dict[str, Any]] = None


class TrainingAnswerMove(BaseModel):
    uci: Optional[str] = None
    san: Optional[str] = None
    name: Optional[str] = None
    comment: Optional[str] = None
    classification: Optional[str] = None
    evaluation: Optional[Evaluation] = None


class TrainingAnswerRead(BaseModel):
    correct: bool
    correct_move_san: Optional[str] = None
    correct_move_uci: Optional[str] = None
    correct_move: TrainingAnswerMove
    next_step: Dict[str, Any]