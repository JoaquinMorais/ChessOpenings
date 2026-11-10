from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Node(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("parent_id", "move_uci", name="uq_node_parent_move"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    opening_id: int = Field(foreign_key="opening.id", ondelete="CASCADE")
    parent_id: Optional[int] = Field(default=None, foreign_key="node.id", ondelete="CASCADE")
    move_san: Optional[str] = None
    move_uci: Optional[str] = None
    fen: str
    ply: int = 0
    order_index: int = 0
    comment: Optional[str] = None