from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from config.database import get_session
from models.node import Node
from models.opening import Opening
from schemas.node_schema import MoveCreate, NodeRead
from utils.tree import IllegalMoveError, apply_move, side_to_move

router = APIRouter(tags=["nodes"])


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
    return node