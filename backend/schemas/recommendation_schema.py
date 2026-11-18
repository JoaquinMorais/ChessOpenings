from typing import Literal, Optional

from pydantic import BaseModel

from schemas.node_schema import Evaluation


class RecommendationMoveRead(BaseModel):
    rank: int
    uci: str
    san: str
    evaluation: Evaluation
    depth: Optional[int] = None


class RecommendationRead(BaseModel):
    node_id: int
    fen: str
    side_to_move: Literal["white", "black"]
    moves: list[RecommendationMoveRead]
