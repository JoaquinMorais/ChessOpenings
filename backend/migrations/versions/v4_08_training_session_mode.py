"""training session mode

Revision ID: v4_08_training_session_mode
Revises: v4_07_eval_source
Create Date: 2026-11-16 00:00:00.000000

"""
import json
from typing import Any, Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "v4_08_training_session_mode"
down_revision: Union[str, None] = "v4_07_eval_source"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _question_count(node: dict[str, Any], color: str) -> int:
    children = node.get("children") or []
    ply = node.get("ply", 0)
    user_turn = ply % 2 == (0 if color == "white" else 1)
    count = 1 if user_turn and children else 0
    return count + sum(_question_count(child, color) for child in children)


def _scope_node(
    node: dict[str, Any],
    scope_root_id: Any,
) -> dict[str, Any] | None:
    if node.get("id") == scope_root_id:
        return node
    for child in node.get("children") or []:
        found = _scope_node(child, scope_root_id)
        if found is not None:
            return found
    return None


def _is_weak(state: Any, questions_total: int) -> bool:
    if not isinstance(state, dict):
        return False
    tree = state.get("tree")
    if not isinstance(tree, dict):
        return False
    color = state.get("color")
    if color not in ("white", "black"):
        return False
    scope = _scope_node(tree, state.get("scope_root_id"))
    if scope is None:
        scope = tree
    return questions_total < _question_count(scope, color)


def upgrade() -> None:
    op.add_column(
        "trainingsession",
        sa.Column(
            "mode",
            sa.String(),
            nullable=False,
            server_default="full",
        ),
    )

    bind = op.get_bind()
    rows = bind.execute(
        text("SELECT id, state, questions_total FROM trainingsession")
    ).mappings()
    for row in rows:
        state = row["state"]
        if isinstance(state, str):
            try:
                state = json.loads(state)
            except json.JSONDecodeError:
                state = None
        if _is_weak(state, row["questions_total"]):
            bind.execute(
                text("UPDATE trainingsession SET mode = 'weak' WHERE id = :id"),
                {"id": row["id"]},
            )


def downgrade() -> None:
    op.drop_column("trainingsession", "mode")
