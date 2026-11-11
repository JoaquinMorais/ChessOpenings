from fastapi.testclient import TestClient

OPENINGS = "/api/openings"
SESSIONS = "/api/training/sessions"


def _create_linear_opening(client: TestClient):
    opening = client.post(
        OPENINGS, json={"name": "Training API", "color": "white"}
    ).json()
    opening_id = opening["id"]

    root_id = 1
    e4 = client.post(
        f"{OPENINGS}/{opening_id}/moves",
        json={"parent_id": root_id, "move": "e4"},
    ).json()
    e5 = client.post(
        f"{OPENINGS}/{opening_id}/moves",
        json={"parent_id": e4["id"], "move": "e5"},
    ).json()
    nf3 = client.post(
        f"{OPENINGS}/{opening_id}/moves",
        json={"parent_id": e5["id"], "move": "Nf3"},
    ).json()
    nc6 = client.post(
        f"{OPENINGS}/{opening_id}/moves",
        json={"parent_id": nf3["id"], "move": "Nc6"},
    ).json()
    bc4 = client.post(
        f"{OPENINGS}/{opening_id}/moves",
        json={"parent_id": nc6["id"], "move": "Bc4"},
    ).json()

    return opening_id, {
        "root": root_id,
        "e4": e4["id"],
        "e5": e5["id"],
        "nf3": nf3["id"],
        "nc6": nc6["id"],
        "bc4": bc4["id"],
    }


def test_full_training_flow(client: TestClient):
    opening_id, ids = _create_linear_opening(client)

    response = client.post(SESSIONS, json={"opening_id": opening_id})
    assert response.status_code == 201
    session = response.json()
    session_id = session["id"]
    assert session["questions_total"] == 3
    assert session["first_try_correct"] == 0
    assert session["finished_at"] is None
    assert session["step"]["kind"] == "question"
    assert session["step"]["node_id"] == ids["root"]
    assert session["step"]["phase"] == "traversal"

    response = client.post(
        f"{SESSIONS}/{session_id}/answer",
        json={"node_id": ids["root"], "move": "d2d4"},
    )
    assert response.status_code == 200
    answer = response.json()
    assert answer["correct"] is False
    assert answer["correct_move_san"] == "e4"
    assert answer["correct_move_uci"] == "e2e4"
    assert answer["next_step"]["node_id"] == ids["e5"]

    # Simula un reinicio: el estado se recupera desde la DB.
    response = client.get(f"{SESSIONS}/{session_id}")
    assert response.status_code == 200
    recovered = response.json()
    assert recovered["step"]["node_id"] == ids["e5"]
    assert recovered["first_try_correct"] == 0

    response = client.post(
        f"{SESSIONS}/{session_id}/answer",
        json={"node_id": ids["e5"], "move": "g1f3"},
    )
    assert response.json()["correct"] is True
    assert response.json()["next_step"]["node_id"] == ids["nc6"]

    response = client.post(
        f"{SESSIONS}/{session_id}/answer",
        json={"node_id": ids["nc6"], "move": "f1c4"},
    )
    assert response.json()["correct"] is True
    assert response.json()["next_step"]["kind"] == "question"
    assert response.json()["next_step"]["phase"] == "review"
    assert response.json()["next_step"]["node_id"] == ids["root"]

    response = client.post(
        f"{SESSIONS}/{session_id}/answer",
        json={"node_id": ids["root"], "move": "e2e4"},
    )
    assert response.json()["correct"] is True
    finished = response.json()["next_step"]
    assert finished["kind"] == "finished"
    assert finished["summary"] == {
        "questions_total": 3,
        "first_try_correct": 2,
        "accuracy": 66.67,
    }

    response = client.get(f"{SESSIONS}/{session_id}")
    session = response.json()
    assert session["finished_at"] is not None
    assert session["questions_total"] == 3
    assert session["first_try_correct"] == 2
    assert session["step"]["kind"] == "finished"

    response = client.post(
        f"{SESSIONS}/{session_id}/answer",
        json={"node_id": ids["root"], "move": "e2e4"},
    )
    assert response.status_code == 409

    stats = client.get(f"{OPENINGS}/{opening_id}/stats").json()
    assert stats["accuracy"] == 75.0
    positions = {position["node_id"]: position for position in stats["positions"]}
    assert positions[ids["root"]]["attempts"] == 2
    assert positions[ids["root"]]["correct"] == 1
    assert positions[ids["root"]]["accuracy"] == 50.0
    assert positions[ids["root"]]["path_san"] == ""
    assert positions[ids["e5"]]["attempts"] == 1
    assert positions[ids["e5"]]["correct"] == 1
    assert positions[ids["e5"]]["path_san"] == "1. e4 e5"
    assert positions[ids["nc6"]]["path_san"] == "1. e4 e5 2. Nf3 Nc6"
    assert positions[ids["nc6"]]["last_practiced_at"] is not None

    opening = client.get(f"{OPENINGS}/{opening_id}").json()
    assert opening["accuracy"] == 75.0


