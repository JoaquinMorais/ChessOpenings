"""baseline

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())

    if "opening" not in existing_tables:
        op.create_table(
            "opening",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("color", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )

    if "node" not in existing_tables:
        op.create_table(
            "node",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("opening_id", sa.Integer(), nullable=False),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("move_san", sa.String(), nullable=True),
            sa.Column("move_uci", sa.String(), nullable=True),
            sa.Column("fen", sa.String(), nullable=False),
            sa.Column("ply", sa.Integer(), nullable=False),
            sa.Column("order_index", sa.Integer(), nullable=False),
            sa.Column("comment", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(
                ["opening_id"], ["opening.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["parent_id"], ["node.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("parent_id", "move_uci", name="uq_node_parent_move"),
        )

    if "trainingsession" not in existing_tables:
        op.create_table(
            "trainingsession",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("opening_id", sa.Integer(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("questions_total", sa.Integer(), nullable=False),
            sa.Column("first_try_correct", sa.Integer(), nullable=False),
            sa.Column("state", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(
                ["opening_id"], ["opening.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    if "positionstat" not in existing_tables:
        op.create_table(
            "positionstat",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("node_id", sa.Integer(), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("correct", sa.Integer(), nullable=False),
            sa.Column("last_practiced_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["node_id"], ["node.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("node_id"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())

    for table_name in ("positionstat", "trainingsession", "node", "opening"):
        if table_name in existing_tables:
            op.drop_table(table_name)