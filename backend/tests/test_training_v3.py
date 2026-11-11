import random
from typing import Any, Optional

from fastapi.testclient import TestClient
from sqlmodel import Session

from models.training import TrainingSession
from utils.training import TrainingNode, answer, start

OPENINGS = "/api/openings"
SESSIONS = "/api/training/sessions"


def _node(
    node_id: int,
    san: Optional[str],
    uci: Optional[str],
    ply: int,
    *,
    name: Optional[str] = None,
    comment: Optional[str] = None,
    classification: Optional[str] = None,
    evaluation: Optional[dict[str, int]] = None,
    children: Optional[list[TrainingNode]] = None,
) -> TrainingNode:
    return TrainingNode(
        id=node_id,
        san=san,
        uci=uci,
        fen=f"fen-{node_id}",
        ply=ply,
        order_index=0,
        name=name,
        comment=comment,
        classification=classification,
        evaluation=evaluation,
        children=children or [],
    )


def test_lead_in_question_and_answer_include_evaluation():
    root = _node(0, None, None, 0, evaluation={"cp": 10})
    rival = _node(
        1,
        "e4",
        "e2e4",
        1,
        name="Rival",
        comment="Comentario rival",
        classification="book",
        evaluation={"cp": 20},
    )
    correct = _node(
        2,
        "e5",
        "e7e5",
        2,
        name="Correcta",
        comment="Comentario correcto",
        classification="best",
        evaluation={"mate": 2},
    )
    rival.children = [correct]
    root.children = [rival]

    state, step = start(root, "black", random.Random(1))

    assert step["node_id"] == 1
    assert step["evaluation"] == {"cp": 20}
    assert step["lead_in"] == [
        {
            "uci": "e2e4",
            "san": "e4",
            "name": "Rival",
            "comment": "Comentario rival",
            "classification": "book",
            "evaluation": {"cp": 20},
            "fast_forward": False,
        }
    ]

    result, _, _ = answer(state, 1, "e7e5")
    assert result["correct_move"] == {
        "uci": "e7e5",
        "san": "e5",
        "name": "Correcta",
        "comment": "Comentario correcto",
        "classification": "best",
        "evaluation": {"mate": 2},
    }


def test_missing_metadata_returns_null():
    root = _node(0, None, None, 0)
    rival = _node(1, "e4", "e2e4", 1)
    correct = _node(2, "e5", "e7e5", 2)
    rival.children = [correct]
    root.children = [rival]

    state, step = start(root, "black", random.Random(1))
    assert step["evaluation"] is None
    assert step["lead_in"][0]["evaluation"] is None
    assert step["lead_in"][0]["name"] is None
    assert step["lead_in"][0]["classification"] is None

    result, _, _ = answer(state, 1, "e7e5")
    assert result["correct_move"] == {
        "uci": "e7e5",
        "san": "e5",
        "name": None,
        "comment": None,
        "classification": None,
        "evaluation": None,
    }


def _create_line(client: TestClient, name: str) -> tuple[int, dict[str, int]]:
    opening = client.post(
        OPENINGS, json={"name": name, "color": "white"}
    ).json()
    opening_id = opening["id"]
    root_id = client.get(f"{OPENINGS}/{opening_id}/tree").json()["id"]

    ids = {"root": root_id}
    parent_id = root_id
    for move in ("e4", "e5", "Nf3", "Nc6", "Bc4"):
        node = client.post(
            f"{OPENINGS}/{opening_id}/moves",
            json={"parent_id": parent_id, "move": move},
        ).json()
        ids[move] = node["id"]
        parent_id = node["id"]
    return opening_id, ids


def _patch_node(
    client: TestClient,
    node_id: int,
    *,
    name: str,
    comment: str,
    classification: str,
    evaluation: dict[str, int],
) -> None:
    response = client.patch(
        f"/api/nodes/{node_id}",
        json={
            "name": name,
            "comment": comment,
            "classification": classification,
            "evaluation": evaluation,
        },
    )
    assert response.status_code == 200


