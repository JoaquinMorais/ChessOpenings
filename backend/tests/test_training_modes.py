from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session

from models.node import Node
from models.opening import Opening
from models.training import PositionStat
from utils.openings import INITIAL_FEN
from utils.training_service import TrainingConflictError, create_training_session
from utils.tree import apply_move


def _create_line(session: Session) -> tuple[Opening, list[int]]:
    opening = Opening(name="Weak Training", color="white")
    session.add(opening)
    session.commit()
    session.refresh(opening)

    root = Node(
        opening_id=opening.id,
        parent_id=None,
        fen=INITIAL_FEN,
        ply=0,
        order_index=0,
    )
    session.add(root)
    session.commit()
    session.refresh(root)

    nodes = [root]
    parent = root
    for san in ["e4", "e5", "Nf3", "Nc6", "Bc4", "a6", "Bb3"]:
        result = apply_move(parent.fen, parent.ply, san)
        node = Node(
            opening_id=opening.id,
            parent_id=parent.id,
            move_san=result.san,
            move_uci=result.uci,
            fen=result.fen,
            ply=result.ply,
            order_index=0,
        )
        session.add(node)
        session.commit()
        session.refresh(node)
        nodes.append(node)
        parent = node

    # White questions are at plies 0, 2, 4 and 6.
    question_ids = [nodes[index].id for index in (0, 2, 4, 6)]
    return opening, question_ids


def _add_stat(
    session: Session,
    node_id: int,
    attempts: int,
    correct: int,
    last_practiced_at: datetime,
) -> None:
    session.add(
        PositionStat(
            node_id=node_id,
            attempts=attempts,
            correct=correct,
            last_practiced_at=last_practiced_at,
        )
    )
    session.commit()


def test_weak_mode_filters_questions(session: Session):
    opening, question_ids = _create_line(session)
    now = datetime.now(timezone.utc)
    _add_stat(session, question_ids[0], 10, 10, now)
    _add_stat(session, question_ids[1], 10, 5, now)
    _add_stat(session, question_ids[2], 10, 10, now - timedelta(days=8))
    # question_ids[3] has no stats, so it is weak too.

    training_session, step = create_training_session(
        session, opening.id, mode="weak"
    )

    assert training_session.questions_total == 3
    assert step["kind"] == "question"
    assert step["node_id"] == question_ids[1]


def test_weak_mode_with_no_weak_questions(session: Session):
    opening, question_ids = _create_line(session)
    now = datetime.now(timezone.utc)
    for node_id in question_ids:
        _add_stat(session, node_id, 10, 10, now)

    with pytest.raises(TrainingConflictError) as exc:
        create_training_session(session, opening.id, mode="weak")

    assert "preguntas débiles" in str(exc.value)
