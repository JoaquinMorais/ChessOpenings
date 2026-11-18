import chess
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from config.database import get_session
from models.node import Node
from schemas.node_schema import Evaluation
from schemas.recommendation_schema import (
    RecommendationMoveRead,
    RecommendationRead,
)
from utils.recommendations import RecommendationError, get_recommendations

router = APIRouter(tags=["recommendations"])


@router.get(
    "/nodes/{node_id}/recommendations",
    response_model=RecommendationRead,
)
def get_node_recommendations(
    node_id: int,
    session: Session = Depends(get_session),
):
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="El nodo no existe.")

    board = chess.Board(node.fen)
    try:
        moves = get_recommendations(node.fen)
    except RecommendationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return RecommendationRead(
        node_id=node.id,
        fen=node.fen,
        side_to_move="white" if board.turn == chess.WHITE else "black",
        moves=[
            RecommendationMoveRead(
                rank=move["rank"],
                uci=move["uci"],
                san=move["san"],
                evaluation=Evaluation(
                    source="engine",
                    **move["evaluation"],
                ),
                depth=move["depth"],
            )
            for move in moves
        ],
    )
