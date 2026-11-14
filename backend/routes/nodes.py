from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from config.database import get_session
from models.classification import Classification
from models.node import Node
from models.opening import Opening
from schemas.node_schema import (
    MoveCreate,
    NodeRead,
    NodeTree,
    NodeUpdate,
    TranspositionInfo,
)
from utils.evaluation import evaluation_to_columns
from utils.tree import (
    IllegalMoveError,
    apply_move,
    build_tree,
    node_path_san,
    normalize_fen,
    side_to_move,
)

router = APIRouter(tags=["nodes"])


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


@router.post("/openings/{opening_id}/moves", response_model=NodeRead)
def add_move(
    opening_id: int,
    payload: MoveCreate,
    response: Response,
    session: Session = Depends(get_session),
):
    opening = session.get(Opening, opening_id)
    if not opening:
        raise HTTPException(status_code=404, detail="La apertura no existe.")

    parent = session.get(Node, payload.parent_id)
    if not parent or parent.opening_id != opening_id:
        raise HTTPException(status_code=404, detail="El nodo padre no pertenece a la apertura.")

    try:
        result = apply_move(parent.fen, parent.ply, payload.move)
    except IllegalMoveError as exc:
        raise HTTPException(status_code=422, detail=f"Jugada ilegal: {exc}")

    existing = session.exec(
        select(Node).where(Node.parent_id == parent.id, Node.move_uci == result.uci)
    ).first()
    if existing:
        response.status_code = 200
        return existing

    if side_to_move(parent.fen, opening.color) == "user":
        siblings = session.exec(select(Node).where(Node.parent_id == parent.id)).all()
        if siblings:
            raise HTTPException(
                status_code=409,
                detail="En tu turno solo puede haber una jugada correcta.",
            )

    siblings = session.exec(select(Node).where(Node.parent_id == parent.id)).all()
    order_index = (max((n.order_index for n in siblings), default=-1) + 1)

    opening_nodes = session.exec(
        select(Node).where(Node.opening_id == opening_id)
    ).all()
    new_fen_key = normalize_fen(result.fen)
    transposition: TranspositionInfo | None = None
    for other in sorted(opening_nodes, key=lambda item: item.id):
        if normalize_fen(other.fen) == new_fen_key:
            transposition = TranspositionInfo(
                node_id=other.id,
                path_san=node_path_san(opening_nodes, other.id),
            )
            break

    node = Node(
        opening_id=opening_id,
        parent_id=parent.id,
        move_san=result.san,
        move_uci=result.uci,
        fen=result.fen,
        ply=result.ply,
        order_index=order_index,
    )
    session.add(node)
    session.commit()
    session.refresh(node)
    response.status_code = 201

    node_read = NodeRead.model_validate(node)
    node_read.transposition_of = transposition
    return node_read


@router.get("/openings/{opening_id}/tree", response_model=NodeTree)
def get_tree(opening_id: int, session: Session = Depends(get_session)):
    opening = session.get(Opening, opening_id)
    if not opening:
        raise HTTPException(status_code=404, detail="La apertura no existe.")
    nodes = session.exec(select(Node).where(Node.opening_id == opening_id)).all()
    try:
        tree = build_tree(nodes)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return tree


@router.patch("/nodes/{node_id}", response_model=NodeRead)
def update_node(
    node_id: int,
    payload: NodeUpdate,
    session: Session = Depends(get_session),
):
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="El nodo no existe.")

    fields = payload.model_fields_set
    if node.parent_id is None and (not fields or fields - {"evaluation"}):
        raise HTTPException(
            status_code=409,
            detail="No se puede editar la raiz de la apertura.",
        )

    if "name" in fields:
        name = _normalize_optional_text(payload.name)
        if name is not None and len(name) > 80:
            raise HTTPException(
                status_code=422,
                detail="El nombre de la rama no puede superar los 80 caracteres.",
            )
        node.name = name

    if "comment" in fields:
        node.comment = _normalize_optional_text(payload.comment)

    if "classification" in fields:
        value = _normalize_optional_text(payload.classification)
        if value is None:
            node.classification = None
        else:
            try:
                node.classification = Classification(value).value
            except ValueError as exc:
                raise HTTPException(
                    status_code=422,
                    detail="La clasificacion no es valida.",
                ) from exc

    if "evaluation" in fields:
        node.eval_cp, node.eval_mate = evaluation_to_columns(payload.evaluation)
        node.eval_source = "manual" if payload.evaluation is not None else None

    session.add(node)
    session.commit()
    session.refresh(node)
    return node


@router.delete("/nodes/{node_id}", status_code=204)
def delete_node(node_id: int, session: Session = Depends(get_session)):
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="El nodo no existe.")
    if node.parent_id is None:
        raise HTTPException(status_code=409, detail="No se puede borrar la raiz de la apertura.")
    parent_id = node.parent_id
    session.delete(node)
    session.commit()
    siblings = session.exec(
        select(Node).where(Node.parent_id == parent_id).order_by(Node.order_index, Node.id)
    ).all()
    for index, sibling in enumerate(siblings):
        sibling.order_index = index
        session.add(sibling)
    session.commit()
    return None


@router.post("/nodes/{node_id}/make-main", response_model=NodeRead)
def make_main(node_id: int, session: Session = Depends(get_session)):
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="El nodo no existe.")
    siblings = session.exec(
        select(Node).where(Node.parent_id == node.parent_id).order_by(Node.order_index, Node.id)
    ).all()
    ordered = [node] + [sibling for sibling in siblings if sibling.id != node.id]
    for index, sibling in enumerate(ordered):
        sibling.order_index = index
        session.add(sibling)
    session.commit()
    session.refresh(node)
    return node