from fastapi.testclient import TestClient


BASE = "/api/openings"


def _create_opening(client: TestClient, name: str, color: str) -> int:
    response = client.post(BASE, json={"name": name, "color": color})
    assert response.status_code == 201
    return response.json()["id"]


def test_illegal_move(client: TestClient):
    opening_id = _create_opening(client, "White Illegal", "white")
    response = client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": 1, "move": "e5"},
    )
    assert response.status_code == 422


def test_new_move_san(client: TestClient):
    opening_id = _create_opening(client, "White New", "white")
    response = client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": 1, "move": "e4"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["move_san"] == "e4"
    assert data["move_uci"] == "e2e4"
    assert data["ply"] == 1
    assert data["order_index"] == 0


def test_new_move_uci(client: TestClient):
    opening_id = _create_opening(client, "White UCI", "white")
    response = client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": 1, "move": "d2d4"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["move_san"] == "d4"
    assert data["move_uci"] == "d2d4"


def test_repeated_move(client: TestClient):
    opening_id = _create_opening(client, "White Repeat", "white")
    first = client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": 1, "move": "e4"},
    ).json()
    second = client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": 1, "move": "e4"},
    )
    assert second.status_code == 200
    assert second.json()["id"] == first["id"]


def test_multiple_rival_branches(client: TestClient):
    opening_id = _create_opening(client, "Black Branches", "black")
    for index, move in enumerate(["e4", "d4", "c4"]):
        response = client.post(
            f"{BASE}/{opening_id}/moves",
            json={"parent_id": 1, "move": move},
        )
        assert response.status_code == 201
        assert response.json()["order_index"] == index


def test_reject_second_own_move_at_root(client: TestClient):
    opening_id = _create_opening(client, "White Reject Root", "white")
    client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": 1, "move": "e4"},
    )
    response = client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": 1, "move": "d4"},
    )
    assert response.status_code == 409


def test_reject_second_own_move_after_rival(client: TestClient):
    opening_id = _create_opening(client, "Black Reject Own", "black")
    rival_move = client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": 1, "move": "e4"},
    ).json()
    child_id = rival_move["id"]
    client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": child_id, "move": "e5"},
    )
    response = client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": child_id, "move": "c5"},
    )
    assert response.status_code == 409


def test_black_opening_allows_multiple_root_moves(client: TestClient):
    opening_id = _create_opening(client, "Black Root", "black")
    first = client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": 1, "move": "e4"},
    )
    second = client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": 1, "move": "d4"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["order_index"] == 0
    assert second.json()["order_index"] == 1