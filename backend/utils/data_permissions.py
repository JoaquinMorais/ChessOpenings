import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def owner_of(path: Path) -> tuple[int, int]:
    try:
        stat = path.stat()
    except OSError:
        stat = DATA_DIR.stat()
    return stat.st_uid, stat.st_gid


def apply_permissions(
    path: Path,
    mode: int,
    owner: tuple[int, int] | None = None,
) -> None:
    target_owner = owner or owner_of(path.parent)
    try:
        os.chown(path, target_owner[0], target_owner[1])
    except OSError as exc:
        logger.warning("Could not chown %s: %s", path, exc)

    try:
        os.chmod(path, mode)
    except OSError as exc:
        logger.warning("Could not chmod %s: %s", path, exc)


def apply_directory_permissions(
    path: Path,
    owner: tuple[int, int] | None = None,
) -> None:
    apply_permissions(path, 0o775, owner)


def apply_seed_permissions(
    path: Path,
    visibility: str,
    owner: tuple[int, int],
) -> None:
    mode = 0o644 if visibility == "public" else 0o600
    apply_permissions(path, mode, owner)


def apply_local_permissions(
    path: Path,
    owner: tuple[int, int],
) -> None:
    apply_permissions(path, 0o600, owner)


def normalize_data_permissions(data_dir: Path | None = None) -> None:
    root = data_dir if data_dir is not None else DATA_DIR
    try:
        root.mkdir(parents=True, exist_ok=True)
        seed_root = root / "seed_import"
        public_dir = seed_root / "public"
        private_dir = seed_root / "private"
        local_dir = root / "local"
        for directory in (seed_root, public_dir, private_dir, local_dir):
            directory.mkdir(parents=True, exist_ok=True)

        owner = owner_of(root)
        apply_directory_permissions(root, owner)
        for directory in (seed_root, public_dir, private_dir, local_dir):
            apply_directory_permissions(directory, owner)

        for path in sorted(seed_root.rglob("*")):
            if path.is_dir():
                apply_directory_permissions(path, owner)
            elif path.parent == public_dir:
                apply_permissions(path, 0o644, owner)
            elif path.parent == private_dir:
                mode = 0o644 if path.name in {".gitignore", ".gitkeep"} else 0o600
                apply_permissions(path, mode, owner)
            else:
                apply_permissions(path, 0o600, owner)

        for path in sorted(local_dir.rglob("*")):
            if path.is_dir():
                apply_directory_permissions(path, owner)
            else:
                apply_local_permissions(path, owner)
    except OSError as exc:
        logger.warning("Could not normalize data permissions: %s", exc)
