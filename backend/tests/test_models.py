import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from models.node import Node
from models.opening import Opening

INITIAL_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def test_create_opening_with_root(session: Session):
    opening = Opening(name="Test Opening", color="white")
    session.add(opening)
    session.commit()
    session.refresh(opening)

    root = Node(
        opening_id=opening.id,
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

    assert opening.id is not None
    assert root.id is not None
    assert root.opening_id == opening.id


def test_unique_parent_move(session: Session):
    opening = Opening(name="Unique Test", color="white")
    session.add(opening)
    session.commit()
    session.refresh(opening)

    root = Node(opening_id=opening.id, parent_id=None, fen=INITIAL_FEN, ply=0)
    session.add(root)
    session.commit()
    session.refresh(root)

    first = Node(
        opening_id=opening.id,
        parent_id=root.id,
        move_san="e4",
        move_uci="e2e4",
        fen=INITIAL_FEN,
        ply=1,
    )
    session.add(first)
    session.commit()

    duplicate = Node(
        opening_id=opening.id,
        parent_id=root.id,
        move_san="e4",
        move_uci="e2e4",
        fen=INITIAL_FEN,
        ply=1,
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_delete_opening_cascades(session: Session):
    opening = Opening(name="Cascade Test", color="black")
    session.add(opening)
    session.commit()
    session.refresh(opening)

    root = Node(opening_id=opening.id, parent_id=None, fen=INITIAL_FEN, ply=0)
    session.add(root)
    session.commit()

    session.delete(opening)
    session.commit()

    remaining = session.exec(select(Node)).all()
    assert remaining == []