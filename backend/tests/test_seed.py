from pathlib import Path

from sqlmodel import Session, select

from models.node import Node
from models.opening import Opening
from utils.seed import load_seed


def test_seed_loads_on_empty_db(session: Session, tmp_path: Path):
    load_seed(session, tmp_path)

    openings = session.exec(select(Opening)).all()
    assert len(openings) == 3
    names = {opening.name for opening in openings}
    assert names == {"Elephant Gambit", "Italian Game", "Mate del pastor"}
    colors = {opening.name: opening.color for opening in openings}
    assert colors["Elephant Gambit"] == "black"
    assert colors["Italian Game"] == "white"
    assert colors["Mate del pastor"] == "white"


def test_seed_includes_name_and_comment(session: Session, tmp_path: Path):
    load_seed(session, tmp_path)

    opening = session.exec(
        select(Opening).where(Opening.name == "Elephant Gambit")
    ).one()
    root = session.exec(
        select(Node).where(Node.opening_id == opening.id, Node.parent_id.is_(None))
    ).one()
    e4 = session.exec(
        select(Node).where(
            Node.parent_id == root.id,
            Node.move_uci == "e2e4",
        )
    ).one()
    e5 = session.exec(
        select(Node).where(
            Node.parent_id == e4.id,
            Node.move_uci == "e7e5",
        )
    ).one()
    bc4 = session.exec(
        select(Node).where(
            Node.parent_id == e5.id,
            Node.move_uci == "f1c4",
        )
    ).one()

    assert e4.name == "Apertura del peón rey"
    assert e4.comment == "El rival abre con e4."
    assert e4.classification == "book"
    assert bc4.classification == "mistake"


def test_seed_includes_evaluations(session: Session, tmp_path: Path):
    load_seed(session, tmp_path)

    elephant = session.exec(
        select(Opening).where(Opening.name == "Elephant Gambit")
    ).one()
    elephant_root = session.exec(
        select(Node).where(
            Node.opening_id == elephant.id,
            Node.parent_id.is_(None),
        )
    ).one()
    e4 = session.exec(
        select(Node).where(
            Node.opening_id == elephant.id,
            Node.move_uci == "e2e4",
        )
    ).one()
    nf3 = session.exec(
        select(Node).where(
            Node.opening_id == elephant.id,
            Node.move_uci == "g1f3",
        )
    ).one()
    d5 = session.exec(
        select(Node).where(
            Node.parent_id == nf3.id,
            Node.move_uci == "d7d5",
        )
    ).one()
    assert elephant_root.eval_cp == 20
    assert e4.eval_cp == 30
    assert d5.eval_cp == -25

    mate_opening = session.exec(
        select(Opening).where(Opening.name == "Mate del pastor")
    ).one()
    mate_root = session.exec(
        select(Node).where(
            Node.opening_id == mate_opening.id,
            Node.parent_id.is_(None),
        )
    ).one()
    nf6 = session.exec(
        select(Node).where(
            Node.opening_id == mate_opening.id,
            Node.move_uci == "g8f6",
        )
    ).one()
    final_move = session.exec(
        select(Node).where(
            Node.opening_id == mate_opening.id,
            Node.move_uci == "h5f7",
        )
    ).one()
    assert mate_root.eval_cp == 20
    assert nf6.eval_mate == 1
    assert nf6.eval_cp is None
    assert nf6.classification == "blunder"
    assert final_move.eval_cp is None
    assert final_move.eval_mate is None


def test_seed_does_not_load_if_db_has_data(
    session: Session,
    tmp_path: Path,
):
    session.add(Opening(name="Existing", color="white"))
    session.commit()

    load_seed(session, tmp_path)

    openings = session.exec(select(Opening)).all()
    assert len(openings) == 1
    assert openings[0].name == "Existing"


def test_seed_is_idempotent(session: Session, tmp_path: Path):
    load_seed(session, tmp_path)
    load_seed(session, tmp_path)

    openings = session.exec(select(Opening)).all()
    assert len(openings) == 3