from typing import Optional

from sqlmodel import Session, select, func

from models.node import Node
from models.opening import Opening
from models.training import PositionStat

INITIAL_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def create_root_node(session: Session, opening_id: int) -> Node:
    root = Node(
        opening_id=opening_id,
        parent_id=None,
        move_san=None,
        move_uci=None,
        fen=INITIAL_FEN,
        ply=0,
        order_index=0,
    )
    session.add(root)
    session.commit()
    session.refresh(root)
    return root


def count_nodes(session: Session, opening_id: int) -> int:
    return session.exec(
        select(func.count()).select_from(Node).where(Node.opening_id == opening_id)
    ).one()


def opening_accuracy(session: Session, opening_id: int) -> Optional[float]:
    stats = session.exec(
        select(PositionStat).join(Node).where(Node.opening_id == opening_id)
    ).all()
    attempts = sum(s.attempts for s in stats)
    correct = sum(s.correct for s in stats)
    if attempts == 0:
        return None
    return correct / attempts * 100