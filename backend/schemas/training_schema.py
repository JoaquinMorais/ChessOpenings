from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class TrainingSessionCreate(BaseModel):
    opening_id: int


class TrainingAnswerCreate(BaseModel):
    node_id: int
    move: str


class TrainingSessionRead(BaseModel):
    id: int
    opening_id: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    questions_total: int
    first_try_correct: int
    step: Optional[Dict[str, Any]] = None


class TrainingAnswerRead(BaseModel):
    correct: bool
    correct_move_san: Optional[str] = None
    correct_move_uci: Optional[str] = None
    next_step: Dict[str, Any]