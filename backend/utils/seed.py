import json
import logging
from pathlib import Path

from sqlmodel import Session, select

from models.opening import Opening
from utils import seed_files
from utils.opening_io import (
    ImportNameConflictError,
    InvalidImportError,
    import_opening,
)

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed.json"

logger = logging.getLogger(__name__)


def _load_seed_json(session: Session) -> None:
    if session.exec(select(Opening)).first():
        return

    with SEED_PATH.open(encoding="utf-8") as seed_file:
        data = json.load(seed_file)

    for entry in data.get("openings", []):
        import_opening(session, entry, on_conflict="reject")


def _load_seed_import(session: Session, directory: Path | None) -> None:
    seed_directory = (
        directory if directory is not None else seed_files.SEED_IMPORT_DIR
    )
    if not seed_directory.is_dir():
        return

    for path in sorted(seed_directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
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

            if session.exec(select(Opening).where(Opening.name == name)).first():
                continue

            import_opening(session, data, on_conflict="reject")
        except (
            OSError,
            json.JSONDecodeError,
            InvalidImportError,
            ImportNameConflictError,
        ) as exc:
            logger.warning("Could not import seed file %s: %s", path, exc)
        except Exception as exc:
            logger.warning(
                "Unexpected error importing seed file %s: %s", path, exc
            )


def load_seed(session: Session, seed_import_dir: Path | None = None) -> None:
    _load_seed_json(session)
    _load_seed_import(session, seed_import_dir)