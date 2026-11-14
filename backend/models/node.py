from typing import Optional

from sqlalchemy import CheckConstraint, String, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class Node(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("parent_id", "move_uci", name="uq_node_parent_move"),
        CheckConstraint(
            "NOT (eval_cp IS NOT NULL AND eval_mate IS NOT NULL)",
            name="ck_node_single_evaluation",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    opening_id: int = Field(foreign_key="opening.id", ondelete="CASCADE")
    parent_id: Optional[int] = Field(default=None, foreign_key="node.id", ondelete="CASCADE")
    move_san: Optional[str] = None
    move_uci: Optional[str] = None
    fen: str
    ply: int = 0
    order_index: int = 0
    name: Optional[str] = Field(default=None, sa_type=String(80))
    comment: Optional[str] = Field(default=None, sa_type=Text)
    classification: Optional[str] = None
    eval_cp: Optional[int] = None
    eval_mate: Optional[int] = None
    eval_source: Optional[str] = None

    @property
    def evaluation(self) -> Optional[dict[str, int | str]]:
        source = self.eval_source or "manual"
        if self.eval_cp is not None:
            return {"cp": self.eval_cp, "source": source}
        if self.eval_mate is not None:
            if self.eval_mate == 0:
                side = self.fen.split()[1] if len(self.fen.split()) > 1 else "w"
                return {
                    "cp": -9999 if side == "w" else 9999,
                    "source": source,
                }
            return {"mate": self.eval_mate, "source": source}
        return None