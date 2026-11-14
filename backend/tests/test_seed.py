import json
import logging
from pathlib import Path

from sqlmodel import Session, select

from models.node import Node
from models.opening import Opening
from models.seed_import import SeedImport
from utils.opening_io import import_opening
from utils.seed import load_seed
from utils.seed_files import (
    file_key,
    find_seed_files,
    seed_visibility,
    write_seed_file,
)


def _seed_data(name: str, move: str = "e4") -> dict:
    return {
        "format": "chess-openings-trainer",
        "version": 1,
        "opening": {
            "name": name,
            "color": "white",
            "tree": {
                "children": [
                    {
                        "san": move,
                        "comment": None,
                        "children": [],
                    }
                ]
            },
        },
    }


def _write_seed(
    path: Path,
    name: str,
    move: str = "e4",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_seed_data(name, move), ensure_ascii=False),
        encoding="utf-8",
    )


def _first_child_san(session: Session, opening_id: int) -> str | None:
    root = session.exec(
        select(Node).where(
            Node.opening_id == opening_id,
            Node.parent_id.is_(None),
        )
    ).one()
    child = session.exec(
        select(Node).where(Node.parent_id == root.id).order_by(
            Node.order_index
        )
    ).first()
    return child.move_san if child else None


def _create_opening(session: Session, name: str) -> Opening:
    return import_opening(session, _seed_data(name))


def test_load_seed_imports_private_and_public(
    session: Session,
    tmp_path: Path,
):
    _write_seed(tmp_path / "private" / "private.json", "Private Seed")
    _write_seed(tmp_path / "public" / "public.json", "Public Seed", "d4")

    load_seed(session, tmp_path)

    names = {
        opening.name for opening in session.exec(select(Opening)).all()
    }
    assert names == {"Private Seed", "Public Seed"}
    assert len(session.exec(select(SeedImport)).all()) == 2


def test_second_start_does_not_reimport(
    session: Session,
    tmp_path: Path,
):
    path = tmp_path / "public" / "stable.json"
    _write_seed(path, "Stable Seed", "e4")
    load_seed(session, tmp_path)

    opening = session.exec(
        select(Opening).where(Opening.name == "Stable Seed")
    ).one()
    row = session.exec(
        select(SeedImport).where(SeedImport.name == "Stable Seed")
    ).one()
    original_hash = row.content_hash
    assert _first_child_san(session, opening.id) == "e4"

    _write_seed(path, "Stable Seed", "d4")
    load_seed(session, tmp_path)

    assert _first_child_san(session, opening.id) == "e4"
    session.refresh(row)
    assert row.content_hash == original_hash


def test_deleted_opening_does_not_resurrect(
    session: Session,
    tmp_path: Path,
):
    _write_seed(tmp_path / "public" / "gone.json", "Gone Seed")
    load_seed(session, tmp_path)
    opening = session.exec(
        select(Opening).where(Opening.name == "Gone Seed")
    ).one()
    session.delete(opening)
    session.commit()

    load_seed(session, tmp_path)

    assert (
        session.exec(
            select(Opening).where(Opening.name == "Gone Seed")
        ).first()
        is None
    )
    assert (
        session.exec(
            select(SeedImport).where(SeedImport.name == "Gone Seed")
        ).first()
        is not None
    )


def test_new_database_imports_again(
    session: Session,
    tmp_path: Path,
):
    _write_seed(tmp_path / "public" / "again.json", "Again Seed")
    load_seed(session, tmp_path)

    for row in session.exec(select(SeedImport)).all():
        session.delete(row)
    for opening in session.exec(select(Opening)).all():
        session.delete(opening)
    session.commit()

    load_seed(session, tmp_path)

    assert (
        session.exec(
            select(Opening).where(Opening.name == "Again Seed")
        ).first()
        is not None
    )


def test_new_file_is_imported(
    session: Session,
    tmp_path: Path,
):
    _write_seed(tmp_path / "public" / "first.json", "First Seed")
    load_seed(session, tmp_path)

    _write_seed(tmp_path / "public" / "second.json", "Second Seed", "d4")
    load_seed(session, tmp_path)

    names = {
        opening.name for opening in session.exec(select(Opening)).all()
    }
    assert names == {"First Seed", "Second Seed"}


