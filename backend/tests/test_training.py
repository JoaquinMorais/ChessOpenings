import json
import random

from utils.training import TrainingNode, answer, start


def make_node(
    node_id: int,
    san,
    uci,
    ply: int,
    children=None,
    order_index: int = 0,
    name=None,
    comment=None,
    classification=None,
) -> TrainingNode:
    return TrainingNode(
        id=node_id,
        san=san,
        uci=uci,
        fen=f"fen-{node_id}",
        ply=ply,
        order_index=order_index,
        name=name,
        comment=comment,
        classification=classification,
        children=children or [],
    )


def linear_tree() -> TrainingNode:
    root = make_node(0, None, None, 0)
    a = make_node(1, "e4", "e2e4", 1)
    b = make_node(2, "e5", "e7e5", 2)
    c = make_node(3, "Nf3", "g1f3", 3)
    d = make_node(4, "Nc6", "b8c6", 4)
    e = make_node(5, "Bc4", "f1c4", 5)
    root.children = [a]
    a.children = [b]
    b.children = [c]
    c.children = [d]
    d.children = [e]
    return root


def three_branch_tree() -> TrainingNode:
    root = make_node(0, None, None, 0)
    a = make_node(1, "e4", "e2e4", 1, order_index=0)
    b = make_node(2, "d4", "d2d4", 1, order_index=1)
    c = make_node(3, "c4", "c2c4", 1, order_index=2)
    a.children = [make_node(4, "e5", "e7e5", 2)]
    b.children = [make_node(5, "d5", "d7d5", 2)]
    c.children = [make_node(6, "e6", "e7e6", 2)]
    root.children = [a, b, c]
    return root


def nested_tree() -> TrainingNode:
    root = make_node(0, None, None, 0)
    a = make_node(1, "e4", "e2e4", 1, order_index=0)
    a1 = make_node(2, "e5", "e7e5", 2)
    a2 = make_node(3, "Nf3", "g1f3", 3, order_index=0)
    a3 = make_node(4, "Bc4", "f1c4", 3, order_index=1)
    b = make_node(5, "d4", "d2d4", 1, order_index=1)
    b1 = make_node(6, "d5", "d7d5", 2)
    a.children = [a1]
    a1.children = [a2, a3]
    a2.children = [make_node(7, "d6", "d7d6", 4)]
    a3.children = [make_node(8, "Nf6", "g8f6", 4)]
    b.children = [b1]
    root.children = [a, b]
    return root


