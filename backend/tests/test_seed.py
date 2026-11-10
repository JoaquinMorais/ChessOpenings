from sqlmodel import Session, select

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