def test_session_without_user_moves(client: TestClient):
    opening = client.post(
        OPENINGS, json={"name": "Nothing To Train", "color": "white"}
    ).json()

    response = client.post(SESSIONS, json={"opening_id": opening["id"]})
    assert response.status_code == 409
    assert "nada para entrenar" in response.json()["detail"]


def test_training_not_found(client: TestClient):
    assert client.post(SESSIONS, json={"opening_id": 9999}).status_code == 404
    assert client.get(f"{SESSIONS}/9999").status_code == 404
    assert (
        client.post(
            f"{SESSIONS}/9999/answer", json={"node_id": 1, "move": "e2e4"}
        ).status_code
        == 404
    )


def test_answer_for_unexpected_node(client: TestClient):
    opening_id, ids = _create_linear_opening(client)
    session = client.post(SESSIONS, json={"opening_id": opening_id}).json()

    response = client.post(
        f"{SESSIONS}/{session['id']}/answer",
        json={"node_id": ids["e5"], "move": "e7e5"},
    )
    assert response.status_code == 422

def test_training_step_includes_move_metadata(client: TestClient):
    opening_id, ids = _create_linear_opening(client)

    client.patch(
        f"/api/nodes/{ids['e4']}",
        json={
            "name": "Salida e4",
            "comment": "Comentario de e4",
            "classification": "book",
        },
    )
    client.patch(
        f"/api/nodes/{ids['e5']}",
        json={
            "name": "Respuesta e5",
            "comment": "Comentario de e5",
            "classification": "mistake",
        },
    )

    response = client.post(SESSIONS, json={"opening_id": opening_id})
    assert response.status_code == 201
    session = response.json()
    assert session["step"]["correct_move"] == {
        "id": ids["e4"],
        "uci": "e2e4",
        "san": "e4",
        "name": "Salida e4",
        "comment": "Comentario de e4",
        "classification": "book",
    }

    response = client.post(
        f"{SESSIONS}/{session['id']}/answer",
        json={"node_id": ids["root"], "move": "e2e4"},
    )
    assert response.status_code == 200
    next_step = response.json()["next_step"]
    assert next_step["node_id"] == ids["e5"]
    assert next_step["lead_in"][-1] == {
        "uci": "e7e5",
        "san": "e5",
        "name": "Respuesta e5",
        "comment": "Comentario de e5",
        "classification": "mistake",
        "evaluation": None,
        "fast_forward": False,
    }


def test_session_from_node_scopes_subtree(client: TestClient):
    opening_id, ids = _create_linear_opening(client)

    response = client.post(
        SESSIONS,
        json={"opening_id": opening_id, "from_node_id": ids["e5"]},
    )
    assert response.status_code == 201
    session = response.json()
    assert session["questions_total"] == 2
    assert session["step"]["node_id"] == ids["e5"]
    assert session["step"]["lead_in"][-1]["fast_forward"] is True

    response = client.post(
        f"{SESSIONS}/{session['id']}/answer",
        json={"node_id": ids["e5"], "move": "g1f3"},
    )
    assert response.status_code == 200
    assert response.json()["next_step"]["node_id"] == ids["nc6"]


def test_hint_used_marks_answer_as_incorrect(client: TestClient):
    opening_id, ids = _create_linear_opening(client)
    session = client.post(SESSIONS, json={"opening_id": opening_id}).json()

    response = client.post(
        f"{SESSIONS}/{session['id']}/answer",
        json={
            "node_id": ids["root"],
            "move": "e2e4",
            "hint_used": True,
        },
    )
    assert response.status_code == 200
    answer = response.json()
    assert answer["correct"] is False
    assert answer["correct_move_san"] == "e4"
    assert answer["next_step"]["node_id"] == ids["e5"]

    recovered = client.get(f"{SESSIONS}/{session['id']}").json()
    assert recovered["first_try_correct"] == 0

    stats = client.get(f"{OPENINGS}/{opening_id}/stats").json()
    root_stats = next(
        position
        for position in stats["positions"]
        if position["node_id"] == ids["root"]
    )
    assert root_stats["attempts"] == 1
    assert root_stats["correct"] == 0
