from typing import Literal, Optional

from pydantic import BaseModel


class OpeningCreate(BaseModel):
    name: str
    color: Literal["white", "black"]


class OpeningUpdate(BaseModel):
    name: str


class OpeningRead(BaseModel):
    id: int
    name: str
    color: str
    node_count: int
    accuracy: Optional[float] = None