from fastapi.testclient import TestClient

BASE = "/api/openings"

EXPECTED_CLASSIFICATIONS = [
    {"key": "brilliant", "label": "Brillante", "symbol": "!!", "color": "#1baca6"},
    {"key": "great", "label": "Gran jugada", "symbol": "!", "color": "#5c8bb0"},
    {"key": "best", "label": "Mejor jugada", "symbol": "★", "color": "#96bc4b"},
    {"key": "excellent", "label": "Excelente", "symbol": "✓", "color": "#81b64c"},
    {"key": "good", "label": "Buena", "symbol": "•", "color": "#a0b090"},
    {"key": "book", "label": "De libro", "symbol": "B", "color": "#a88865"},
    {"key": "inaccuracy", "label": "Imprecision", "symbol": "?!", "color": "#f7c631"},
    {"key": "mistake", "label": "Error", "symbol": "?", "color": "#e58f2a"},
    {"key": "miss", "label": "Oportunidad perdida", "symbol": "✗", "color": "#ff7769"},
    {"key": "blunder", "label": "Error grave", "symbol": "??", "color": "#ca3431"},
]


def _create_opening(client: TestClient, name: str = "Classifications") -> int:
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


def _strip_classification(node: dict) -> None:
    node.pop("classification", None)
    for child in node.get("children", []):
        _strip_classification(child)


def test_patch_classification_and_tree(client: TestClient):
    opening_id = _create_opening(client)
    e4 = _add_move(client, opening_id, 1, "e4")

    response = client.patch(
        f"/api/nodes/{e4['id']}",
        json={"classification": "brilliant"},
    )
    assert response.status_code == 200
    assert response.json()["classification"] == "brilliant"

    tree = client.get(f"{BASE}/{opening_id}/tree").json()
    assert tree["children"][0]["classification"] == "brilliant"


def test_patch_remove_classification(client: TestClient):
    opening_id = _create_opening(client)
    e4 = _add_move(client, opening_id, 1, "e4")

    client.patch(f"/api/nodes/{e4['id']}", json={"classification": "book"})
    response = client.patch(
        f"/api/nodes/{e4['id']}",
        json={"classification": None},
    )
    assert response.status_code == 200
    assert response.json()["classification"] is None

    client.patch(f"/api/nodes/{e4['id']}", json={"classification": "mistake"})
    response = client.patch(
        f"/api/nodes/{e4['id']}",
        json={"classification": ""},
    )
    assert response.status_code == 200
    assert response.json()["classification"] is None


def test_patch_invalid_classification(client: TestClient):
    opening_id = _create_opening(client)
    e4 = _add_move(client, opening_id, 1, "e4")

    response = client.patch(
        f"/api/nodes/{e4['id']}",
        json={"classification": "unknown"},
    )
    assert response.status_code == 422
    assert "no es valida" in response.json()["detail"]


def test_patch_root_classification_conflict(client: TestClient):
    opening_id = _create_opening(client)
    root_id = client.get(f"{BASE}/{opening_id}/tree").json()["id"]

    response = client.patch(
        f"/api/nodes/{root_id}",
        json={"classification": "book"},
    )
    assert response.status_code == 409


def test_export_import_preserves_classification(client: TestClient):
    opening_id = _create_opening(client, "Classification Round Trip")
    e4 = _add_move(client, opening_id, 1, "e4")
    e5 = _add_move(client, opening_id, e4["id"], "e5")

    client.patch(f"/api/nodes/{e4['id']}", json={"classification": "book"})
    client.patch(f"/api/nodes/{e5['id']}", json={"classification": "mistake"})

    exported = client.get(f"{BASE}/{opening_id}/export").json()
    assert client.delete(f"{BASE}/{opening_id}").status_code == 204

    response = client.post(f"{BASE}/import", json=exported)
    assert response.status_code == 201
    imported_id = response.json()["id"]

    tree = client.get(f"{BASE}/{imported_id}/tree").json()
    assert tree["children"][0]["classification"] == "book"
    assert tree["children"][0]["children"][0]["classification"] == "mistake"

    re_exported = client.get(f"{BASE}/{imported_id}/export").json()
    assert re_exported == exported


def test_import_unknown_classification(client: TestClient):
    opening_id = _create_opening(client, "Bad Classification")
    _add_move(client, opening_id, 1, "e4")
    exported = client.get(f"{BASE}/{opening_id}/export").json()
    exported["opening"]["tree"]["children"][0]["classification"] = "unknown"

    response = client.post(f"{BASE}/import", json=exported)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "1. e4" in detail
    assert "unknown" in detail


def test_import_old_json_without_classification(client: TestClient):
    opening_id = _create_opening(client, "Old Classification Format")
    _add_move(client, opening_id, 1, "e4")
    exported = client.get(f"{BASE}/{opening_id}/export").json()
    for child in exported["opening"]["tree"]["children"]:
        _strip_classification(child)

    assert client.delete(f"{BASE}/{opening_id}").status_code == 204

    response = client.post(f"{BASE}/import", json=exported)
    assert response.status_code == 201
    imported_id = response.json()["id"]

    tree = client.get(f"{BASE}/{imported_id}/tree").json()
    assert tree["children"][0]["classification"] is None


def test_classifications_meta_endpoint(client: TestClient):
    response = client.get("/api/meta/classifications")
    assert response.status_code == 200
    assert response.json() == EXPECTED_CLASSIFICATIONS