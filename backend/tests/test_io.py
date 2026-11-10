from fastapi.testclient import TestClient

BASE = "/api/openings"


def _create_opening(client: TestClient, name: str, color: str) -> int:
    response = client.post(BASE, json={"name": name, "color": color})
    assert response.status_code == 201
    return response.json()["id"]


def _add_move(client: TestClient, opening_id: int, parent_id: int, move: str) -> dict:
    response = client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": parent_id, "move": move},
    )
    assert response.status_code in (200, 201)
    return response.json()


def _make_tree(client: TestClient) -> int:
    opening_id = _create_opening(client, "IO Tree", "black")
    e4 = _add_move(client, opening_id, 1, "e4")["id"]
    _add_move(client, opening_id, 1, "d4")
    e5 = _add_move(client, opening_id, e4, "e5")["id"]
    _add_move(client, opening_id, e5, "Nf3")
    _add_move(client, opening_id, e5, "Bc4")
    return opening_id


def test_export(client: TestClient):
    opening_id = _make_tree(client)
    response = client.get(f"{BASE}/{opening_id}/export")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    data = response.json()
    assert data["format"] == "chess-openings-trainer"
    assert data["version"] == 1
    assert data["opening"]["name"] == "IO Tree"
    assert data["opening"]["color"] == "black"
    assert [c["san"] for c in data["opening"]["tree"]["children"]] == ["e4", "d4"]
    assert data["opening"]["tree"]["children"][0]["children"][0]["san"] == "e5"
    assert [c["san"] for c in data["opening"]["tree"]["children"][0]["children"][0]["children"]] == ["Nf3", "Bc4"]


def test_export_not_found(client: TestClient):
    response = client.get(f"{BASE}/9999/export")
    assert response.status_code == 404


def test_round_trip(client: TestClient):
    opening_id = _make_tree(client)
    exported = client.get(f"{BASE}/{opening_id}/export").json()

    assert client.delete(f"{BASE}/{opening_id}").status_code == 204

    response = client.post(f"{BASE}/import", json=exported)
    assert response.status_code == 201
    new_id = response.json()["id"]

    re_exported = client.get(f"{BASE}/{new_id}/export").json()
    assert re_exported == exported


def test_import_conflict_reject(client: TestClient):
    opening_id = _create_opening(client, "Conflict", "white")
    exported = client.get(f"{BASE}/{opening_id}/export").json()

    response = client.post(f"{BASE}/import", json=exported)
    assert response.status_code == 409


def test_import_conflict_replace(client: TestClient):
    opening_id = _create_opening(client, "Replace", "white")
    _add_move(client, opening_id, 1, "e4")
    exported = client.get(f"{BASE}/{opening_id}/export").json()

    response = client.post(f"{BASE}/import?on_conflict=replace", json=exported)
    assert response.status_code == 201
    assert response.json()["node_count"] == 2
    assert len(client.get(BASE).json()) == 1


def test_import_conflict_duplicate(client: TestClient):
    opening_id = _create_opening(client, "Dup", "white")
    exported = client.get(f"{BASE}/{opening_id}/export").json()

    first = client.post(f"{BASE}/import?on_conflict=duplicate", json=exported)
    assert first.status_code == 201
    assert first.json()["name"] == "Dup (2)"

    second = client.post(f"{BASE}/import?on_conflict=duplicate", json=exported)
    assert second.status_code == 201
    assert second.json()["name"] == "Dup (3)"


def test_import_invalid_json(client: TestClient):
    response = client.post(
        f"{BASE}/import",
        content="not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422

    response = client.post(f"{BASE}/import", json={"foo": "bar"})
    assert response.status_code == 422


def test_import_unknown_version(client: TestClient):
    opening_id = _create_opening(client, "Version", "white")
    data = client.get(f"{BASE}/{opening_id}/export").json()
    data["version"] = 2

    response = client.post(f"{BASE}/import", json=data)
    assert response.status_code == 422


def test_import_illegal_move(client: TestClient):
    opening_id = _create_opening(client, "Illegal Import", "white")
    data = client.get(f"{BASE}/{opening_id}/export").json()
    data["opening"]["tree"]["children"] = [
        {"san": "Nf9", "comment": None, "children": []}
    ]

    response = client.post(f"{BASE}/import", json=data)
    assert response.status_code == 422
    assert "1. Nf9" in response.json()["detail"]


def test_import_own_turn_multiple_moves(client: TestClient):
    opening_id = _create_opening(client, "Own Turn Import", "white")
    data = client.get(f"{BASE}/{opening_id}/export").json()
    data["opening"]["tree"]["children"] = [
        {"san": "e4", "comment": None, "children": []},
        {"san": "d4", "comment": None, "children": []},
    ]

    response = client.post(f"{BASE}/import", json=data)
    assert response.status_code == 422