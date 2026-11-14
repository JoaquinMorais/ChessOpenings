import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from models.opening import Opening
from models.seed_import import SeedImport
from utils import seed_files
from utils.opening_io import (
    ImportNameConflictError,
    InvalidImportError,
    import_opening,
)

logger = logging.getLogger(__name__)


def _register_seed(
    session: Session,
    file_key: str,
    name: str,
    content_hash: str,
) -> None:
    session.add(
        SeedImport(
            file_key=file_key,
            name=name,
            content_hash=content_hash,
            imported_at=datetime.now(timezone.utc),
        )
    )
    session.commit()


def load_seed(session: Session, seed_import_dir: Path | None = None) -> None:
    seen_names: set[str] = set()

    for path, file_key, _visibility in seed_files.iter_seed_files(
        seed_import_dir
    ):
        registered = session.exec(
            select(SeedImport).where(SeedImport.file_key == file_key)
        ).first()
        if registered is not None:
            seen_names.add(registered.name)
            continue

        try:
            raw = path.read_bytes()
            data = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.warning("Could not read seed file %s: %s", path, exc)
            continue

        opening_data = data.get("opening") if isinstance(data, dict) else None
        name = (
            opening_data.get("name")
            if isinstance(opening_data, dict)
            else None
        )
        if not isinstance(name, str) or not name.strip():
            logger.warning(
                "Seed file %s has no valid opening name; skipping.", path
            )
            continue

        if name in seen_names:
            logger.warning(
                "Seed file %s duplicates opening %s; skipping.",
                path,
                name,
            )
            continue

        content_hash = hashlib.sha256(raw).hexdigest()
        existing = session.exec(
            select(Opening).where(Opening.name == name)
        ).first()
        if existing is not None:
            _register_seed(session, file_key, name, content_hash)
            seen_names.add(name)
            continue

        try:
            import_opening(session, data, on_conflict="reject")
        except (
            InvalidImportError,
            ImportNameConflictError,
        ) as exc:
            logger.warning("Could not import seed file %s: %s", path, exc)
            continue
        except Exception as exc:
            logger.warning(
                "Unexpected error importing seed file %s: %s", path, exc
            )
            continue

        _register_seed(session, file_key, name, content_hash)
        seen_names.add(name)
