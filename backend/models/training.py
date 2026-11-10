from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class TrainingSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    opening_id: int = Field(foreign_key="opening.id", ondelete="CASCADE")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    questions_total: int = 0
    first_try_correct: int = 0
    state: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class PositionStat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    node_id: int = Field(foreign_key="node.id", ondelete="CASCADE", unique=True)
    attempts: int = 0
    correct: int = 0
    last_practiced_at: Optional[datetime] = None