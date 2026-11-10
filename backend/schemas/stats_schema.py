from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PositionStatRead(BaseModel):
    node_id: int
    path_san: str
    attempts: int
    correct: int
    accuracy: Optional[float] = None
    last_practiced_at: Optional[datetime] = None


class OpeningStatsRead(BaseModel):
    opening_id: int
    accuracy: Optional[float] = None
    positions: List[PositionStatRead]