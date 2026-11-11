import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from models.node import Node
from models.opening import Opening
from utils.openings import INITIAL_FEN
from utils.seed import load_seed
from utils.seed_files import (
    delete_seed_file,
    seed_file_exists,
    seed_file_path,
    slugify,
    write_seed_file,
)
from utils.tree import apply_move

BASE = "/api/openings"


def _create_opening(
    session: Session,
    name: str = "Seed Test",
    color: str = "white",
) -> tuple[Opening, Node]:
    opening = Opening(name=name, color=color)
    session.add(opening)
    session.commit()
    session.refresh(opening)
    root = Node(
        opening_id=opening.id,
        parent_id=None,
        fen=INITIAL_FEN,
        ply=0,
        order_index=0,
    )
    session.add(root)
    session.commit()
    session.refresh(root)
    return opening, root


def _add_move(
    session: Session,
    opening: Opening,
    parent: Node,
    san: str,
    order_index: int = 0,
    name: str | None = None,
    comment: str | None = None,
    classification: str | None = None,
    eval_cp: int | None = None,
    eval_mate: int | None = None,
) -> Node:
    result = apply_move(parent.fen, parent.ply, san)
    node = Node(
        opening_id=opening.id,
        parent_id=parent.id,
        move_san=result.san,
        move_uci=result.uci,
        fen=result.fen,
        ply=result.ply,
        order_index=order_index,
        name=name,
        comment=comment,
        classification=classification,
        eval_cp=eval_cp,
        eval_mate=eval_mate,
    )
    session.add(node)
    session.commit()
    session.refresh(node)
    return node


def test_slugify():
    assert slugify("Apertura Española: ¡Rey!") == "apertura-espanola-rey"
    assert slugify("  ---  ") == "opening"


def test_write_overwrite_delete_seed_file(session: Session, tmp_path: Path):
    opening, root = _create_opening(session, "Write Seed")
    _add_move(session, opening, root, "e4")

    path = write_seed_file(session, opening, tmp_path)
    assert path == seed_file_path("Write Seed", tmp_path)
    assert path.is_file()
    assert seed_file_exists("Write Seed", tmp_path)
    assert list(tmp_path.glob("*.tmp")) == []

    first = json.loads(path.read_text(encoding="utf-8"))
    assert first["opening"]["name"] == "Write Seed"
    assert len(first["opening"]["tree"]["children"]) == 1

    assert first["opening"]["tree"]["children"][0]["san"] == "e4"
    # Keep the same file name; overwrite by adding a new branch under e4.
    e4_node = session.exec(
        select(Node).where(
            Node.opening_id == opening.id,
            Node.move_uci == "e2e4",
        )
    ).one()
    _add_move(session, opening, e4_node, "e5", order_index=0)

    write_seed_file(session, opening, tmp_path)
    assert len(list(tmp_path.glob("*.json"))) == 1
    second = json.loads(path.read_text(encoding="utf-8"))
    assert len(second["opening"]["tree"]["children"][0]["children"]) == 1

    assert delete_seed_file("Write Seed", tmp_path) is True
    assert not path.exists()
    assert delete_seed_file("Write Seed", tmp_path) is False


def test_load_seed_import_creates_missing_openings(
    session: Session, tmp_path: Path
):
    opening, root = _create_opening(session, "External Seed")
    root.eval_cp = 20
    session.add(root)
    session.commit()
    session.refresh(root)
    _add_move(
        session,
        opening,
        root,
        "e4",
        name="Rama importada",
        comment="Comentario importado",
        classification="book",
        eval_cp=35,
    )
    write_seed_file(session, opening, tmp_path)
    expected = json.loads(
        seed_file_path("External Seed", tmp_path).read_text(encoding="utf-8")
    )

    session.delete(opening)
    session.commit()

    load_seed(session, tmp_path)

    imported = session.exec(
        select(Opening).where(Opening.name == "External Seed")
    ).one()
    assert imported.color == "white"
    imported_root = session.exec(
        select(Node).where(
            Node.opening_id == imported.id,
            Node.parent_id.is_(None),
        )
    ).one()
    assert imported_root.eval_cp == 20
    imported_node = session.exec(
        select(Node).where(
            Node.opening_id == imported.id,
            Node.move_uci == "e2e4",
        )
    ).one()
    assert imported_node.name == "Rama importada"
    assert imported_node.comment == "Comentario importado"
    assert imported_node.classification == "book"
    assert imported_node.eval_cp == 35

    from utils.opening_io import export_opening

    assert export_opening(session, imported.id) == expected


