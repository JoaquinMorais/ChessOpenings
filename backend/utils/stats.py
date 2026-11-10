from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from models.node import Node
from models.opening import Opening
from models.training import PositionStat


def _format_move_path(moves: List[str]) -> str:
    parts: List[str] = []
    for index, san in enumerate(moves):
        if index % 2 == 0:
            parts.append(f"{index // 2 + 1}. {san}")
        else:
            parts.append(str(san))
    return " ".join(parts)


def _node_path_san(by_id: Dict[int, Node], node_id: int) -> str:
    moves: List[str] = []
    current: Optional[Node] = by_id.get(node_id)
    while current is not None and current.parent_id is not None:
        if current.move_san:
            moves.append(current.move_san)
        current = by_id.get(current.parent_id)
    moves.reverse()
    return _format_move_path(moves)


def opening_stats(session: Session, opening_id: int) -> Dict[str, Any]:
    opening = session.get(Opening, opening_id)
    if not opening:
        raise LookupError("La apertura no existe.")

    nodes = session.exec(select(Node).where(Node.opening_id == opening_id)).all()
    by_id = {node.id: node for node in nodes}

    stats = session.exec(
        select(PositionStat)
        .join(Node)
        .where(Node.opening_id == opening_id)
        .order_by(PositionStat.node_id)
    ).all()

    total_attempts = sum(stat.attempts for stat in stats)
    total_correct = sum(stat.correct for stat in stats)
    accuracy = total_correct / total_attempts * 100 if total_attempts else None

    positions = []
    for stat in stats:
        position_accuracy = (
            stat.correct / stat.attempts * 100 if stat.attempts else None
        )
        positions.append(
            {
                "node_id": stat.node_id,
                "path_san": _node_path_san(by_id, stat.node_id),
                "attempts": stat.attempts,
                "correct": stat.correct,
                "accuracy": position_accuracy,
                "last_practiced_at": stat.last_practiced_at,
            }
        )

    return {
        "opening_id": opening_id,
        "accuracy": accuracy,
        "positions": positions,
    }