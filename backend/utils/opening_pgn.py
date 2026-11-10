import io
import re
from typing import Any, Dict, List, Optional, Tuple

import chess
import chess.pgn
from sqlmodel import Session, select

from models.classification import Classification
from models.node import Node
from models.opening import Opening
from utils.tree import build_tree

VALID_CLASSIFICATIONS = {classification.value for classification in Classification}

NAG_TO_CLASSIFICATION = {
    chess.pgn.NAG_BRILLIANT_MOVE: "brilliant",
    chess.pgn.NAG_GOOD_MOVE: "great",
    chess.pgn.NAG_MISTAKE: "mistake",
    chess.pgn.NAG_BLUNDER: "blunder",
    chess.pgn.NAG_DUBIOUS_MOVE: "inaccuracy",
}
CLASSIFICATION_TO_NAG = {
    classification: nag for nag, classification in NAG_TO_CLASSIFICATION.items()
}
COMMENT_TAG_CLASSIFICATIONS = {"best", "excellent", "good", "book", "miss"}
CLASSIFICATION_TAG_PATTERN = re.compile(r"\[%cls\s+([a-zA-Z_]+)\]", re.IGNORECASE)


class PgnImportError(ValueError):
    pass


def _format_move_path(moves: List[str]) -> str:
    parts: List[str] = []
    for index, san in enumerate(moves):
        if index % 2 == 0:
            parts.append(f"{index // 2 + 1}. {san}")
        else:
            parts.append(str(san))
    return " ".join(parts)


def _metadata_from_node(
    node: chess.pgn.ChildNode,
) -> Tuple[Optional[str], Optional[str]]:
    classification: Optional[str] = None
    for nag in sorted(node.nags):
        if nag in NAG_TO_CLASSIFICATION:
            classification = NAG_TO_CLASSIFICATION[nag]
            break

    comment = node.comment or ""
    tag_classification: Optional[str] = None

    def replace_tag(match: re.Match[str]) -> str:
        nonlocal tag_classification
        key = match.group(1).lower()
        if key not in VALID_CLASSIFICATIONS:
            return match.group(0)
        if tag_classification is None:
            tag_classification = key
        return ""

    cleaned_comment = CLASSIFICATION_TAG_PATTERN.sub(replace_tag, comment).strip()
    if classification is None:
        classification = tag_classification

    return cleaned_comment or None, classification


def _own_color(color: str) -> chess.Color:
    return chess.WHITE if color == "white" else chess.BLACK


def _collect_own_conflicts(
    game_node: chess.pgn.GameNode,
    board: chess.Board,
    color: str,
    path: List[str],
    conflicts: List[Tuple[List[str], List[str]]],
) -> None:
    variations = [child for child in game_node.variations if child.move is not None]
    if len(variations) > 1 and board.turn == _own_color(color):
        child_sans = [board.san(child.move) for child in variations]
        conflicts.append((list(path), child_sans))

    for child in variations:
        san = board.san(child.move)
        next_board = board.copy()
        next_board.push(child.move)
        _collect_own_conflicts(child, next_board, color, path + [san], conflicts)


def _parse_variations(
    game_node: chess.pgn.GameNode,
    board: chess.Board,
    color: str,
    path: List[str],
    on_own_branch: str,
) -> List[Dict[str, Any]]:
    variations = [child for child in game_node.variations if child.move is not None]
    if (
        on_own_branch == "first"
        and len(variations) > 1
        and board.turn == _own_color(color)
    ):
        variations = variations[:1]

    parsed: List[Dict[str, Any]] = []
    for child in variations:
        move = child.move
        try:
            san = board.san(move)
            uci = move.uci()
        except ValueError as exc:
            position = _format_move_path(path) or "posición inicial"
            raise PgnImportError(
                f"Jugada inválida en {position}: {exc}"
            ) from exc

        next_board = board.copy()
        next_board.push(move)
        comment, classification = _metadata_from_node(child)
        parsed.append(
            {
                "san": san,
                "name": None,
                "comment": comment,
                "classification": classification,
                "children": _parse_variations(
                    child,
                    next_board,
                    color,
                    path + [san],
                    on_own_branch,
                ),
            }
        )
    return parsed


