from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from config.database import get_session
from models.opening import Opening
from schemas.opening_schema import OpeningCreate, OpeningRead, OpeningUpdate
from utils.openings import count_nodes, create_root_node, opening_accuracy
from utils.seed_files import delete_seed_file, seed_visibility

router = APIRouter(prefix="/openings", tags=["openings"])


def _to_read(session: Session, opening: Opening) -> OpeningRead:
    visibility = seed_visibility(opening.name)
    return OpeningRead(
        id=opening.id,
        name=opening.name,
        color=opening.color,
        node_count=count_nodes(session, opening.id),
        accuracy=opening_accuracy(session, opening.id),
        in_seed=visibility is not None,
        seed_visibility=visibility,
    )


@router.get("", response_model=list[OpeningRead])
def list_openings(session: Session = Depends(get_session)):
    openings = session.exec(select(Opening)).all()
    return [_to_read(session, o) for o in openings]


@router.post("", response_model=OpeningRead, status_code=201)
def create_opening(payload: OpeningCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(Opening).where(Opening.name == payload.name)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe una apertura con ese nombre.")
    opening = Opening(name=payload.name, color=payload.color)
    session.add(opening)
    session.commit()
    session.refresh(opening)
    create_root_node(session, opening.id)
    return _to_read(session, opening)


@router.get("/{opening_id}", response_model=OpeningRead)
def get_opening(opening_id: int, session: Session = Depends(get_session)):
    opening = session.get(Opening, opening_id)
    if not opening:
        raise HTTPException(status_code=404, detail="La apertura no existe.")
    return _to_read(session, opening)


@router.patch("/{opening_id}", response_model=OpeningRead)
def update_opening(opening_id: int, payload: OpeningUpdate, session: Session = Depends(get_session)):
    opening = session.get(Opening, opening_id)
    if not opening:
        raise HTTPException(status_code=404, detail="La apertura no existe.")
    if payload.name != opening.name:
        existing = session.exec(select(Opening).where(Opening.name == payload.name)).first()
        if existing:
            raise HTTPException(status_code=409, detail="Ya existe una apertura con ese nombre.")
    # Renaming does not move or delete the old seed_import file. The old file
    # remains on disk and may reappear under its old name after a restart.
    opening.name = payload.name
    session.add(opening)
    session.commit()
    session.refresh(opening)
    return _to_read(session, opening)


@router.delete("/{opening_id}", status_code=204)
def delete_opening(
    opening_id: int,
    scope: Literal["local", "seed", "both"] | None = Query(default=None),
    session: Session = Depends(get_session),
):
    opening = session.get(Opening, opening_id)
    if not opening:
        raise HTTPException(status_code=404, detail="La apertura no existe.")

    has_seed_file = seed_visibility(opening.name) is not None
    if has_seed_file and scope is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "Indicá el alcance del borrado: local, seed o both."
            ),
        )

    if has_seed_file and scope in ("seed", "both"):
        delete_seed_file(session, opening.name)

    if not has_seed_file or scope in ("local", "both"):
        session.delete(opening)
        session.commit()

    return None