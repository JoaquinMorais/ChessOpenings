from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from config.settings import settings
from routes import recommendations as recommendation_routes
from utils.recommenders import StockfishRecommender
from utils.recommendations import RecommendationError


def _create_opening(client: TestClient) -> tuple[int, int]:
    opening = client.post(
        "/api/openings",
        json={"name": "Recommendations", "color": "white"},
    ).json()
    tree = client.get(f"/api/openings/{opening['id']}/tree").json()
    return opening["id"], tree["id"]


def test_recommendations_endpoint(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    _, root_id = _create_opening(client)

    def fake_recommendations(fen: str):
        return [
            {
                "rank": 1,
                "uci": "e2e4",
                "san": "e4",
                "evaluation": {"cp": 35},
                "depth": 20,
            },
            {
                "rank": 2,
                "uci": "d2d4",
                "san": "d4",
                "evaluation": {"cp": 28},
                "depth": 20,
            },
            {
                "rank": 3,
                "uci": "c2c4",
                "san": "c4",
                "evaluation": {"cp": 20},
                "depth": 20,
            },
        ]

    monkeypatch.setattr(
        recommendation_routes,
        "get_recommendations",
        fake_recommendations,
    )
    response = client.get(f"/api/nodes/{root_id}/recommendations")
    assert response.status_code == 200
    payload = response.json()
    assert payload["node_id"] == root_id
    assert payload["side_to_move"] == "white"
    assert [move["san"] for move in payload["moves"]] == ["e4", "d4", "c4"]
    assert payload["moves"][0]["evaluation"] == {
        "cp": 35,
        "source": "engine",
    }


def test_recommendations_endpoint_404(client: TestClient):
    response = client.get("/api/nodes/9999/recommendations")
    assert response.status_code == 404
    assert "nodo" in response.json()["detail"]


def test_recommendations_endpoint_stockfish_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    _, root_id = _create_opening(client)

    def fail(_fen: str):
        raise RecommendationError("Stockfish no disponible.")

    monkeypatch.setattr(
        recommendation_routes,
        "get_recommendations",
        fail,
    )
    response = client.get(f"/api/nodes/{root_id}/recommendations")
    assert response.status_code == 503
    assert "Stockfish" in response.json()["detail"]


@pytest.mark.skipif(
    not Path(settings.stockfish_path).is_file(),
    reason="Stockfish binary not available",
)
def test_stockfish_recommender_returns_three_lines():
    recommender = StockfishRecommender(settings.stockfish_path, 100)
    try:
        moves = recommender.recommend(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        )
    finally:
        recommender.close()

    assert len(moves) == 3
    assert [move["rank"] for move in moves] == [1, 2, 3]
    assert all(move["uci"] and move["san"] for move in moves)
    assert all(move["evaluation"] for move in moves)
