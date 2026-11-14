import json
import logging
from typing import Any, Dict, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from sqlmodel import Session, select

from config.database import get_session
from models.opening import Opening
from models.seed_import import SeedImport
from schemas.opening_schema import (
    OpeningRead,
    SeedFileInfo,
    SeedFileRead,
    SeedRestoreRequest,
    SeedSaveRequest,
)
from utils.evaluation_jobs import JobAlreadyRunning, start_evaluation_job
from utils.evaluators import is_external_evaluator
from utils.openings import count_nodes, opening_accuracy
from utils.opening_pgn import PgnImportError, export_opening_pgn, pgn_to_import_data
from utils.opening_io import (
    ImportNameConflictError,
    InvalidImportError,
    export_opening,
    import_opening,
)
from utils.seed_files import (
    delete_seed_file,
    iter_seed_files,
    opening_name_from_file,
    resolve_seed_file_key,
    seed_visibility,
    write_seed_file,
)

router = APIRouter(tags=["io"])
logger = logging.getLogger(__name__)


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

    visibility = seed_visibility(opening.name)
    return OpeningRead(
        id=opening.id,
        name=opening.name,
        color=opening.color,
        node_count=count_nodes(session, opening.id),
        accuracy=opening_accuracy(session, opening.id),
        in_seed=visibility is not None,
        seed_visibility=visibility,
        is_favorite=opening.is_favorite,
    )


@router.post(
    "/openings/{opening_id}/seed",
    response_model=SeedFileRead,
)
def save_opening_seed(
    opening_id: int,
    payload: SeedSaveRequest,
    session: Session = Depends(get_session),
):
    opening = session.get(Opening, opening_id)
    if not opening:
        raise HTTPException(status_code=404, detail="La apertura no existe.")

    if (
        payload.evaluate
        and is_external_evaluator()
        and payload.visibility == "private"
        and not payload.allow_external
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "El evaluator externo requiere allow_external=true "
                "para valorar una apertura privada."
            ),
        )

    path = write_seed_file(session, opening, payload.visibility)
    job = None
    message = None
    if payload.evaluate:
        try:
            job = start_evaluation_job(
                session,
                opening.id,
                payload.visibility,
            )
        except JobAlreadyRunning as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        if job is None:
            message = "La apertura ya esta valorada."

    return SeedFileRead(
        path=f"data/seed_import/{payload.visibility}/{path.name}",
        job_id=job.id if job is not None else None,
        message=message,
    )


@router.delete("/openings/{opening_id}/seed", status_code=204)
def remove_opening_seed(opening_id: int, session: Session = Depends(get_session)):
    opening = session.get(Opening, opening_id)
    if not opening:
        raise HTTPException(status_code=404, detail="La apertura no existe.")
    delete_seed_file(session, opening.name)
    return None


@router.get("/seed/files", response_model=list[SeedFileInfo])
def list_seed_files(session: Session = Depends(get_session)):
    files: list[SeedFileInfo] = []
    for path, key, visibility in iter_seed_files():
        name = opening_name_from_file(path)
        if name is None:
            logger.warning("Seed file %s has no valid opening name; skipping.", path)
            continue

        opening = session.exec(
            select(Opening).where(Opening.name == name)
        ).first()
        if opening is not None:
            state = "in_db"
        elif session.exec(
            select(SeedImport).where(SeedImport.file_key == key)
        ).first() is not None:
            state = "deleted_locally"
        else:
            state = "new"

        files.append(
            SeedFileInfo(
                file_key=key,
                name=name,
                visibility=visibility,
                state=state,
            )
        )
    return files


@router.post("/seed/restore", response_model=OpeningRead, status_code=201)
def restore_seed_file(
    payload: SeedRestoreRequest,
    session: Session = Depends(get_session),
):
    try:
        path = resolve_seed_file_key(payload.file_key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="El archivo de seed no existe.",
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=422,
            detail="El archivo de seed no es valido.",
        ) from exc

    name = opening_name_from_file(path)
    if name is None:
        raise HTTPException(
            status_code=422,
            detail="El archivo de seed no tiene un nombre de apertura valido.",
        )

    if session.exec(select(Opening).where(Opening.name == name)).first():
        raise HTTPException(
            status_code=409,
            detail="Ya existe una apertura con ese nombre.",
        )

    try:
        opening = import_opening(session, data, on_conflict="reject")
    except ImportNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    visibility = (
        "private" if payload.file_key.startswith("private/") else "public"
    )
    return OpeningRead(
        id=opening.id,
        name=opening.name,
        color=opening.color,
        node_count=count_nodes(session, opening.id),
        accuracy=opening_accuracy(session, opening.id),
        in_seed=True,
        seed_visibility=visibility,
        is_favorite=opening.is_favorite,
    )


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

    visibility = seed_visibility(opening.name)
    return OpeningRead(
        id=opening.id,
        name=opening.name,
        color=opening.color,
        node_count=count_nodes(session, opening.id),
        accuracy=opening_accuracy(session, opening.id),
        in_seed=visibility is not None,
        seed_visibility=visibility,
        is_favorite=opening.is_favorite,
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