def _prepare_opening(client: TestClient, name: str) -> tuple[int, dict[str, int]]:
    opening_id, ids = _create_line(client, name)
    root_response = client.patch(
        f"/api/nodes/{ids['root']}",
        json={"evaluation": {"cp": 20}},
    )
    assert root_response.status_code == 200
    _patch_node(
        client,
        ids["e4"],
        name="Salida",
        comment="Comentario e4",
        classification="book",
        evaluation={"cp": 30},
    )
    _patch_node(
        client,
        ids["e5"],
        name="Respuesta",
        comment="Comentario e5",
        classification="mistake",
        evaluation={"cp": -20},
    )
    _patch_node(
        client,
        ids["Nf3"],
        name="Desarrollo",
        comment="Comentario Nf3",
        classification="best",
        evaluation={"cp": 40},
    )
    _patch_node(
        client,
        ids["Nc6"],
        name="Defensa",
        comment="Comentario Nc6",
        classification="book",
        evaluation={"cp": 50},
    )
    return opening_id, ids


def test_api_training_steps_include_evaluation_and_metadata(client: TestClient):
    opening_id, ids = _prepare_opening(client, "Training V3 API")

    session = client.post(
        SESSIONS, json={"opening_id": opening_id}
    ).json()
    step = session["step"]
    assert step["node_id"] == ids["root"]
    assert step["evaluation"] == {"cp": 20}

    response = client.post(
        f"{SESSIONS}/{session['id']}/answer",
        json={"node_id": ids["root"], "move": "e2e4"},
    )
    assert response.status_code == 200
    answer_data = response.json()
    assert answer_data["correct_move"] == {
        "uci": "e2e4",
        "san": "e4",
        "name": "Salida",
        "comment": "Comentario e4",
        "classification": "book",
        "evaluation": {"cp": 30},
    }

    next_step = answer_data["next_step"]
    assert next_step["node_id"] == ids["e5"]
    assert next_step["evaluation"] == {"cp": -20}
    assert next_step["lead_in"][0]["evaluation"] == {"cp": 30}
    assert next_step["lead_in"][0]["name"] == "Salida"
    assert next_step["lead_in"][0]["classification"] == "book"
    assert next_step["lead_in"][1]["evaluation"] == {"cp": -20}
    assert next_step["lead_in"][1]["name"] == "Respuesta"
    assert next_step["lead_in"][1]["classification"] == "mistake"


def _strip_tree_metadata(node: dict[str, Any]) -> None:
    for key in ("name", "comment", "classification", "evaluation"):
        node.pop(key, None)
    for child in node.get("children", []):
        _strip_tree_metadata(child)


def _strip_step_metadata(step: dict[str, Any]) -> None:
    step.pop("evaluation", None)
    for move in step.get("lead_in", []):
        for key in ("name", "comment", "classification", "evaluation"):
            move.pop(key, None)

    correct_move = step.get("correct_move")
    if isinstance(correct_move, dict):
        for key in ("name", "comment", "classification", "evaluation"):
            correct_move.pop(key, None)


def test_old_session_state_is_hydrated_from_current_tree(
    client: TestClient, session: Session
):
    opening_id, ids = _prepare_opening(client, "Training V3 Legacy")
    created = client.post(
        SESSIONS, json={"opening_id": opening_id}
    ).json()

    client.post(
        f"{SESSIONS}/{created['id']}/answer",
        json={"node_id": ids["root"], "move": "e2e4"},
    )

    session.expire_all()
    training_session = session.get(TrainingSession, created["id"])
    state = training_session.state
    _strip_tree_metadata(state["tree"])
    _strip_step_metadata(state["last_step"])
    training_session.state = state
    session.add(training_session)
    session.commit()

    recovered = client.get(f"{SESSIONS}/{created['id']}")
    assert recovered.status_code == 200
    step = recovered.json()["step"]
    assert step["node_id"] == ids["e5"]
    assert step["evaluation"] == {"cp": -20}
    assert step["lead_in"][0]["evaluation"] == {"cp": 30}
    assert step["lead_in"][0]["name"] == "Salida"
    assert step["lead_in"][1]["evaluation"] == {"cp": -20}
    assert step["lead_in"][1]["name"] == "Respuesta"

    response = client.post(
        f"{SESSIONS}/{created['id']}/answer",
        json={"node_id": ids["e5"], "move": "g1f3"},
    )
    assert response.status_code == 200
    answer_data = response.json()
    assert answer_data["correct_move"] == {
        "uci": "g1f3",
        "san": "Nf3",
        "name": "Desarrollo",
        "comment": "Comentario Nf3",
        "classification": "best",
        "evaluation": {"cp": 40},
    }

    session.expire_all()
    persisted = session.get(TrainingSession, created["id"])
    assert persisted.state["tree"]["children"][0]["evaluation"] == {"cp": 30}
    assert (
        persisted.state["last_step"]["lead_in"][-1]["evaluation"]
        == {"cp": 50}
    ), persisted.state["last_step"]
