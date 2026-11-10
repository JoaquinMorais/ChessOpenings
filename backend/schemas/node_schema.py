from typing import Optional

from pydantic import BaseModel, ConfigDict


class MoveCreate(BaseModel):
    parent_id: int
    move: str


class NodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    opening_id: int
    parent_id: Optional[int] = None
    move_san: Optional[str] = None
    move_uci: Optional[str] = None
    fen: str
    ply: int
    order_index: int
    comment: Optional[str] = None