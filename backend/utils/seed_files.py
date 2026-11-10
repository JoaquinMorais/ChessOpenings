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


def seed_file_path(name: str, directory: Path | None = None) -> Path:
    return _resolve_directory(directory) / f"{slugify(name)}.json"


def seed_file_exists(name: str, directory: Path | None = None) -> bool:
    return seed_file_path(name, directory).is_file()


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
    path = seed_file_path(name, directory)
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False