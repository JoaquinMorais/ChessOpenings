from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from models.node import Node
from models.opening import Opening
from utils.openings import INITIAL_FEN, count_nodes, opening_accuracy
from utils.tree import IllegalMoveError, apply_move, build_tree, side_to_move


class InvalidImportError(ValueError):
    pass


class ImportNameConflictError(ValueError):
    pass


@dataclass
class _ParsedImport:
    name: str
    color: str
    children: List[Dict[str, Any]]


def export_opening(session: Session, opening_id: int) -> Dict[str, Any]:
    opening = session.get(Opening, opening_id)
    if not opening:
        raise LookupError("La apertura no existe.")

    nodes = session.exec(select(Node).where(Node.opening_id == opening_id)).all()
    tree = build_tree(nodes)

    def export_node(node: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "san": node["san"],
            "comment": node["comment"],
            "children": [export_node(child) for child in node["children"]],
        }

    return {
        "format": "chess-openings-trainer",
        "version": 1,
        "opening": {
            "name": opening.name,
            "color": opening.color,
            "tree": {"children": [export_node(child) for child in tree["children"]]},
        },
    }


def _format_move_path(moves: List[str]) -> str:
    parts: List[str] = []
    for index, san in enumerate(moves):
        if index % 2 == 0:
            parts.append(f"{index // 2 + 1}. {san}")
        else:
            parts.append(str(san))
    return " ".join(parts)


def _parse_import(data: Any) -> _ParsedImport:
    if not isinstance(data, dict):
        raise InvalidImportError("El JSON debe ser un objeto.")

    if data.get("format") != "chess-openings-trainer":
        raise InvalidImportError("El formato no es valido.")
    if data.get("version") != 1:
        raise InvalidImportError("La version no es compatible.")

    opening_data = data.get("opening")
    if not isinstance(opening_data, dict):
        raise InvalidImportError("Falta la apertura.")

    name = opening_data.get("name")
    color = opening_data.get("color")
    if not isinstance(name, str) or not name.strip():
        raise InvalidImportError("El nombre de la apertura no es valido.")
    if color not in ("white", "black"):
        raise InvalidImportError("El color de la apertura no es valido.")

    tree_data = opening_data.get("tree")
    if not isinstance(tree_data, dict):
        raise InvalidImportError("Falta el arbol de la apertura.")

    children_data = tree_data.get("children", [])
    if children_data is None:
        children_data = []
    if not isinstance(children_data, list):
        raise InvalidImportError("Los hijos deben ser una lista.")

    parsed_children = _parse_children(
        INITIAL_FEN, 0, children_data, color, []
    )
    return _ParsedImport(name=name, color=color, children=parsed_children)


def _parse_children(
    parent_fen: str,
    parent_ply: int,
    children_data: List[Any],
    color: str,
    path: List[str],
) -> List[Dict[str, Any]]:
    if len(children_data) > 1 and side_to_move(parent_fen, color) == "user":
        offending = children_data[1]
        offending_san = offending.get("san") if isinstance(offending, dict) else None
        offending_path = _format_move_path(path + [str(offending_san)])
        raise InvalidImportError(
            f"En turno propio solo puede haber una jugada correcta: {offending_path}"
        )

    parsed: List[Dict[str, Any]] = []
    for child_data in children_data:
        if not isinstance(child_data, dict):
            raise InvalidImportError("Cada jugada debe ser un objeto.")

        san_raw = child_data.get("san")
        if not isinstance(san_raw, str) or not san_raw.strip():
            raise InvalidImportError("La jugada (san) no es valida.")

        comment = child_data.get("comment", None)
        if comment is not None and not isinstance(comment, str):
            raise InvalidImportError("El comentario no es valido.")

        child_children = child_data.get("children", [])
        if child_children is None:
            child_children = []
        if not isinstance(child_children, list):
            raise InvalidImportError("Los hijos deben ser una lista.")

        try:
            result = apply_move(parent_fen, parent_ply, san_raw)
        except IllegalMoveError:
            move_path = _format_move_path(path + [san_raw])
            raise InvalidImportError(f"Jugada ilegal: {move_path}")

        parsed.append(
            {
                "san": result.san,
                "uci": result.uci,
                "fen": result.fen,
                "ply": result.ply,
                "comment": comment,
                "children": _parse_children(
                    result.fen, result.ply, child_children, color, path + [result.san]
                ),
            }
        )
    return parsed


def _next_duplicate_name(session: Session, base_name: str) -> str:
    number = 2
    candidate = f"{base_name} (2)"
    while session.exec(select(Opening).where(Opening.name == candidate)).first():
        number += 1
        candidate = f"{base_name} ({number})"
    return candidate


def _insert_children(
    session: Session, opening_id: int, parent_id: int, children: List[Dict[str, Any]]
) -> None:
    for index, child in enumerate(children):
        node = Node(
            opening_id=opening_id,
            parent_id=parent_id,
            move_san=child["san"],
            move_uci=child["uci"],
            fen=child["fen"],
            ply=child["ply"],
            order_index=index,
            comment=child["comment"],
        )
        session.add(node)
        session.flush()
        _insert_children(session, opening_id, node.id, child["children"])


def import_opening(session: Session, data: Any, on_conflict: str = "reject") -> Opening:
    if on_conflict not in ("reject", "replace", "duplicate"):
        raise InvalidImportError("El modo de conflicto no es valido.")

    parsed = _parse_import(data)

    try:
        existing = session.exec(
            select(Opening).where(Opening.name == parsed.name)
        ).first()

        if existing:
            if on_conflict == "reject":
                raise ImportNameConflictError("Ya existe una apertura con ese nombre.")
            if on_conflict == "replace":
                session.delete(existing)
                session.flush()
            if on_conflict == "duplicate":
                parsed.name = _next_duplicate_name(session, parsed.name)

        opening = Opening(name=parsed.name, color=parsed.color)
        session.add(opening)
        session.flush()

        root = Node(
            opening_id=opening.id,
            parent_id=None,
            move_san=None,
            move_uci=None,
            fen=INITIAL_FEN,
            ply=0,
            order_index=0,
        )
        session.add(root)
        session.flush()

        _insert_children(session, opening.id, root.id, parsed.children)
        session.commit()
        session.refresh(opening)
        return opening
    except Exception:
        session.rollback()
        raise