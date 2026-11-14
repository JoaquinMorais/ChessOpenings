from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from models.node import Node
from models.opening import Opening
from utils.openings import INITIAL_FEN

BASE = "/api/openings"


def _create_opening(client: TestClient, name: str = "Evaluation") -> int:
    response = client.post(BASE, json={"name": name, "color": "white"})
    assert response.status_code == 201
    return response.json()["id"]


def _add_move(client: TestClient, opening_id: int, parent_id: int, move: str) -> dict:
    response = client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": parent_id, "move": move},
    )
    assert response.status_code in (200, 201)
    return response.json()


def _detail(response) -> str:
    detail = response.json()["detail"]
    if isinstance(detail, list):
        return " ".join(
            str(item.get("msg", ""))
            for item in detail
            if isinstance(item, dict)
        )
    return str(detail)


def _patch_evaluation(client: TestClient, node_id: int, evaluation: Any):
    return client.patch(
        f"/api/nodes/{node_id}",
        json={"evaluation": evaluation},
    )


def test_patch_evaluation_cp_and_mate(
    client: TestClient, session: Session
):
    opening_id = _create_opening(client)
    e4 = _add_move(client, opening_id, 1, "e4")

    response = _patch_evaluation(client, e4["id"], {"cp": 35})
    assert response.status_code == 200
    assert response.json()["evaluation"] == {"cp": 35, "source": "manual"}

    stored = session.get(Node, e4["id"])
    assert stored.eval_cp == 35
    assert stored.eval_mate is None
    assert stored.eval_source == "manual"

    response = _patch_evaluation(client, e4["id"], {"mate": 3})
    assert response.status_code == 200
    assert response.json()["evaluation"] == {"mate": 3, "source": "manual"}

    session.refresh(stored)
    assert stored.eval_cp is None
    assert stored.eval_mate == 3


def test_patch_evaluation_null_clears(client: TestClient, session: Session):
    opening_id = _create_opening(client)
    e4 = _add_move(client, opening_id, 1, "e4")
    _patch_evaluation(client, e4["id"], {"cp": 12})

    response = _patch_evaluation(client, e4["id"], None)
    assert response.status_code == 200
    assert response.json()["evaluation"] is None

    stored = session.get(Node, e4["id"])
    assert stored.eval_cp is None
    assert stored.eval_mate is None
    assert stored.eval_source is None


@pytest.mark.parametrize(
    ("evaluation", "expected"),
    [
        ({"cp": 1, "mate": 2}, "exactamente una"),
        ({"cp": 10000}, "cp"),
        ({"cp": -10000}, "cp"),
        ({"mate": 0}, "mate"),
        ({"mate": 100}, "mate"),
        ({}, "exactamente una"),
        ({"cp": None}, "cp"),
        ({"cp": "35"}, "entero"),
        ({"mate": 1.5}, "entero"),
        ({"cp": 1, "foo": 2}, "solo admite"),
    ],
)
def test_patch_invalid_evaluation(
    client: TestClient, evaluation: dict, expected: str
):
    opening_id = _create_opening(client)
    e4 = _add_move(client, opening_id, 1, "e4")

    response = _patch_evaluation(client, e4["id"], evaluation)
    assert response.status_code == 422
    assert expected in _detail(response)


def test_patch_root_evaluation_allowed(client: TestClient):
    opening_id = _create_opening(client)
    root_id = client.get(f"{BASE}/{opening_id}/tree").json()["id"]

    response = _patch_evaluation(client, root_id, {"cp": 20})
    assert response.status_code == 200
    assert response.json()["evaluation"] == {"cp": 20, "source": "manual"}

    tree = client.get(f"{BASE}/{opening_id}/tree").json()
    assert tree["evaluation"] == {"cp": 20, "source": "manual"}

    response = _patch_evaluation(client, root_id, {"mate": 2})
    assert response.status_code == 200
    assert response.json()["evaluation"] == {"mate": 2, "source": "manual"}


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Raiz"},
        {"comment": "Raiz"},
        {"classification": "book"},
        {"name": "Raiz", "evaluation": {"cp": 1}},
        {},
    ],
)
def test_patch_root_metadata_still_conflict(
    client: TestClient, payload: dict
):
    opening_id = _create_opening(client)
    root_id = client.get(f"{BASE}/{opening_id}/tree").json()["id"]

    response = client.patch(f"/api/nodes/{root_id}", json=payload)
    assert response.status_code == 409


