from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from models.seed_import import SeedImport
from utils.opening_io import import_opening
from utils.seed_files import (
    delete_seed_file,
    file_key,
    seed_file_exists,
    seed_file_path,
    seed_visibility,
    write_seed_file,
)

BASE = "/api/openings"


def _seed_data(name: str) -> dict:
    return {
        "format": "chess-openings-trainer",
        "version": 1,
        "opening": {
            "name": name,
            "color": "white",
            "tree": {
                "children": [
                    {
                        "san": "e4",
                        "comment": None,
                        "children": [],
                    }
                ]
            },
        },
    }


def _add_move(
    client: TestClient,
    opening_id: int,
    parent_id: int,
    move: str,
) -> dict:
    response = client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": parent_id, "move": move},
    )
    assert response.status_code in (200, 201)
    return response.json()


@pytest.fixture
def seed_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from utils import seed_files

    monkeypatch.setattr(seed_files, "SEED_IMPORT_DIR", tmp_path)
    return tmp_path


def test_write_move_delete_seed_file(session: Session, seed_dir: Path):
    opening = import_opening(session, _seed_data("Write Seed"))
    path = write_seed_file(session, opening, "public", seed_dir)

    assert path.parent == seed_dir / "public"
    assert path.is_file()
    assert seed_visibility(opening.name, seed_dir) == "public"
    assert seed_file_exists(opening.name, seed_dir)
    assert list(seed_dir.glob("**/*.tmp")) == []

    row = session.exec(
        select(SeedImport).where(SeedImport.name == opening.name)
    ).one()
    assert row.file_key == file_key(path, seed_dir)

    private_path = write_seed_file(session, opening, "private", seed_dir)
    assert not path.exists()
    assert private_path.parent == seed_dir / "private"
    assert seed_visibility(opening.name, seed_dir) == "private"
    row = session.exec(
        select(SeedImport).where(SeedImport.name == opening.name)
    ).one()
    assert row.file_key == file_key(private_path, seed_dir)

    assert delete_seed_file(session, opening.name, seed_dir) is True
    assert not private_path.exists()
    assert session.exec(
        select(SeedImport).where(SeedImport.name == opening.name)
    ).first() is None
    assert delete_seed_file(session, opening.name, seed_dir) is False


def test_seed_endpoints_and_visibility(
    client: TestClient,
    seed_dir: Path,
):
    opening = client.post(
        BASE, json={"name": "API Seed", "color": "white"}
    ).json()
    _add_move(client, opening["id"], 1, "e4")

    response = client.post(
        f"{BASE}/{opening['id']}/seed",
        json={"visibility": "public"},
    )
    assert response.status_code == 200
    public_path = seed_file_path("API Seed", seed_dir)
    assert response.json() == {
        "path": f"data/seed_import/public/{public_path.name}"
    }
    assert public_path.is_file()

    item = next(
        item
        for item in client.get(BASE).json()
        if item["id"] == opening["id"]
    )
    assert item["in_seed"] is True
    assert item["seed_visibility"] == "public"

    response = client.post(
        f"{BASE}/{opening['id']}/seed",
        json={"visibility": "private"},
    )
    assert response.status_code == 200
    private_path = seed_file_path("API Seed", seed_dir)
    assert private_path.parent == seed_dir / "private"
    assert not public_path.exists()
    assert (seed_dir / "private" / ".gitignore").is_file()

    item = next(
        item
        for item in client.get(BASE).json()
        if item["id"] == opening["id"]
    )
    assert item["in_seed"] is True
    assert item["seed_visibility"] == "private"

    response = client.delete(f"{BASE}/{opening['id']}/seed")
    assert response.status_code == 204
    assert not private_path.exists()
    assert (
        client.get(f"{BASE}/{opening['id']}").json()["seed_visibility"]
        is None
    )


def test_save_seed_requires_visibility(
    client: TestClient,
    seed_dir: Path,
):
    opening = client.post(
        BASE, json={"name": "No Visibility", "color": "white"}
    ).json()

    assert (
        client.post(f"{BASE}/{opening['id']}/seed").status_code == 422
    )
    assert (
        client.post(
            f"{BASE}/{opening['id']}/seed",
            json={"visibility": "invalid"},
        ).status_code
        == 422
    )


def test_seed_endpoints_not_found(
    client: TestClient,
    seed_dir: Path,
):
    assert (
        client.post(
            f"{BASE}/9999/seed",
            json={"visibility": "public"},
        ).status_code
        == 404
    )
    assert client.delete(f"{BASE}/9999/seed").status_code == 404


def test_rename_keeps_old_seed_file(
    client: TestClient,
    seed_dir: Path,
):
    opening = client.post(
        BASE, json={"name": "Old Seed Name", "color": "white"}
    ).json()
    response = client.post(
        f"{BASE}/{opening['id']}/seed",
        json={"visibility": "public"},
    )
    assert response.status_code == 200
    old_path = seed_file_path("Old Seed Name", seed_dir)
    assert old_path.is_file()

    response = client.patch(
        f"{BASE}/{opening['id']}",
        json={"name": "New Seed Name"},
    )
    assert response.status_code == 200
    assert old_path.is_file()
    assert not seed_file_path("New Seed Name", seed_dir).exists()
    assert seed_visibility("New Seed Name", seed_dir) is None
    assert response.json()["seed_visibility"] is None
