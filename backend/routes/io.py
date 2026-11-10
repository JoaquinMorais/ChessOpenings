import json
from typing import Any, Dict, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from sqlmodel import Session

from config.database import get_session
from models.opening import Opening
from schemas.opening_schema import OpeningRead, SeedFileRead
from utils.openings import count_nodes, opening_accuracy
from utils.opening_pgn import PgnImportError, export_opening_pgn, pgn_to_import_data
from utils.opening_io import (
    ImportNameConflictError,
    InvalidImportError,
    export_opening,
    import_opening,
)
from utils.seed_files import delete_seed_file, seed_file_exists, write_seed_file

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

@router.post(
    "/openings/{opening_id}/seed",
    response_model=SeedFileRead,
)
def save_opening_seed(opening_id: int, session: Session = Depends(get_session)):
    opening = session.get(Opening, opening_id)
    if not opening:
        raise HTTPException(status_code=404, detail="La apertura no existe.")
    path = write_seed_file(session, opening)
    return SeedFileRead(path=f"data/seed_import/{path.name}")


@router.delete("/openings/{opening_id}/seed", status_code=204)
def remove_opening_seed(opening_id: int, session: Session = Depends(get_session)):
    opening = session.get(Opening, opening_id)
    if not opening:
        raise HTTPException(status_code=404, detail="La apertura no existe.")
    delete_seed_file(opening.name)
    return None


async def _read_pgn_payload(request: Request) -> tuple[str, str | None, str]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(
                status_code=422,
                detail="El cuerpo debe ser un objeto JSON.",
            )
        pgn = body.get("pgn")
        name = body.get("name")
        color = body.get("color")
    elif content_type.startswith("multipart/form-data") or content_type.startswith(
        "application/x-www-form-urlencoded"
    ):
        form = await request.form()
        upload = form.get("file")
        if upload is not None and hasattr(upload, "read"):
            pgn = (await upload.read()).decode("utf-8", errors="replace")
        else:
            pgn = form.get("pgn")
        name = form.get("name")
        color = form.get("color")
    else:
        raise HTTPException(
            status_code=422,
            detail="Enviá el PGN como JSON o multipart/form-data.",
        )

    if not isinstance(pgn, str) or not pgn.strip():
        raise HTTPException(
            status_code=422,
            detail="El PGN está vacío.",
        )
    if color not in ("white", "black"):
        raise HTTPException(
            status_code=422,
            detail="El color debe ser 'white' o 'black'.",
        )
    if name is not None and not isinstance(name, str):
        raise HTTPException(
            status_code=422,
            detail="El nombre debe ser un texto.",
        )

    return pgn, (name.strip() or None if isinstance(name, str) else None), color


@router.post("/openings/import-pgn", response_model=OpeningRead, status_code=201)
async def import_pgn_endpoint(
    request: Request,
    on_own_branch: Literal["error", "first"] = Query("error"),
    session: Session = Depends(get_session),
):
    pgn_text, name, color = await _read_pgn_payload(request)

    try:
        data = pgn_to_import_data(
            pgn_text,
            color,
            name=name,
            on_own_branch=on_own_branch,
        )
        opening = import_opening(session, data, on_conflict="reject")
    except PgnImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
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
        in_seed=seed_file_exists(opening.name),
    )


@router.get("/openings/{opening_id}/export.pgn")
def export_pgn_endpoint(opening_id: int, session: Session = Depends(get_session)):
    try:
        content = export_opening_pgn(session, opening_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="La apertura no existe.")

    opening = session.get(Opening, opening_id)
    filename = f"{opening.name}.pgn".replace('"', "")
    return Response(
        content=content,
        media_type="application/x-chess-pgn",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
