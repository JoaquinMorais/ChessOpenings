import json
from pathlib import Path

from sqlmodel import Session, select

from models.opening import Opening
from utils.opening_io import import_opening

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed.json"


def load_seed(session: Session) -> None:
    if session.exec(select(Opening)).first():
        return

    with SEED_PATH.open(encoding="utf-8") as seed_file:
        data = json.load(seed_file)

    for entry in data.get("openings", []):
        import_opening(session, entry, on_conflict="reject")