def test_linear_tree_and_finish():
    state, step = start(linear_tree(), "white", random.Random(1))
    json.dumps(state)

    assert step["kind"] == "question"
    assert step["node_id"] == 0
    assert step["lead_in"] == []
    assert step["phase"] == "traversal"
    assert state["questions_total"] == 3

    result, state, step = answer(state, 0, "e2e4")
    assert result["correct"] is True
    assert result["correct_move_san"] == "e4"
    assert step["node_id"] == 2
    assert step["lead_in"] == [
        {"uci": "e2e4", "san": "e4", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": True},
        {"uci": "e7e5", "san": "e5", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": False},
    ]

    result, state, step = answer(state, 2, "g1f3")
    assert result["correct"] is True
    assert step["node_id"] == 4
    assert step["lead_in"] == [
        {"uci": "e2e4", "san": "e4", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": True},
        {"uci": "e7e5", "san": "e5", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": True},
        {"uci": "g1f3", "san": "Nf3", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": True},
        {"uci": "b8c6", "san": "Nc6", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": False},
    ]

    result, state, step = answer(state, 4, "f1c4")
    assert result["correct"] is True
    assert step["kind"] == "finished"
    assert step["summary"] == {
        "questions_total": 3,
        "first_try_correct": 3,
        "accuracy": 100.0,
    }


def test_three_branches_principal_first_and_shuffle():
    rest = [2, 3]
    random.Random(1).shuffle(rest)
    expected_questions = [1] + rest

    correct_by_node = {1: "e7e5", 2: "d7d5", 3: "e7e6"}

    state, step = start(three_branch_tree(), "black", random.Random(1))
    visited = []
    while step["kind"] == "question":
        visited.append(step["node_id"])
        _, state, step = answer(state, step["node_id"], correct_by_node[step["node_id"]])

    assert visited == expected_questions
    assert step["kind"] == "finished"


def test_nested_branches_do_not_jump_between_far_branches():
    state, step = start(nested_tree(), "black", random.Random(1))
    assert step["node_id"] == 1

    _, state, step = answer(state, 1, "e7e5")
    assert step["node_id"] == 3
    assert step["lead_in"] == [
        {"uci": "e2e4", "san": "e4", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": True},
        {"uci": "e7e5", "san": "e5", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": True},
        {"uci": "g1f3", "san": "Nf3", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": False},
    ]

    _, state, step = answer(state, 3, "d7d6")
    assert step["node_id"] == 4
    assert step["lead_in"] == [
        {"uci": "e2e4", "san": "e4", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": True},
        {"uci": "e7e5", "san": "e5", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": True},
        {"uci": "f1c4", "san": "Bc4", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": False},
    ]

    _, state, step = answer(state, 4, "g8f6")
    assert step["node_id"] == 5
    assert step["lead_in"] == [
        {"uci": "d2d4", "san": "d4", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": False},
    ]


def test_wrong_answer_goes_to_review_with_rounds():
    state, step = start(linear_tree(), "white", random.Random(1))

    _, state, step = answer(state, 0, "e2e4")
    assert step["node_id"] == 2

    result, state, step = answer(state, 2, "d2d4")
    assert result["correct"] is False
    assert result["correct_move_san"] == "Nf3"
    assert step["node_id"] == 4

    _, state, step = answer(state, 4, "f1c4")
    assert step["kind"] == "question"
    assert step["phase"] == "review"
    assert step["node_id"] == 2
    assert step["lead_in"] == [
        {"uci": "e2e4", "san": "e4", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": True},
        {"uci": "e7e5", "san": "e5", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": True},
    ]
    assert state["pending"] == [2]

    result, state, step = answer(state, 2, "d2d4")
    assert result["correct"] is False
    assert step["phase"] == "review"
    assert step["node_id"] == 2
    assert state["pending"] == [2]

    result, state, step = answer(state, 2, "g1f3")
    assert result["correct"] is True
    assert step["kind"] == "finished"
    assert step["summary"] == {
        "questions_total": 3,
        "first_try_correct": 2,
        "accuracy": 66.67,
    }


def test_black_opening_first_step_includes_rival_move():
    state, step = start(three_branch_tree(), "black", random.Random(1))

    assert step["kind"] == "question"
    assert step["node_id"] == 1
    assert step["lead_in"] == [
        {"uci": "e2e4", "san": "e4", "name": None, "comment": None, "classification": None, "evaluation": None, "fast_forward": False},
    ]
    assert json.dumps(state)

def test_step_includes_move_metadata():
    root = make_node(0, None, None, 0)
    rival = make_node(
        1,
        "e4",
        "e2e4",
        1,
        name="Apertura rival",
        comment="Comentario del rival",
        classification="book",
    )
    correct = make_node(
        2,
        "e5",
        "e7e5",
        2,
        name="Respuesta correcta",
        comment="Comentario correcto",
        classification="best",
    )
    rival.children = [correct]
    root.children = [rival]

    _, step = start(root, "black", random.Random(1))

    assert step["node_id"] == 1
    assert step["lead_in"] == [
        {
            "uci": "e2e4",
            "san": "e4",
            "name": "Apertura rival",
            "comment": "Comentario del rival",
            "classification": "book",
            "evaluation": None,
            "fast_forward": False,
        }
    ]
    assert step["correct_move"] == {
        "id": 2,
        "uci": "e7e5",
        "san": "e5",
        "name": "Respuesta correcta",
        "comment": "Comentario correcto",
        "classification": "best",
    }


def test_question_filter_skips_disallowed_questions():
    state, step = start(
        linear_tree(),
        "white",
        random.Random(1),
        question_filter={2},
    )

    assert state["questions_total"] == 1
    assert step["node_id"] == 2
    assert step["lead_in"] == [
        {
            "uci": "e2e4",
            "san": "e4",
            "name": None,
            "comment": None,
            "classification": None,
            "evaluation": None,
            "fast_forward": True,
        },
        {
            "uci": "e7e5",
            "san": "e5",
            "name": None,
            "comment": None,
            "classification": None,
            "evaluation": None,
            "fast_forward": False,
        },
    ]

    _, state, step = answer(state, 2, "g1f3")
    assert step["kind"] == "finished"


def test_from_node_id_scopes_subtree():
    state, step = start(
        linear_tree(),
        "white",
        random.Random(1),
        from_node_id=2,
    )

    assert state["questions_total"] == 2
    assert step["node_id"] == 2
    assert step["lead_in"] == [
        {
            "uci": "e2e4",
            "san": "e4",
            "name": None,
            "comment": None,
            "classification": None,
            "evaluation": None,
            "fast_forward": True,
        },
        {
            "uci": "e7e5",
            "san": "e5",
            "name": None,
            "comment": None,
            "classification": None,
            "evaluation": None,
            "fast_forward": True,
        },
    ]

    _, state, step = answer(state, 2, "g1f3")
    assert step["node_id"] == 4

    _, state, step = answer(state, 4, "f1c4")
    assert step["kind"] == "finished"


def test_empty_question_filter_finishes():
    _, step = start(
        linear_tree(),
        "white",
        random.Random(1),
        question_filter=set(),
    )

    assert step["kind"] == "finished"
    assert step["summary"]["questions_total"] == 0
    assert step["summary"]["accuracy"] == 0.0


def test_hint_used_counts_as_error():
    state, step = start(linear_tree(), "white", random.Random(1))

    result, state, step = answer(state, 0, "e2e4", hint_used=True)

    assert result["correct"] is False
    assert result["move_correct"] is True
    assert state["pending"] == [0]
    assert state["first_try_correct"] == 0
    assert step["node_id"] == 2
