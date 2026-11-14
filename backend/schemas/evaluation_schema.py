from typing import Literal, Optional

from pydantic import BaseModel


class EvaluationStatusRead(BaseModel):
    total: int
    missing: int
    running: bool
    job_id: Optional[str] = None
    evaluator: Literal["stockfish", "llm"]


class JobRead(BaseModel):
    state: Literal["running", "done", "cancelled", "error"]
    done: int
    total: int
    errors: int
    message: Optional[str] = None
