import re
from dataclasses import dataclass
from typing import Literal, Sequence

import chess

from models.node import Node


@dataclass(frozen=True)
class MoveResult:
    san: str
    uci: str
    fen: str
    ply: int


class IllegalMoveError(ValueError):
    pass


def _parse_move(board: chess.Board, move: str) -> chess.Move:
    move = move.strip()
    if re.fullmatch(r"[a-h][1-8][a-h][1-8][qrbn]?", move):
        try:
            parsed = board.parse_uci(move)
        except ValueError as exc:
            raise IllegalMoveError("movimiento no valido en esta posicion") from exc
    else:
        try:
            parsed = board.parse_san(move)
        except ValueError as exc:
            raise IllegalMoveError("movimiento no valido en esta posicion") from exc
    if parsed not in board.legal_moves:
        raise IllegalMoveError("movimiento no legal en esta posicion")
    return parsed


def apply_move(parent_fen: str, parent_ply: int, move: str) -> MoveResult:
    board = chess.Board(parent_fen)
    parsed = _parse_move(board, move)
    san = board.san(parsed)
    uci = parsed.uci()
    board.push(parsed)
    return MoveResult(san=san, uci=uci, fen=board.fen(), ply=parent_ply + 1)


def side_to_move(fen: str, opening_color: str) -> Literal["user", "rival"]:
    board = chess.Board(fen)
    user_is_white = opening_color == "white"
    turn_is_white = board.turn == chess.WHITE
    return "user" if (turn_is_white == user_is_white) else "rival"


def build_tree(nodes: Sequence[Node]) -> dict:
    by_parent: dict = {}
    roots = []
    for node in nodes:
        if node.parent_id is None:
            roots.append(node)
        else:
            by_parent.setdefault(node.parent_id, []).append(node)

    if not roots:
        raise ValueError("La apertura no tiene nodo raiz.")
    if len(roots) > 1:
        raise ValueError("La apertura tiene mas de un nodo raiz.")

    def to_dict(node: Node) -> dict:
        children = sorted(
            by_parent.get(node.id, []),
            key=lambda child: child.order_index,
        )
        return {
            "id": node.id,
            "san": node.move_san,
            "uci": node.move_uci,
            "fen": node.fen,
            "ply": node.ply,
            "order_index": node.order_index,
            "comment": node.comment,
            "children": [to_dict(child) for child in children],
        }

    return to_dict(roots[0])