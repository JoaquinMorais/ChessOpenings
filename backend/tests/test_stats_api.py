from fastapi.testclient import TestClient

OPENINGS = "/api/openings"


def test_stats_empty_opening(client: TestClient):
    opening = client.post(
        OPENINGS, json={"name": "Stats Empty", "color": "white"}
    ).json()

    response = client.get(f"{OPENINGS}/{opening['id']}/stats")
    assert response.status_code == 200
    assert response.json() == {
        "opening_id": opening["id"],
        "accuracy": None,
        "positions": [],
    }


def test_stats_opening_not_found(client: TestClient):
    response = client.get(f"{OPENINGS}/9999/stats")
    assert response.status_code == 404