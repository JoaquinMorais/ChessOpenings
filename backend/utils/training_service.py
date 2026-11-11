import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

from sqlmodel import Session, select

from models.node import Node
from models.opening import Opening
from models.training import PositionStat, TrainingSession
from utils.training import (
    TrainingNode,
    answer as training_answer,
    refresh_step,
    start as training_start,
)
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
        name=data.get("name"),
        comment=data.get("comment"),
        classification=data.get("classification"),
        evaluation=data.get("evaluation"),
        children=[_to_training_node(child) for child in data["children"]],
    )


def _build_training_tree(session: Session, opening_id: int) -> TrainingNode:
    nodes = session.exec(select(Node).where(Node.opening_id == opening_id)).all()
    return _to_training_node(build_tree(nodes))


def _index_training_tree(tree: TrainingNode) -> dict[int, TrainingNode]:
    by_id: dict[int, TrainingNode] = {}

    def walk(node: TrainingNode) -> None:
        by_id[node.id] = node
        for child in node.children:
            walk(child)

    walk(tree)
    return by_id


def _merge_tree_metadata(
    stored: Dict[str, Any],
    current_by_id: dict[int, TrainingNode],
) -> None:
    current = current_by_id.get(stored["id"])
    if current is not None:
        stored["name"] = current.name
        stored["comment"] = current.comment
        stored["classification"] = current.classification
        stored["evaluation"] = current.evaluation

    for child in stored.get("children", []):
        _merge_tree_metadata(child, current_by_id)


def _hydrate_session_state(
    session: Session,
    training_session: TrainingSession,
) -> Dict[str, Any]:
    state = training_session.state or {}
    tree = state.get("tree")
    if not isinstance(tree, dict):
        return state

    current_tree = _build_training_tree(session, training_session.opening_id)
    _merge_tree_metadata(tree, _index_training_tree(current_tree))

    last_step = state.get("last_step")
    if isinstance(last_step, dict):
        state["last_step"] = refresh_step(state, last_step)

    training_session.state = state
    return state


def _question_ids(tree: TrainingNode, color: str) -> set[int]:
    ids: set[int] = set()

    def walk(node: TrainingNode) -> None:
        user_turn = node.ply % 2 == (0 if color == "white" else 1)
        if user_turn and node.children:
            ids.add(node.id)
        for child in node.children:
            walk(child)

    walk(tree)
    return ids


def _weak_question_ids(
    session: Session,
    opening_id: int,
    tree: TrainingNode,
    color: str,
) -> set[int]:
    question_ids = _question_ids(tree, color)
    stats = session.exec(
        select(PositionStat)
        .join(Node)
        .where(Node.opening_id == opening_id)
    ).all()
    by_node = {stat.node_id: stat for stat in stats}
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    weak: set[int] = set()

    for node_id in question_ids:
        stat = by_node.get(node_id)
        if stat is None or stat.attempts == 0:
            weak.add(node_id)
            continue

        accuracy = stat.correct / stat.attempts * 100
        if accuracy < 70:
            weak.add(node_id)
            continue

        last_practiced_at = stat.last_practiced_at
        if last_practiced_at is None:
            weak.add(node_id)
            continue
        if last_practiced_at.tzinfo is None:
            last_practiced_at = last_practiced_at.replace(tzinfo=timezone.utc)
        if last_practiced_at < cutoff:
            weak.add(node_id)

    return weak


def create_training_session(
    session: Session,
    opening_id: int,
    mode: str = "full",
    from_node_id: int | None = None,
) -> Tuple[TrainingSession, Dict[str, Any]]:
    opening = session.get(Opening, opening_id)
    if not opening:
        raise TrainingNotFoundError("La apertura no existe.")
    if mode not in ("full", "weak"):
        raise TrainingConflictError("El modo de entrenamiento no es valido.")

    if from_node_id is not None:
        from_node = session.get(Node, from_node_id)
        if not from_node or from_node.opening_id != opening_id:
            raise TrainingNotFoundError(
                "La posicion no existe en la apertura."
            )

    tree = _build_training_tree(session, opening_id)
    question_filter = (
        _weak_question_ids(session, opening_id, tree, opening.color)
        if mode == "weak"
        else None
    )

    try:
        state, step = training_start(
            tree,
            opening.color,
            random.Random(),
            question_filter=question_filter,
            from_node_id=from_node_id,
        )
    except ValueError as exc:
        raise TrainingNotFoundError(str(exc))

    if state["questions_total"] == 0:
        if mode == "weak" and from_node_id is not None:
            detail = "No hay preguntas débiles en esta rama."
        elif mode == "weak":
            detail = "No hay preguntas débiles para entrenar."
        elif from_node_id is not None:
            detail = "No hay preguntas en esta rama."
        else:
            detail = "No hay nada para entrenar."
        raise TrainingConflictError(detail)

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
    _hydrate_session_state(session, training_session)
    return training_session


def submit_training_answer(
    session: Session,
    session_id: int,
    node_id: int,
    move_uci: str,
    hint_used: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    training_session = session.get(TrainingSession, session_id)
    if not training_session:
        raise TrainingNotFoundError("La sesion no existe.")
    if training_session.finished_at is not None:
        raise TrainingConflictError("La sesion ya termino.")

    state = _hydrate_session_state(session, training_session)
    try:
        result, new_state, step = training_answer(
            state,
            node_id,
            move_uci,
            hint_used=hint_used,
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