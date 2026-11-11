import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path

from sqlmodel import Session

from models.opening import Opening
from utils.opening_io import export_opening

SEED_IMPORT_DIR = Path(__file__).resolve().parent.parent / "data" / "seed_import"


def _resolve_directory(directory: Path | None) -> Path:
    return directory if directory is not None else SEED_IMPORT_DIR


def slugify(name: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", name)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug or "opening"


def _opening_name_from_file(path: Path) -> str | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    opening = data.get("opening") if isinstance(data, dict) else None
    name = opening.get("name") if isinstance(opening, dict) else None
    return name if isinstance(name, str) else None


def _find_seed_file(
    name: str,
    directory: Path | None = None,
) -> Path | None:
    target_directory = _resolve_directory(directory)
    slug_path = target_directory / f"{slugify(name)}.json"
    if slug_path.is_file():
        return slug_path

    if target_directory.is_dir():
        for path in sorted(target_directory.glob("*.json")):
            if _opening_name_from_file(path) == name:
                return path

    return None


def seed_file_path(name: str, directory: Path | None = None) -> Path:
    existing = _find_seed_file(name, directory)
    if existing is not None:
        return existing
    return _resolve_directory(directory) / f"{slugify(name)}.json"


def seed_file_exists(name: str, directory: Path | None = None) -> bool:
    return _find_seed_file(name, directory) is not None


def write_seed_file(
    session: Session,
    opening: Opening,
    directory: Path | None = None,
) -> Path:
    target_directory = _resolve_directory(directory)
    target_directory.mkdir(parents=True, exist_ok=True)

    data = export_opening(session, opening.id)
    path = seed_file_path(opening.name, target_directory)

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}.",
        suffix=".tmp",
        dir=target_directory,
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
            json.dump(data, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise

    return path


def delete_seed_file(name: str, directory: Path | None = None) -> bool:
    path = _find_seed_file(name, directory)
    if path is None:
        return False
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False