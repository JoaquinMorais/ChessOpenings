from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from models.classification import Classification
from models.node import Node
from models.opening import Opening
from schemas.node_schema import Evaluation
from utils.evaluation import evaluation_to_columns, parse_evaluation
from utils.openings import INITIAL_FEN, count_nodes, opening_accuracy
from utils.tree import IllegalMoveError, apply_move, build_tree, side_to_move


class InvalidImportError(ValueError):
    pass


class ImportNameConflictError(ValueError):
    pass


VALID_CLASSIFICATIONS = {classification.value for classification in Classification}


@dataclass
class _ParsedImport:
    name: str
    color: str
    evaluation: Optional[Evaluation]
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
            "name": node["name"],
            "comment": node["comment"],
            "classification": node["classification"],
            "evaluation": node["evaluation"],
            "children": [export_node(child) for child in node["children"]],
        }

    return {
        "format": "chess-openings-trainer",
        "version": 1,
        "opening": {
            "name": opening.name,
            "color": opening.color,
            "tree": {
                "evaluation": tree["evaluation"],
                "children": [
                    export_node(child) for child in tree["children"]
                ],
            },
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

    try:
        root_evaluation = parse_evaluation(
            tree_data.get("evaluation"),
            INITIAL_FEN,
        )
    except ValueError as exc:
        raise InvalidImportError(
            f"Evaluacion invalida en la posicion inicial: {exc}"
        ) from exc

    parsed_children = _parse_children(
        INITIAL_FEN, 0, children_data, color, []
    )
    return _ParsedImport(
        name=name,
        color=color,
        evaluation=root_evaluation,
        children=parsed_children,
    )


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

        name_raw = child_data.get("name", None)
        if name_raw is not None and not isinstance(name_raw, str):
            raise InvalidImportError("El nombre de la rama no es valido.")
        name = name_raw.strip() if isinstance(name_raw, str) else None
        if name == "":
            name = None
        if name is not None and len(name) > 80:
            raise InvalidImportError(
                "El nombre de la rama no puede superar los 80 caracteres."
            )

        comment_raw = child_data.get("comment", None)
        if comment_raw is not None and not isinstance(comment_raw, str):
            raise InvalidImportError("El comentario no es valido.")
        comment = comment_raw.strip() if isinstance(comment_raw, str) else None
        if comment == "":
            comment = None

        classification_raw = child_data.get("classification", None)
        if classification_raw is not None and not isinstance(
            classification_raw, str
        ):
            raise InvalidImportError("La clasificacion no es valida.")
        classification = (
            classification_raw.strip()
            if isinstance(classification_raw, str)
            else None
        )
        if classification == "":
            classification = None
        if (
            classification is not None
            and classification not in VALID_CLASSIFICATIONS
        ):
            move_path = _format_move_path(path + [san_raw])
            raise InvalidImportError(
                f"Clasificacion desconocida en {move_path}: {classification}"
            )

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

        try:
            evaluation = parse_evaluation(
                child_data.get("evaluation"),
                result.fen,
            )
        except ValueError as exc:
            move_path = _format_move_path(path + [san_raw])
            raise InvalidImportError(
                f"Evaluacion invalida en {move_path}: {exc}"
            ) from exc

        parsed.append(
            {
                "san": result.san,
                "uci": result.uci,
                "fen": result.fen,
                "ply": result.ply,
                "name": name,
                "comment": comment,
                "classification": classification,
                "evaluation": evaluation,
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
        evaluation = child["evaluation"]
        eval_cp, eval_mate = evaluation_to_columns(evaluation)
        node = Node(
            opening_id=opening_id,
            parent_id=parent_id,
            move_san=child["san"],
            move_uci=child["uci"],
            fen=child["fen"],
            ply=child["ply"],
            order_index=index,
            name=child["name"],
            comment=child["comment"],
            classification=child["classification"],
            eval_cp=eval_cp,
            eval_mate=eval_mate,
            eval_source=evaluation.source if evaluation is not None else None,
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

        root_eval_cp, root_eval_mate = evaluation_to_columns(parsed.evaluation)
        root = Node(
            opening_id=opening.id,
            parent_id=None,
            move_san=None,
            move_uci=None,
            fen=INITIAL_FEN,
            ply=0,
            order_index=0,
            eval_cp=root_eval_cp,
            eval_mate=root_eval_mate,
            eval_source=(
                parsed.evaluation.source
                if parsed.evaluation is not None
                else None
            ),
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