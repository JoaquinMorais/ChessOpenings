"""node evaluation

Revision ID: ec05a3954d89
Revises: 4f7298615f4e
Create Date: 2026-11-11 00:07:28.231913

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec05a3954d89'
down_revision: Union[str, None] = '4f7298615f4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('node', sa.Column('eval_cp', sa.Integer(), nullable=True))
    op.add_column('node', sa.Column('eval_mate', sa.Integer(), nullable=True))
    op.create_check_constraint(
        'ck_node_single_evaluation',
        'node',
        'NOT (eval_cp IS NOT NULL AND eval_mate IS NOT NULL)',
    )


def downgrade() -> None:
    op.drop_constraint(
        'ck_node_single_evaluation',
        'node',
        type_='check',
    )
    op.drop_column('node', 'eval_mate')
    op.drop_column('node', 'eval_cp')