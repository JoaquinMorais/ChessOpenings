import hashlib
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Literal

from sqlmodel import Session, select

from models.opening import Opening
from models.seed_import import SeedImport
from utils.data_permissions import (
    apply_directory_permissions,
    apply_permissions,
    apply_seed_permissions,
    owner_of,
)
from utils.opening_io import export_opening

Visibility = Literal["public", "private"]

SEED_IMPORT_DIR = Path(__file__).resolve().parent.parent / "data" / "seed_import"
PRIVATE_GITIGNORE = "*\n!.gitignore\n!.gitkeep\n"
SEED_FILE_KEY_PATTERN = re.compile(r"^(public|private)/[^/\\]+\.json$")


def _resolve_root(root: Path | None) -> Path:
    return root if root is not None else SEED_IMPORT_DIR


def _visibility_directory(
    visibility: Visibility,
    root: Path | None = None,
) -> Path:
    return _resolve_root(root) / visibility


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


def opening_name_from_file(path: Path) -> str | None:
    return _opening_name_from_file(path)


def resolve_seed_file_key(
    file_key: str,
    root: Path | None = None,
) -> Path:
    if not isinstance(file_key, str) or not SEED_FILE_KEY_PATTERN.fullmatch(
        file_key
    ):
        raise ValueError("El file_key no es valido.")

    seed_root = _resolve_root(root).resolve()
    path = (seed_root / file_key).resolve()
    if not path.is_relative_to(seed_root):
        raise ValueError("El file_key no es valido.")
    return path


def _find_in_directory(name: str, directory: Path) -> list[Path]:
    found: list[Path] = []
    slug_path = directory / f"{slugify(name)}.json"
    if slug_path.is_file():
        found.append(slug_path)

    if directory.is_dir():
        for path in sorted(directory.glob("*.json")):
            if path == slug_path:
                continue
            if _opening_name_from_file(path) == name:
                found.append(path)

    return found


def find_seed_files(name: str, root: Path | None = None) -> list[Path]:
    found: list[Path] = []
    for visibility in ("private", "public"):
        found.extend(_find_in_directory(name, _resolve_root(root) / visibility))
    return found


def seed_visibility(
    name: str,
    root: Path | None = None,
) -> Visibility | None:
    for visibility in ("private", "public"):
        if _find_in_directory(name, _resolve_root(root) / visibility):
            return visibility
    return None


def seed_file_exists(name: str, root: Path | None = None) -> bool:
    return seed_visibility(name, root) is not None


def seed_file_path(name: str, root: Path | None = None) -> Path:
    files = find_seed_files(name, root)
    if files:
        return files[0]
    return _visibility_directory("public", root) / f"{slugify(name)}.json"


def file_key(path: Path, root: Path | None = None) -> str:
    return path.resolve().relative_to(_resolve_root(root).resolve()).as_posix()


def iter_seed_files(
    root: Path | None = None,
) -> Iterator[tuple[Path, str, Visibility]]:
    seed_root = _resolve_root(root)
    for visibility in ("private", "public"):
        directory = seed_root / visibility
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            yield path, f"{visibility}/{path.name}", visibility


def ensure_private_gitignore(root: Path | None = None) -> Path:
    private_dir = _visibility_directory("private", root)
    private_dir.mkdir(parents=True, exist_ok=True)
    seed_root = _resolve_root(root)
    owner = owner_of(seed_root)
    apply_directory_permissions(private_dir, owner)
    gitignore = private_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(PRIVATE_GITIGNORE, encoding="utf-8")
    apply_permissions(gitignore, 0o644, owner)
    return gitignore


def write_seed_file(
    session: Session,
    opening: Opening,
    visibility: Visibility,
    root: Path | None = None,
) -> Path:
    if visibility not in ("public", "private"):
        raise ValueError("La visibilidad debe ser 'public' o 'private'.")

    seed_root = _resolve_root(root)
    target_directory = _visibility_directory(visibility, seed_root)
    target_directory.mkdir(parents=True, exist_ok=True)
    owner = owner_of(seed_root)
    apply_directory_permissions(target_directory, owner)
    if visibility == "private":
        ensure_private_gitignore(seed_root)

    existing = find_seed_files(opening.name, seed_root)
    basename = existing[0].name if existing else f"{slugify(opening.name)}.json"
    for path in existing:
        path.unlink(missing_ok=True)

    data = export_opening(session, opening.id)
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path = target_directory / basename

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}.",
        suffix=".tmp",
        dir=target_directory,
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_name, path)
        apply_seed_permissions(path, visibility, owner)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise

    new_file_key = file_key(path, seed_root)
    rows = session.exec(
        select(SeedImport).where(SeedImport.name == opening.name)
    ).all()
    for row in rows:
        session.delete(row)

    now = datetime.now(timezone.utc)
    existing_row = session.exec(
        select(SeedImport).where(SeedImport.file_key == new_file_key)
    ).first()
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if existing_row is not None:
        existing_row.name = opening.name
        existing_row.content_hash = content_hash
        existing_row.imported_at = now
        session.add(existing_row)
    else:
        session.add(
            SeedImport(
                file_key=new_file_key,
                name=opening.name,
                content_hash=content_hash,
                imported_at=now,
            )
        )
    session.commit()
    return path


def delete_seed_file(
    session: Session,
    name: str,
    root: Path | None = None,
) -> bool:
    paths = find_seed_files(name, root)
    if not paths:
        return False

    for path in paths:
        path.unlink(missing_ok=True)

    rows = session.exec(
        select(SeedImport).where(SeedImport.name == name)
    ).all()
    for row in rows:
        session.delete(row)
    session.commit()
    return True