def pgn_to_import_data(
    pgn_text: str,
    color: str,
    name: Optional[str] = None,
    on_own_branch: str = "error",
) -> Dict[str, Any]:
    if on_own_branch not in ("error", "first"):
        raise PgnImportError(
            "on_own_branch debe ser 'error' o 'first'."
        )
    if color not in ("white", "black"):
        raise PgnImportError("El color debe ser 'white' o 'black'.")

    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception as exc:
        raise PgnImportError("El PGN no es válido.") from exc

    if game is None or not game.variations:
        raise PgnImportError("El PGN no contiene jugadas.")
    if game.errors:
        errors = "; ".join(str(error) for error in game.errors)
        raise PgnImportError(f"El PGN contiene errores: {errors}")

    event_name = (game.headers.get("Event") or "").strip()
    if event_name == "?":
        event_name = ""
    resolved_name = (name or "").strip() or event_name
    if not resolved_name:
        raise PgnImportError(
            "El PGN no tiene nombre y no se proporcionó uno."
        )

    if on_own_branch == "error":
        conflicts: List[Tuple[List[str], List[str]]] = []
        _collect_own_conflicts(game, chess.Board(), color, [], conflicts)
        if conflicts:
            details = []
            for path, moves in conflicts:
                position = _format_move_path(path) or "posición inicial"
                details.append(f"{position}: {', '.join(moves)}")
            raise PgnImportError(
                "Hay varias jugadas propias en: " + "; ".join(details)
            )

    children = _parse_variations(game, chess.Board(), color, [], on_own_branch)
    return {
        "format": "chess-openings-trainer",
        "version": 1,
        "opening": {
            "name": resolved_name,
            "color": color,
            "tree": {"children": children},
        },
    }


def _apply_metadata(game_node: chess.pgn.GameNode, node: Dict[str, Any]) -> None:
    classification = node.get("classification")
    comment = node.get("comment") or ""

    if classification in CLASSIFICATION_TO_NAG:
        game_node.nags.add(CLASSIFICATION_TO_NAG[classification])
    elif classification in COMMENT_TAG_CLASSIFICATIONS:
        tag = f"[%cls {classification}]"
        comment = f"{comment} {tag}".strip() if comment else tag

    if comment:
        game_node.comment = comment


def _add_variations(
    parent_node: chess.pgn.GameNode,
    tree_node: Dict[str, Any],
    board: chess.Board,
) -> None:
    children = sorted(
        tree_node["children"],
        key=lambda child: child["order_index"],
    )
    for child in children:
        if not child.get("uci"):
            continue
        try:
            move = board.parse_uci(child["uci"])
        except ValueError as exc:
            raise ValueError(
                f"No se pudo exportar la jugada {child.get('san')}: {exc}"
            ) from exc

        game_node = parent_node.add_variation(move)
        _apply_metadata(game_node, child)
        next_board = board.copy()
        next_board.push(move)
        _add_variations(game_node, child, next_board)


def export_opening_pgn(session: Session, opening_id: int) -> str:
    opening = session.get(Opening, opening_id)
    if not opening:
        raise LookupError("La apertura no existe.")

    nodes = session.exec(select(Node).where(Node.opening_id == opening_id)).all()
    tree = build_tree(nodes)

    game = chess.pgn.Game()
    game.headers["Event"] = opening.name
    game.headers["Site"] = "Chess Openings Trainer"
    game.headers["White"] = (
        opening.name if opening.color == "white" else "Rival"
    )
    game.headers["Black"] = (
        opening.name if opening.color == "black" else "Rival"
    )
    game.headers["Result"] = "*"

    _add_variations(game, tree, chess.Board())
    return str(game) + "\n"