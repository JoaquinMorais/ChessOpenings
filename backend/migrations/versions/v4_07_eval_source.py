"""node evaluation source

Revision ID: v4_07_eval_source
Revises: v4_05_opening_favorite
Create Date: 2026-11-14 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "v4_07_eval_source"
down_revision: Union[str, None] = "v4_05_opening_favorite"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "node",
        sa.Column("eval_source", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("node", "eval_source")
