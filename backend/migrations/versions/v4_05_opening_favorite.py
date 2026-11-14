"""opening favorite

Revision ID: v4_05_opening_favorite
Revises: v4_01_replace_elephant
Create Date: 2026-11-14 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "v4_05_opening_favorite"
down_revision: Union[str, None] = "v4_01_replace_elephant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "opening",
        sa.Column(
            "is_favorite",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("opening", "is_favorite")
