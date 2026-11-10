from typing import Optional

from pydantic import BaseModel, ConfigDict


class MoveCreate(BaseModel):
    parent_id: int
    move: str


class NodeUpdate(BaseModel):
    name: Optional[str] = None
    comment: Optional[str] = None
    classification: Optional[str] = None


class TranspositionInfo(BaseModel):
    node_id: int
    path_san: str


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
    name: Optional[str] = None
    comment: Optional[str] = None
    classification: Optional[str] = None
    transposition_of: Optional[TranspositionInfo] = None


class NodeTree(BaseModel):
    id: int
    san: Optional[str] = None
    uci: Optional[str] = None
    fen: str
    ply: int
    order_index: int
    name: Optional[str] = None
    comment: Optional[str] = None
    classification: Optional[str] = None
    children: list["NodeTree"] = []


NodeTree.model_rebuild()