def test_invalid_file_is_ignored(
    session: Session,
    tmp_path: Path,
    caplog,
):
    (tmp_path / "public").mkdir(parents=True)
    (tmp_path / "public" / "broken.json").write_text(
        "not json",
        encoding="utf-8",
    )
    _write_seed(tmp_path / "public" / "valid.json", "Valid Seed")

    caplog.set_level(logging.WARNING)
    load_seed(session, tmp_path)

    names = {
        opening.name for opening in session.exec(select(Opening)).all()
    }
    assert names == {"Valid Seed"}
    assert any(
        "Could not read seed file" in record.message
        for record in caplog.records
    )


def test_name_collision_private_wins(
    session: Session,
    tmp_path: Path,
    caplog,
):
    _write_seed(tmp_path / "private" / "collision.json", "Collision Seed", "e4")
    _write_seed(tmp_path / "public" / "collision.json", "Collision Seed", "d4")

    caplog.set_level(logging.WARNING)
    load_seed(session, tmp_path)

    opening = session.exec(
        select(Opening).where(Opening.name == "Collision Seed")
    ).one()
    row = session.exec(
        select(SeedImport).where(SeedImport.name == "Collision Seed")
    ).one()
    assert _first_child_san(session, opening.id) == "e4"
    assert row.file_key.startswith("private/")
    assert any(
        "duplicates opening" in record.message
        for record in caplog.records
    )


def test_write_seed_file_moves_visibility(
    session: Session,
    tmp_path: Path,
):
    opening = _create_opening(session, "Visibility Seed")

    public_path = write_seed_file(
        session, opening, "public", tmp_path
    )
    assert public_path.parent == tmp_path / "public"
    assert seed_visibility(opening.name, tmp_path) == "public"
    row = session.exec(
        select(SeedImport).where(SeedImport.name == opening.name)
    ).one()
    assert row.file_key == file_key(public_path, tmp_path)

    private_path = write_seed_file(
        session, opening, "private", tmp_path
    )
    assert private_path.parent == tmp_path / "private"
    assert not public_path.exists()
    assert seed_visibility(opening.name, tmp_path) == "private"
    row = session.exec(
        select(SeedImport).where(SeedImport.name == opening.name)
    ).one()
    assert row.file_key == file_key(private_path, tmp_path)
    assert len(find_seed_files(opening.name, tmp_path)) == 1
    assert len(session.exec(select(SeedImport)).all()) == 1


def test_private_gitignore_created_only_if_missing(
    session: Session,
    tmp_path: Path,
):
    opening = _create_opening(session, "Gitignore Seed")

    write_seed_file(session, opening, "private", tmp_path)
    gitignore = tmp_path / "private" / ".gitignore"
    assert gitignore.read_text(encoding="utf-8") == (
        "*\n!.gitignore\n!.gitkeep\n"
    )

    gitignore.write_text("custom\n", encoding="utf-8")
    write_seed_file(session, opening, "private", tmp_path)
    assert gitignore.read_text(encoding="utf-8") == "custom\n"


def test_gitignore_files_ignore_private_files():
    private_gitignore_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "seed_import"
        / "private"
        / ".gitignore"
    )
    root_candidates = [
        Path("/repo-root/.gitignore"),
        Path(__file__).resolve().parents[2] / ".gitignore",
    ]
    root_gitignore_path = next(
        (path for path in root_candidates if path.is_file()),
        None,
    )
    assert root_gitignore_path is not None

    private_lines = {
        line.strip()
        for line in private_gitignore_path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    }
    root_lines = {
        line.strip()
        for line in root_gitignore_path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    }
    assert private_lines == {"*", "!.gitignore", "!.gitkeep"}
    assert "backend/data/seed_import/private/*" in root_lines
    assert "!backend/data/seed_import/private/.gitkeep" in root_lines
    assert "backend/data/local/" in root_lines
