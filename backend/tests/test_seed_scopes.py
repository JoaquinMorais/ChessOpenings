import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from models.opening import Opening
from models.seed_import import SeedImport
from utils.seed import load_seed
from utils.seed_files import file_key, seed_file_path

BASE = "/api/openings"


@pytest.fixture
def seed_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from utils import seed_files

    monkeypatch.setattr(seed_files, "SEED_IMPORT_DIR", tmp_path)
    return tmp_path


def _create_seeded(
    client: TestClient,
    name: str,
    visibility: str = "public",
) -> tuple[dict, str]:
    opening = client.post(
        BASE, json={"name": name, "color": "white"}
    ).json()
    client.post(
        f"{BASE}/{opening['id']}/moves",
        json={"parent_id": 1, "move": "e4"},
    )
    response = client.post(
        f"{BASE}/{opening['id']}/seed",
        json={"visibility": visibility},
    )
    assert response.status_code == 200
    return opening, response.json()["path"]


def _write_new_seed(
    seed_dir: Path,
    name: str,
    move: str = "d4",
) -> str:
    path = seed_dir / "public" / "new-file.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
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
        ),
        encoding="utf-8",
    )
    return file_key(path, seed_dir)


def _seed_state(client: TestClient, key: str) -> str | None:
    files = client.get("/api/seed/files").json()
    item = next(
        (item for item in files if item["file_key"] == key),
        None,
    )
    return item["state"] if item else None


def test_delete_scope_local_keeps_file_and_registry(
    client: TestClient,
    session: Session,
    seed_dir: Path,
):
    opening, _ = _create_seeded(client, "Local Scope")
    path = seed_file_path("Local Scope", seed_dir)

    response = client.delete(
        f"{BASE}/{opening['id']}?scope=local"
    )
    assert response.status_code == 204
    assert client.get(f"{BASE}/{opening['id']}").status_code == 404
    assert path.is_file()
    assert session.exec(
        select(SeedImport).where(SeedImport.name == "Local Scope")
    ).first() is not None
    key = file_key(path, seed_dir)
    assert _seed_state(client, key) == "deleted_locally"

    load_seed(session, seed_dir)

    assert (
        session.exec(
            select(Opening).where(Opening.name == "Local Scope")
        ).first()
        is None
    )


def test_delete_scope_seed_keeps_opening_and_removes_file(
    client: TestClient,
    session: Session,
    seed_dir: Path,
):
    opening, _ = _create_seeded(client, "Seed Scope")
    path = seed_file_path("Seed Scope", seed_dir)

    response = client.delete(
        f"{BASE}/{opening['id']}?scope=seed"
    )
    assert response.status_code == 204
    assert client.get(f"{BASE}/{opening['id']}").status_code == 200
    assert not path.exists()
    assert session.exec(
        select(SeedImport).where(SeedImport.name == "Seed Scope")
    ).first() is None
    assert client.get(f"{BASE}/{opening['id']}").json()[
        "seed_visibility"
    ] is None


def test_delete_scope_both_removes_everything(
    client: TestClient,
    session: Session,
    seed_dir: Path,
):
    opening, _ = _create_seeded(client, "Both Scope")
    path = seed_file_path("Both Scope", seed_dir)

    response = client.delete(
        f"{BASE}/{opening['id']}?scope=both"
    )
    assert response.status_code == 204
    assert client.get(f"{BASE}/{opening['id']}").status_code == 404
    assert not path.exists()
    assert session.exec(
        select(SeedImport).where(SeedImport.name == "Both Scope")
    ).first() is None


@pytest.mark.parametrize("scope", ["local", "seed", "both", None])
def test_delete_scope_ignored_without_file(
    client: TestClient,
    scope: str | None,
):
    opening = client.post(
        BASE, json={"name": f"No File {scope}", "color": "white"}
    ).json()
    suffix = f"?scope={scope}" if scope else ""
    response = client.delete(f"{BASE}/{opening['id']}{suffix}")
    assert response.status_code == 204
    assert client.get(f"{BASE}/{opening['id']}").status_code == 404


def test_delete_file_without_scope_is_422(
    client: TestClient,
    seed_dir: Path,
):
    opening, _ = _create_seeded(client, "Needs Scope")

    response = client.delete(f"{BASE}/{opening['id']}")
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "alcance" in str(detail).lower()
    assert client.get(f"{BASE}/{opening['id']}").status_code == 200


def test_restore_deleted_locally(
    client: TestClient,
    seed_dir: Path,
):
    opening, _ = _create_seeded(client, "Restore Me")
    path = seed_file_path("Restore Me", seed_dir)
    key = file_key(path, seed_dir)
    assert client.delete(
        f"{BASE}/{opening['id']}?scope=local"
    ).status_code == 204
    assert _seed_state(client, key) == "deleted_locally"

    response = client.post("/api/seed/restore", json={"file_key": key})
    assert response.status_code == 201
    restored = response.json()
    assert restored["name"] == "Restore Me"
    assert restored["seed_visibility"] == "public"
    assert _seed_state(client, key) == "in_db"


def test_restore_new_file(
    client: TestClient,
    seed_dir: Path,
):
    key = _write_new_seed(seed_dir, "New File Opening")
    assert _seed_state(client, key) == "new"

    response = client.post("/api/seed/restore", json={"file_key": key})
    assert response.status_code == 201
    assert response.json()["name"] == "New File Opening"
    assert _seed_state(client, key) == "in_db"


def test_restore_collision_is_409(
    client: TestClient,
    seed_dir: Path,
):
    _write_new_seed(seed_dir, "Collision Restore")
    client.post(
        BASE, json={"name": "Collision Restore", "color": "white"}
    )
    key = file_key(seed_dir / "public" / "new-file.json", seed_dir)

    response = client.post("/api/seed/restore", json={"file_key": key})
    assert response.status_code == 409
    assert "Ya existe" in response.json()["detail"]


def test_restore_missing_file_is_404(client: TestClient, seed_dir: Path):
    response = client.post(
        "/api/seed/restore",
        json={"file_key": "public/does-not-exist.json"},
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "file_key_value",
    [
        "../outside.json",
        "public/../private/elephant-gambit.json",
        "private/sub/file.json",
        "other/file.json",
        "public/file.txt",
        "public/file.json/..",
    ],
)
def test_restore_rejects_path_traversal(
    client: TestClient,
    seed_dir: Path,
    file_key_value: str,
):
    response = client.post(
        "/api/seed/restore",
        json={"file_key": file_key_value},
    )
    assert response.status_code == 422
    assert "file_key" in response.json()["detail"].lower()
