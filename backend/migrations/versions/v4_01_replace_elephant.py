"""remove legacy elephant gambit

Revision ID: v4_01_replace_elephant
Revises: 08861bdb618a
Create Date: 2026-11-13 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "v4_01_replace_elephant"
down_revision: Union[str, None] = "08861bdb618a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        text("DELETE FROM seed_import WHERE name = :name"),
        {"name": "Elephant Gambit"},
    )
    bind.execute(
        text("DELETE FROM opening WHERE name = :name"),
        {"name": "Elephant Gambit"},
    )


def downgrade() -> None:
    pass
