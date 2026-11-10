import random
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from sqlmodel import Session, select

from models.node import Node
from models.opening import Opening
from models.training import PositionStat, TrainingSession
from utils.training import TrainingNode, answer as training_answer, start as training_start
from utils.tree import build_tree


class TrainingNotFoundError(Exception):
    pass


class TrainingConflictError(Exception):
    pass


class TrainingAnswerError(Exception):
    pass


def _to_training_node(data: Dict[str, Any]) -> TrainingNode:
    return TrainingNode(
        id=data["id"],
        san=data["san"],
        uci=data["uci"],
        fen=data["fen"],
        ply=data["ply"],
        order_index=data["order_index"],
        children=[_to_training_node(child) for child in data["children"]],
    )


def _build_training_tree(session: Session, opening_id: int) -> TrainingNode:
    nodes = session.exec(select(Node).where(Node.opening_id == opening_id)).all()
    return _to_training_node(build_tree(nodes))


def create_training_session(
    session: Session, opening_id: int
) -> Tuple[TrainingSession, Dict[str, Any]]:
    opening = session.get(Opening, opening_id)
    if not opening:
        raise TrainingNotFoundError("La apertura no existe.")

    tree = _build_training_tree(session, opening_id)
    state, step = training_start(tree, opening.color, random.Random())

    if state["questions_total"] == 0:
        raise TrainingConflictError("No hay nada para entrenar.")

    state["last_step"] = step
    training_session = TrainingSession(
        opening_id=opening_id,
        state=state,
        questions_total=state["questions_total"],
        first_try_correct=0,
    )
    session.add(training_session)
    session.commit()
    session.refresh(training_session)
    return training_session, step


def get_training_session(session: Session, session_id: int) -> TrainingSession:
    training_session = session.get(TrainingSession, session_id)
    if not training_session:
        raise TrainingNotFoundError("La sesion no existe.")
    return training_session


def submit_training_answer(
    session: Session, session_id: int, node_id: int, move_uci: str
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    training_session = session.get(TrainingSession, session_id)
    if not training_session:
        raise TrainingNotFoundError("La sesion no existe.")
    if training_session.finished_at is not None:
        raise TrainingConflictError("La sesion ya termino.")

    try:
        result, new_state, step = training_answer(
            training_session.state, node_id, move_uci
        )
    except ValueError as exc:
        raise TrainingAnswerError(str(exc))

    now = datetime.now(timezone.utc)
    position_stat = session.exec(
        select(PositionStat).where(PositionStat.node_id == node_id)
    ).first()
    if not position_stat:
        position_stat = PositionStat(node_id=node_id, attempts=0, correct=0)
    position_stat.attempts += 1
    if result["correct"]:
        position_stat.correct += 1
    position_stat.last_practiced_at = now
    session.add(position_stat)

    new_state["last_step"] = step
    training_session.state = new_state
    training_session.questions_total = new_state["questions_total"]
    training_session.first_try_correct = new_state["first_try_correct"]
    if step["kind"] == "finished":
        training_session.finished_at = now
    session.add(training_session)
    session.commit()
    session.refresh(training_session)

    return result, step