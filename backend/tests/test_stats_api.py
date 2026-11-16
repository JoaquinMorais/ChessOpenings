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
        "sessions": [],
    }


def test_stats_opening_not_found(client: TestClient):
    response = client.get(f"{OPENINGS}/9999/stats")
    assert response.status_code == 404

def test_stats_only_completed_sessions_in_order(
    client: TestClient,
    session,
):
    from datetime import datetime, timezone

    from models.training import TrainingSession

    opening = client.post(
        OPENINGS, json={"name": "Stats Sessions", "color": "white"}
    ).json()
    base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    session.add(
        TrainingSession(
            opening_id=opening["id"],
            started_at=base,
            finished_at=base,
            questions_total=10,
            first_try_correct=8,
            state={},
        )
    )
    session.add(
        TrainingSession(
            opening_id=opening["id"],
            started_at=base,
            finished_at=None,
            questions_total=10,
            first_try_correct=1,
            state={},
        )
    )
    session.add(
        TrainingSession(
            opening_id=opening["id"],
            started_at=base,
            finished_at=base.replace(hour=13),
            questions_total=20,
            first_try_correct=10,
            state={},
        )
    )
    session.commit()

    response = client.get(f"{OPENINGS}/{opening['id']}/stats")
    assert response.status_code == 200
    sessions = response.json()["sessions"]
    assert [item["accuracy"] for item in sessions] == [80.0, 50.0]
    assert [item["first_try_correct"] for item in sessions] == [8, 10]
