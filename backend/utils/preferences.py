import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Iterable

from sqlmodel import Session, select

from models.opening import Opening
from utils.data_permissions import (
    apply_directory_permissions,
    apply_local_permissions,
    owner_of,
)

logger = logging.getLogger(__name__)

FAVORITES_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "local"
    / "favorites.json"
)


def _resolve_path(path: Path | None) -> Path:
    return path if path is not None else FAVORITES_PATH


def _unique(names: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


def read_favorites(path: Path | None = None) -> list[str]:
    target = _resolve_path(path)
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("Could not read favorites file %s: %s", target, exc)
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("Could not parse favorites file %s: %s", target, exc)
        return []

    if not isinstance(data, list) or not all(
        isinstance(name, str) for name in data
    ):
        logger.warning("Favorites file %s has an invalid format.", target)
        return []

    return data


def write_favorites(
    names: Iterable[str],
    path: Path | None = None,
) -> None:
    target = _resolve_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    owner = owner_of(target.parent.parent)
    apply_directory_permissions(target.parent, owner)
    content = json.dumps(_unique(names), ensure_ascii=False, indent=2) + "\n"

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.stem}.",
        suffix=".tmp",
        dir=target.parent,
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_name, target)
        apply_local_permissions(target, owner)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def apply_favorites(
    session: Session,
    path: Path | None = None,
) -> None:
    names = read_favorites(path)
    if not names:
        return

    openings = session.exec(
        select(Opening).where(Opening.name.in_(names))
    ).all()
    changed = False
    for opening in openings:
        if not opening.is_favorite:
            opening.is_favorite = True
            session.add(opening)
            changed = True

    if changed:
        session.commit()


def set_favorite(
    session: Session,
    opening: Opening,
    value: bool,
    path: Path | None = None,
) -> None:
    opening.is_favorite = value
    session.add(opening)
    session.commit()
    session.refresh(opening)

    names = read_favorites(path)
    if value:
        if opening.name not in names:
            names.append(opening.name)
    else:
        names = [name for name in names if name != opening.name]
    write_favorites(names, path)


def rename_favorite(
    old_name: str,
    new_name: str,
    path: Path | None = None,
) -> None:
    names = read_favorites(path)
    if old_name not in names:
        return

    write_favorites(
        [new_name if name == old_name else name for name in names],
        path,
    )
