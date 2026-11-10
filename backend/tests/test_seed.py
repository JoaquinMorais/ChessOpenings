from sqlmodel import Session, select

from models.node import Node
from models.opening import Opening
from utils.seed import load_seed


def test_seed_loads_on_empty_db(session: Session):
    load_seed(session)

    openings = session.exec(select(Opening)).all()
    assert len(openings) == 2
    names = {opening.name for opening in openings}
    assert names == {"Elephant Gambit", "Italian Game"}
    colors = {opening.name: opening.color for opening in openings}
    assert colors["Elephant Gambit"] == "black"
    assert colors["Italian Game"] == "white"


def test_seed_includes_name_and_comment(session: Session):
    load_seed(session)

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


def test_seed_does_not_load_if_db_has_data(session: Session):
    session.add(Opening(name="Existing", color="white"))
    session.commit()

    load_seed(session)

    openings = session.exec(select(Opening)).all()
    assert len(openings) == 1
    assert openings[0].name == "Existing"


def test_seed_is_idempotent(session: Session):
    load_seed(session)
    load_seed(session)

    openings = session.exec(select(Opening)).all()
    assert len(openings) == 2