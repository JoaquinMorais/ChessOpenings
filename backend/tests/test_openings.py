import pytest
from fastapi.testclient import TestClient

BASE = "/api/openings"


def test_list_openings_empty(client: TestClient):
    response = client.get(BASE)
    assert response.status_code == 200
    assert response.json() == []


def test_create_opening_happy(client: TestClient):
    response = client.post(BASE, json={"name": "Italian", "color": "white"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Italian"
    assert data["color"] == "white"
    assert data["node_count"] == 1
    assert data["accuracy"] is None


def test_create_opening_duplicate(client: TestClient):
    client.post(BASE, json={"name": "Italian", "color": "white"})
    response = client.post(BASE, json={"name": "Italian", "color": "black"})
    assert response.status_code == 409


def test_create_opening_invalid_color(client: TestClient):
    response = client.post(BASE, json={"name": "Italian", "color": "red"})
    assert response.status_code == 422


def test_list_openings_with_data(client: TestClient):
    client.post(BASE, json={"name": "Italian", "color": "white"})
    response = client.get(BASE)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_opening_happy(client: TestClient):
    created = client.post(BASE, json={"name": "Italian", "color": "white"}).json()
    response = client.get(f"{BASE}/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_opening_not_found(client: TestClient):
    response = client.get(f"{BASE}/9999")
    assert response.status_code == 404


def test_update_opening_happy(client: TestClient):
    created = client.post(BASE, json={"name": "Italian", "color": "white"}).json()
    response = client.patch(f"{BASE}/{created['id']}", json={"name": "Giuoco"})
    assert response.status_code == 200
    assert response.json()["name"] == "Giuoco"


def test_update_opening_duplicate(client: TestClient):
    first = client.post(BASE, json={"name": "Italian", "color": "white"}).json()
    client.post(BASE, json={"name": "Sicilian", "color": "black"})
    response = client.patch(f"{BASE}/{first['id']}", json={"name": "Sicilian"})
    assert response.status_code == 409


def test_update_opening_not_found(client: TestClient):
    response = client.patch(f"{BASE}/9999", json={"name": "X"})
    assert response.status_code == 404


def test_delete_opening_happy(client: TestClient):
    created = client.post(BASE, json={"name": "Italian", "color": "white"}).json()
    response = client.delete(f"{BASE}/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"{BASE}/{created['id']}").status_code == 404


def test_delete_opening_not_found(client: TestClient):
    response = client.delete(f"{BASE}/9999")
    assert response.status_code == 404