def test_patch_only_sent_fields_keeps_evaluation(client: TestClient):
    opening_id = _create_opening(client)
    e4 = _add_move(client, opening_id, 1, "e4")
    _patch_evaluation(client, e4["id"], {"cp": 35})

    response = client.patch(
        f"/api/nodes/{e4['id']}",
        json={"name": "Rama", "comment": "Comentario"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Rama"
    assert data["comment"] == "Comentario"
    assert data["evaluation"] == {"cp": 35, "source": "manual"}


def test_tree_includes_evaluation(client: TestClient):
    opening_id = _create_opening(client)
    root_id = client.get(f"{BASE}/{opening_id}/tree").json()["id"]
    e4 = _add_move(client, opening_id, 1, "e4")
    _patch_evaluation(client, root_id, {"cp": 20})
    _patch_evaluation(client, e4["id"], {"mate": 1})

    tree = client.get(f"{BASE}/{opening_id}/tree").json()
    assert tree["evaluation"] == {"cp": 20, "source": "manual"}
    assert tree["children"][0]["evaluation"] == {"mate": 1, "source": "manual"}


def test_export_import_round_trip_with_evaluation(client: TestClient):
    opening_id = _create_opening(client, "Evaluation Round Trip")
    root_id = client.get(f"{BASE}/{opening_id}/tree").json()["id"]
    e4 = _add_move(client, opening_id, 1, "e4")
    e5 = _add_move(client, opening_id, e4["id"], "e5")
    _patch_evaluation(client, root_id, {"cp": 20})
    _patch_evaluation(client, e4["id"], {"mate": 1})
    _patch_evaluation(client, e5["id"], {"cp": 15})

    exported = client.get(f"{BASE}/{opening_id}/export").json()
    assert exported["opening"]["tree"]["evaluation"] == {"cp": 20, "source": "manual"}
    assert (
        exported["opening"]["tree"]["children"][0]["evaluation"]
        == {"mate": 1, "source": "manual"}
    )

    assert client.delete(f"{BASE}/{opening_id}").status_code == 204
    response = client.post(f"{BASE}/import", json=exported)
    assert response.status_code == 201
    imported_id = response.json()["id"]

    tree = client.get(f"{BASE}/{imported_id}/tree").json()
    assert tree["evaluation"] == {"cp": 20, "source": "manual"}
    assert tree["children"][0]["evaluation"] == {"mate": 1, "source": "manual"}
    assert tree["children"][0]["children"][0]["evaluation"] == {"cp": 15, "source": "manual"}

    re_exported = client.get(f"{BASE}/{imported_id}/export").json()
    assert re_exported == exported


def test_import_old_json_without_evaluation(client: TestClient):
    opening_id = _create_opening(client, "Old Evaluation Format")
    e4 = _add_move(client, opening_id, 1, "e4")
    _patch_evaluation(client, e4["id"], {"cp": 35})

    exported = client.get(f"{BASE}/{opening_id}/export").json()
    exported["opening"]["tree"].pop("evaluation")
    exported["opening"]["tree"]["children"][0].pop("evaluation")

    assert client.delete(f"{BASE}/{opening_id}").status_code == 204
    response = client.post(f"{BASE}/import", json=exported)
    assert response.status_code == 201
    imported_id = response.json()["id"]

    tree = client.get(f"{BASE}/{imported_id}/tree").json()
    assert tree["evaluation"] is None
    assert tree["children"][0]["evaluation"] is None


def test_import_invalid_evaluation(client: TestClient):
    opening_id = _create_opening(client, "Invalid Evaluation")
    e4 = _add_move(client, opening_id, 1, "e4")
    _patch_evaluation(client, e4["id"], {"cp": 35})
    exported = client.get(f"{BASE}/{opening_id}/export").json()

    exported["opening"]["tree"]["children"][0]["evaluation"] = {
        "cp": 1,
        "mate": 2,
    }
    response = client.post(f"{BASE}/import?on_conflict=duplicate", json=exported)
    assert response.status_code == 422
    assert "1. e4" in response.json()["detail"]
    assert "exactamente una" in response.json()["detail"]

    exported["opening"]["tree"]["children"][0].pop("evaluation")
    exported["opening"]["tree"]["evaluation"] = {"mate": 0}
    response = client.post(f"{BASE}/import?on_conflict=duplicate", json=exported)
    assert response.status_code == 422
    assert "posicion inicial" in response.json()["detail"]


def test_check_constraint_rejects_both_evaluations(session: Session):
    opening = Opening(name="Constraint", color="white")
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

    invalid = Node(
        opening_id=opening.id,
        parent_id=root.id,
        move_san="e4",
        move_uci="e2e4",
        fen=INITIAL_FEN,
        ply=1,
        eval_cp=1,
        eval_mate=1,
    )
    session.add(invalid)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_patch_evaluation_source_is_forced_to_manual(
    client: TestClient, session: Session
):
    opening_id = _create_opening(client, "Source Patch")
    e4 = _add_move(client, opening_id, 1, "e4")

    response = _patch_evaluation(
        client,
        e4["id"],
        {"cp": 10, "source": "engine"},
    )
    assert response.status_code == 200
    assert response.json()["evaluation"] == {"cp": 10, "source": "manual"}

    stored = session.get(Node, e4["id"])
    assert stored is not None
    assert stored.eval_source == "manual"


def test_import_preserves_engine_source(client: TestClient):
    opening_id = _create_opening(client, "Source Import")
    e4 = _add_move(client, opening_id, 1, "e4")
    _patch_evaluation(client, e4["id"], {"cp": 35})
    exported = client.get(f"{BASE}/{opening_id}/export").json()
    exported["opening"]["tree"]["children"][0]["evaluation"] = {
        "cp": 35,
        "source": "engine",
    }

    response = client.post(
        f"{BASE}/import?on_conflict=duplicate",
        json=exported,
    )
    assert response.status_code == 201
    imported_id = response.json()["id"]
    tree = client.get(f"{BASE}/{imported_id}/tree").json()
    assert tree["children"][0]["evaluation"] == {
        "cp": 35,
        "source": "engine",
    }


def test_import_rejects_invalid_source(client: TestClient):
    opening_id = _create_opening(client, "Invalid Source")
    e4 = _add_move(client, opening_id, 1, "e4")
    _patch_evaluation(client, e4["id"], {"cp": 35})
    exported = client.get(f"{BASE}/{opening_id}/export").json()
    exported["opening"]["tree"]["children"][0]["evaluation"]["source"] = "robot"

    response = client.post(
        f"{BASE}/import?on_conflict=duplicate",
        json=exported,
    )
    assert response.status_code == 422
    assert "1. e4" in response.json()["detail"]


def test_import_normalizes_terminal_mate_zero(client: TestClient):
    opening_id = _create_opening(client, "Mate Zero Import")
    root_id = client.get(f"{BASE}/{opening_id}/tree").json()["id"]
    parent_id = root_id
    for move in ("f3", "e5", "g4", "Qh4#"):
        node = _add_move(client, opening_id, parent_id, move)
        parent_id = node["id"]

    exported = client.get(f"{BASE}/{opening_id}/export").json()
    exported["opening"]["tree"]["children"][0]["children"][0][
        "children"
    ][0]["children"][0]["evaluation"] = {
        "mate": 0,
        "source": "engine",
    }

    assert client.delete(f"{BASE}/{opening_id}").status_code == 204
    response = client.post(
        f"{BASE}/import?on_conflict=duplicate",
        json=exported,
    )
    assert response.status_code == 201
    imported_id = response.json()["id"]
    tree = client.get(f"{BASE}/{imported_id}/tree").json()
    final = tree["children"][0]["children"][0]["children"][0][
        "children"
    ][0]
    assert final["evaluation"] == {"cp": -9999, "source": "engine"}


def test_legacy_mate_zero_node_is_read_as_cp(
    client: TestClient,
    session: Session,
):
    opening_id = _create_opening(client, "Legacy Mate Zero")
    e4 = _add_move(client, opening_id, 1, "e4")
    node = session.get(Node, e4["id"])
    node.eval_mate = 0
    node.eval_source = "engine"
    session.add(node)
    session.commit()

    tree = client.get(f"{BASE}/{opening_id}/tree").json()
    assert tree["children"][0]["evaluation"] == {
        "cp": 9999,
        "source": "engine",
    }
