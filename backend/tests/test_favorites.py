import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from models.opening import Opening
from utils.preferences import apply_favorites, read_favorites, write_favorites
from utils.seed import load_seed
from utils.seed_files import seed_file_path

BASE = "/api/openings"


@pytest.fixture
def favorites_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    from utils import preferences

    path = tmp_path / "local" / "favorites.json"
    monkeypatch.setattr(preferences, "FAVORITES_PATH", path)
    return path


@pytest.fixture
def seed_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    from utils import seed_files

    path = tmp_path / "seed"
    monkeypatch.setattr(seed_files, "SEED_IMPORT_DIR", path)
    return path


def _create_opening(
    client: TestClient,
    name: str,
    color: str = "white",
) -> dict:
    response = client.post(BASE, json={"name": name, "color": color})
    assert response.status_code == 201
    return response.json()


def _toggle(
    client: TestClient,
    opening_id: int,
    value: bool,
):
    return client.post(
        f"{BASE}/{opening_id}/favorite",
        json={"value": value},
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


def _write_seed(path: Path, name: str, move: str = "e4") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_seed_data(name, move), ensure_ascii=False),
        encoding="utf-8",
    )


def test_toggle_favorite_persists_file(
    client: TestClient,
    favorites_path: Path,
):
    opening = _create_opening(client, "Favorite A")

    response = _toggle(client, opening["id"], True)
    assert response.status_code == 200
    assert response.json()["is_favorite"] is True
    assert favorites_path.parent.is_dir()
    assert json.loads(favorites_path.read_text(encoding="utf-8")) == [
        "Favorite A"
    ]
    assert favorites_path.stat().st_mode & 0o777 == 0o600
    assert {path.name for path in favorites_path.parent.iterdir()} == {
        "favorites.json"
    }

    item = next(
        item for item in client.get(BASE).json()
        if item["id"] == opening["id"]
    )
    assert item["is_favorite"] is True

    response = _toggle(client, opening["id"], False)
    assert response.status_code == 200
    assert response.json()["is_favorite"] is False
    assert json.loads(favorites_path.read_text(encoding="utf-8")) == []

    assert _toggle(client, 9999, True).status_code == 404
    assert _toggle(client, opening["id"], "invalid").status_code == 422


def test_list_favorites_first_case_insensitive(
    client: TestClient,
    favorites_path: Path,
):
    ids = {
        name: _create_opening(client, name)["id"]
        for name in ("zulu", "Alpha", "beta", "Delta")
    }

    for name in ("zulu", "Alpha"):
        assert _toggle(client, ids[name], True).status_code == 200

    openings = client.get(BASE).json()

    assert [opening["name"] for opening in openings] == [
        "Alpha",
        "zulu",
        "beta",
        "Delta",
    ]
    assert [opening["is_favorite"] for opening in openings] == [
        True,
        True,
        False,
        False,
    ]


def test_apply_favorites_after_seed(
    session: Session,
    tmp_path: Path,
    favorites_path: Path,
):
    seed_root = tmp_path / "seed"
    _write_seed(seed_root / "public" / "one.json", "Seed One")
    _write_seed(seed_root / "private" / "two.json", "Seed Two", "d4")

    write_favorites(["Seed Two"], favorites_path)
    load_seed(session, seed_root)
    apply_favorites(session, favorites_path)

    openings = {
        opening.name: opening
        for opening in session.exec(select(Opening)).all()
    }
    assert openings["Seed One"].is_favorite is False
    assert openings["Seed Two"].is_favorite is True


def test_rename_favorite_updates_file(
    client: TestClient,
    favorites_path: Path,
):
    opening = _create_opening(client, "Old Favorite")
    assert _toggle(client, opening["id"], True).status_code == 200

    response = client.patch(
        f"{BASE}/{opening['id']}",
        json={"name": "New Favorite"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Favorite"
    assert response.json()["is_favorite"] is True
    assert read_favorites(favorites_path) == ["New Favorite"]


def test_corrupt_favorites_file_is_ignored(
    client: TestClient,
    session: Session,
    favorites_path: Path,
    caplog: pytest.LogCaptureFixture,
):
    opening = _create_opening(client, "Still Favorite")
    assert _toggle(client, opening["id"], True).status_code == 200
    favorites_path.write_text("not json", encoding="utf-8")

    caplog.set_level(logging.WARNING)
    apply_favorites(session, favorites_path)

    session.expire_all()
    stored = session.get(Opening, opening["id"])
    assert stored is not None
    assert stored.is_favorite is True
    assert any(
        "Could not parse favorites file" in record.message
        for record in caplog.records
    )


def test_export_and_seed_do_not_include_favorite(
    client: TestClient,
    favorites_path: Path,
    seed_dir: Path,
):
    opening = _create_opening(client, "No Favorite Export")
    assert _toggle(client, opening["id"], True).status_code == 200

    exported = client.get(f"{BASE}/{opening['id']}/export").json()
    assert "is_favorite" not in exported["opening"]

    response = client.post(
        f"{BASE}/{opening['id']}/seed",
        json={"visibility": "public"},
    )
    assert response.status_code == 200
    path = seed_file_path("No Favorite Export", seed_dir)
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert "is_favorite" not in stored["opening"]
