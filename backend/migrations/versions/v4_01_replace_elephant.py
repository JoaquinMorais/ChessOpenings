"""replace elephant gambit with private seed

Revision ID: v4_01_replace_elephant
Revises: 08861bdb618a
Create Date: 2026-11-13 23:50:00.000000

"""
import json
import logging
from pathlib import Path
from typing import Sequence, Union

from alembic import op
from sqlmodel import Session, select

from models.opening import Opening
from utils.opening_io import import_opening

revision: str = "v4_01_replace_elephant"
down_revision: Union[str, None] = "08861bdb618a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger(__name__)
SEED_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "seed_import"
    / "private"
    / "elephant-gambit.json"
)


def upgrade() -> None:
    if not SEED_PATH.is_file():
        logger.warning("Private Elephant Gambit seed not found: %s", SEED_PATH)
        return

    try:
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read private Elephant Gambit seed: %s", exc)
        return

    with Session(bind=op.get_bind()) as session:
        existing = session.exec(
            select(Opening).where(Opening.name == "Elephant Gambit")
        ).first()
        if existing is not None:
            session.delete(existing)

        try:
            import_opening(session, data, on_conflict="reject")
        except Exception as exc:
            logger.warning(
                "Could not replace Elephant Gambit from private seed: %s",
                exc,
            )
            return


def downgrade() -> None:
    # The old Elephant Gambit content is not recoverable.
    pass