def test_load_seed_import_does_not_overwrite_existing(
    session: Session, tmp_path: Path
):
    existing, root = _create_opening(session, "Existing Seed")
    _add_move(session, existing, root, "e4")
    write_seed_file(session, existing, tmp_path)

    # The DB diverges after saving the file; load_seed must not overwrite it.
    _add_move(session, existing, root, "d4")
    node_count = len(
        session.exec(select(Node).where(Node.opening_id == existing.id)).all()
    )

    load_seed(session, tmp_path)

    session.refresh(existing)
    assert existing.name == "Existing Seed"
    assert (
        len(
            session.exec(
                select(Node).where(Node.opening_id == existing.id)
            ).all()
        )
        == node_count
    )


def test_load_seed_import_ignores_invalid_files(
    session: Session, tmp_path: Path
):
    (tmp_path / "broken.json").write_text("not json", encoding="utf-8")

    valid, root = _create_opening(session, "Valid External")
    _add_move(session, valid, root, "e4")
    write_seed_file(session, valid, tmp_path)
    session.delete(valid)
    session.commit()

    load_seed(session, tmp_path)

    loaded = session.exec(
        select(Opening).where(Opening.name == "Valid External")
    ).first()
    assert loaded is not None


@pytest.fixture
def seed_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from utils import seed_files

    monkeypatch.setattr(seed_files, "SEED_IMPORT_DIR", tmp_path)
    return tmp_path


def test_seed_endpoints_and_in_seed(client: TestClient, seed_dir: Path):
    opening = client.post(
        BASE, json={"name": "API Seed", "color": "white"}
    ).json()
    e4 = client.post(
        f"{BASE}/{opening['id']}/moves",
        json={"parent_id": 1, "move": "e4"},
    ).json()
    client.patch(
        f"/api/nodes/{e4['id']}",
        json={
            "name": "Rama API",
            "comment": "Comentario API",
            "classification": "mistake",
        },
    )

    response = client.post(f"{BASE}/{opening['id']}/seed")
    assert response.status_code == 200
    path = seed_file_path("API Seed", seed_dir)
    assert response.json() == {"path": f"data/seed_import/{path.name}"}
    assert path.is_file()
    assert seed_file_exists("API Seed", seed_dir)

    listed = client.get(BASE).json()
    item = next(item for item in listed if item["id"] == opening["id"])
    assert item["in_seed"] is True
    assert client.get(f"{BASE}/{opening['id']}").json()["in_seed"] is True

    response = client.delete(f"{BASE}/{opening['id']}/seed")
    assert response.status_code == 204
    assert not path.exists()
    item = next(
        item for item in client.get(BASE).json() if item["id"] == opening["id"]
    )
    assert item["in_seed"] is False


def test_seed_endpoints_not_found(client: TestClient, seed_dir: Path):
    assert client.post(f"{BASE}/9999/seed").status_code == 404
    assert client.delete(f"{BASE}/9999/seed").status_code == 404


def test_rename_keeps_old_seed_file(client: TestClient, seed_dir: Path):
    opening = client.post(
        BASE, json={"name": "Old Seed Name", "color": "white"}
    ).json()
    assert client.post(f"{BASE}/{opening['id']}/seed").status_code == 200
    old_path = seed_file_path("Old Seed Name", seed_dir)
    assert old_path.is_file()

    response = client.patch(
        f"{BASE}/{opening['id']}",
        json={"name": "New Seed Name"},
    )
    assert response.status_code == 200
    assert old_path.is_file()
    assert not seed_file_path("New Seed Name", seed_dir).exists()
    assert response.json()["in_seed"] is False