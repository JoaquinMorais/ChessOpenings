import json
from typing import Any, Dict, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from sqlmodel import Session

from config.database import get_session
from models.opening import Opening
from schemas.opening_schema import OpeningRead
from utils.openings import count_nodes, opening_accuracy
from utils.opening_io import (
    ImportNameConflictError,
    InvalidImportError,
    export_opening,
    import_opening,
)

router = APIRouter(tags=["io"])


@router.get("/openings/{opening_id}/export")
def export_opening_endpoint(opening_id: int, session: Session = Depends(get_session)):
    try:
        data = export_opening(session, opening_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="La apertura no existe.")

    filename = f"{data['opening']['name']}.json".replace('"', "")
    content = json.dumps(data, ensure_ascii=False, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/openings/import", response_model=OpeningRead, status_code=201)
def import_opening_endpoint(
    on_conflict: Literal["reject", "replace", "duplicate"] = Query("reject"),
    data: Dict[str, Any] = Body(...),
    session: Session = Depends(get_session),
):
    try:
        opening = import_opening(session, data, on_conflict)
    except ImportNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return OpeningRead(
        id=opening.id,
        name=opening.name,
        color=opening.color,
        node_count=count_nodes(session, opening.id),
        accuracy=opening_accuracy(session, opening.id),
    )