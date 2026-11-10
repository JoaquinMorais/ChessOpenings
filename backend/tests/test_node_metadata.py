from typing import Any

from fastapi.testclient import TestClient

BASE = "/api/openings"


def _create_opening(client: TestClient, name: str = "Node Metadata") -> int:
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


def _strip_metadata(node: dict[str, Any]) -> None:
    node.pop("name", None)
    node.pop("comment", None)
    for child in node.get("children", []):
        _strip_metadata(child)


def test_patch_node_name_and_comment(client: TestClient):
    opening_id = _create_opening(client)
    e4 = _add_move(client, opening_id, 1, "e4")

    response = client.patch(
        f"/api/nodes/{e4['id']}",
        json={"name": "Rama principal", "comment": "Comentario de prueba"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Rama principal"
    assert data["comment"] == "Comentario de prueba"

    tree = client.get(f"{BASE}/{opening_id}/tree").json()
    node = tree["children"][0]
    assert node["name"] == "Rama principal"
    assert node["comment"] == "Comentario de prueba"


def test_patch_only_sent_field(client: TestClient):
    opening_id = _create_opening(client)
    e4 = _add_move(client, opening_id, 1, "e4")

    client.patch(f"/api/nodes/{e4['id']}", json={"name": "Nombre"})
    response = client.patch(f"/api/nodes/{e4['id']}", json={"comment": "Solo comentario"})

    assert response.status_code == 200
    assert response.json()["name"] == "Nombre"
    assert response.json()["comment"] == "Solo comentario"


def test_patch_blank_values_become_null(client: TestClient):
    opening_id = _create_opening(client)
    e4 = _add_move(client, opening_id, 1, "e4")
    client.patch(
        f"/api/nodes/{e4['id']}",
        json={"name": "Nombre", "comment": "Comentario"},
    )

    response = client.patch(
        f"/api/nodes/{e4['id']}",
        json={"name": "   ", "comment": "   "},
    )

    assert response.status_code == 200
    assert response.json()["name"] is None
    assert response.json()["comment"] is None


def test_patch_name_too_long(client: TestClient):
    opening_id = _create_opening(client)
    e4 = _add_move(client, opening_id, 1, "e4")

    response = client.patch(f"/api/nodes/{e4['id']}", json={"name": "x" * 81})
    assert response.status_code == 422


def test_patch_not_found(client: TestClient):
    response = client.patch("/api/nodes/9999", json={"name": "Nombre"})
    assert response.status_code == 404


def test_patch_root_conflict(client: TestClient):
    opening_id = _create_opening(client)
    root_id = client.get(f"{BASE}/{opening_id}/tree").json()["id"]

    response = client.patch(f"/api/nodes/{root_id}", json={"name": "Raiz"})
    assert response.status_code == 409


def test_export_import_preserves_name_and_comment(client: TestClient):
    opening_id = _create_opening(client, "Metadata Round Trip")
    e4 = _add_move(client, opening_id, 1, "e4")
    e5 = _add_move(client, opening_id, e4["id"], "e5")

    client.patch(
        f"/api/nodes/{e4['id']}",
        json={"name": "Rama e4", "comment": "Comentario e4"},
    )
    client.patch(
        f"/api/nodes/{e5['id']}",
        json={"name": "Rama e5", "comment": "Comentario e5"},
    )

    exported = client.get(f"{BASE}/{opening_id}/export").json()
    assert client.delete(f"{BASE}/{opening_id}").status_code == 204

    response = client.post(f"{BASE}/import", json=exported)
    assert response.status_code == 201
    imported_id = response.json()["id"]

    tree = client.get(f"{BASE}/{imported_id}/tree").json()
    e4_node = tree["children"][0]
    assert e4_node["name"] == "Rama e4"
    assert e4_node["comment"] == "Comentario e4"
    assert e4_node["children"][0]["name"] == "Rama e5"
    assert e4_node["children"][0]["comment"] == "Comentario e5"

    re_exported = client.get(f"{BASE}/{imported_id}/export").json()
    assert re_exported == exported


def test_import_old_json_without_name_and_comment(client: TestClient):
    opening_id = _create_opening(client, "Old Import Format")
    _add_move(client, opening_id, 1, "e4")

    exported = client.get(f"{BASE}/{opening_id}/export").json()
    for child in exported["opening"]["tree"]["children"]:
        _strip_metadata(child)

    assert client.delete(f"{BASE}/{opening_id}").status_code == 204

    response = client.post(f"{BASE}/import", json=exported)
    assert response.status_code == 201
    imported_id = response.json()["id"]

    tree = client.get(f"{BASE}/{imported_id}/tree").json()
    node = tree["children"][0]
    assert node["name"] is None
    assert node["comment"] is None