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


def test_tree_multilevel(client: TestClient):
    opening_id = _create_opening(client, "Tree Multi", "black")
    e4 = _add_move(client, opening_id, 1, "e4")["id"]
    _add_move(client, opening_id, 1, "d4")
    e5 = _add_move(client, opening_id, e4, "e5")["id"]
    _add_move(client, opening_id, e5, "Nf3")
    _add_move(client, opening_id, e5, "Bc4")

    response = client.get(f"{BASE}/{opening_id}/tree")
    assert response.status_code == 200
    tree = response.json()
    assert tree["san"] is None
    assert [child["uci"] for child in tree["children"]] == ["e2e4", "d2d4"]
    e4_node = tree["children"][0]
    assert [child["uci"] for child in e4_node["children"]] == ["e7e5"]
    assert [child["san"] for child in e4_node["children"][0]["children"]] == ["Nf3", "Bc4"]


def test_delete_subtree(client: TestClient):
    opening_id = _create_opening(client, "Tree Delete", "black")
    e4 = _add_move(client, opening_id, 1, "e4")["id"]
    e5 = _add_move(client, opening_id, e4, "e5")["id"]
    _add_move(client, opening_id, e5, "Nf3")
    _add_move(client, opening_id, 1, "d4")

    response = client.delete(f"/api/nodes/{e4}")
    assert response.status_code == 204

    tree = client.get(f"{BASE}/{opening_id}/tree").json()
    assert len(tree["children"]) == 1
    assert tree["children"][0]["uci"] == "d2d4"
    assert tree["children"][0]["order_index"] == 0

    # El subarbol borrado ya no existe.
    assert client.delete(f"/api/nodes/{e5}").status_code == 404


def test_delete_root_error(client: TestClient):
    opening_id = _create_opening(client, "Tree Root", "white")
    response = client.delete("/api/nodes/1")
    assert response.status_code == 409


def test_make_main(client: TestClient):
    opening_id = _create_opening(client, "Tree Main", "black")
    _add_move(client, opening_id, 1, "e4")
    _add_move(client, opening_id, 1, "d4")
    c4 = _add_move(client, opening_id, 1, "c4")["id"]

    response = client.post(f"/api/nodes/{c4}/make-main")
    assert response.status_code == 200

    tree = client.get(f"{BASE}/{opening_id}/tree").json()
    assert [child["uci"] for child in tree["children"]] == ["c2c4", "e2e4", "d2d4"]


def test_tree_not_found(client: TestClient):
    response = client.get(f"{BASE}/9999/tree")
    assert response.status_code == 404

def test_normalize_fen_ignores_move_counters():
    from utils.tree import normalize_fen

    left = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    right = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 8 42"

    assert normalize_fen(left) == normalize_fen(right)
