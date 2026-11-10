from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TrainingNode:
    id: int
    san: Optional[str]
    uci: Optional[str]
    fen: str
    ply: int
    order_index: int
    name: Optional[str] = None
    comment: Optional[str] = None
    classification: Optional[str] = None
    children: List["TrainingNode"] = field(default_factory=list)


State = Dict[str, Any]
Step = Dict[str, Any]
AnswerResult = Dict[str, Any]


def _is_user_turn(ply: int, color: str) -> bool:
    return ply % 2 == (0 if color == "white" else 1)


def _is_question(node: Dict[str, Any], color: str) -> bool:
    return _is_user_turn(node["ply"], color) and bool(node["children"])


def _serialize_tree(node: TrainingNode, rng: random.Random) -> Dict[str, Any]:
    children = sorted(node.children, key=lambda child: (child.order_index, child.id))
    if children:
        main = children[0]
        rest = children[1:]
        rng.shuffle(rest)
        ordered_children = [main] + rest
    else:
        ordered_children = []

    return {
        "id": node.id,
        "san": node.san,
        "uci": node.uci,
        "fen": node.fen,
        "ply": node.ply,
        "order_index": node.order_index,
        "name": node.name,
        "comment": node.comment,
        "classification": node.classification,
        "children": [_serialize_tree(child, rng) for child in ordered_children],
    }


def _index_tree(root: Dict[str, Any]) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, Optional[int]], List[int]]:
    by_id: Dict[int, Dict[str, Any]] = {}
    parent: Dict[int, Optional[int]] = {}
    order: List[int] = []

    def walk(node: Dict[str, Any], parent_id: Optional[int]) -> None:
        by_id[node["id"]] = node
        parent[node["id"]] = parent_id
        order.append(node["id"])
        for child in node["children"]:
            walk(child, node["id"])

    walk(root, None)
    return by_id, parent, order


def _pending_in_dfs_order(pending: List[int], order: List[int]) -> List[int]:
    pending_set = set(pending)
    return [node_id for node_id in order if node_id in pending_set]


def _scope_order(
    full_order: List[int],
    parent: Dict[int, Optional[int]],
    start_id: int,
) -> List[int]:
    def in_subtree(node_id: int) -> bool:
        current: Optional[int] = node_id
        while current is not None:
            if current == start_id:
                return True
            current = parent[current]
        return False

    return [node_id for node_id in full_order if in_subtree(node_id)]


def _ancestor_ids(
    start_id: int,
    parent: Dict[int, Optional[int]],
) -> List[int]:
    ids: List[int] = []
    current: Optional[int] = start_id
    while current is not None:
        ids.append(current)
        current = parent[current]
    return ids


def _lead_in(
    node_id: int,
    by_id: Dict[int, Dict[str, Any]],
    parent: Dict[int, Optional[int]],
    seen: List[int],
    phase: str,
) -> List[Dict[str, Any]]:
    seen_set = set(seen)
    moves: List[Dict[str, Any]] = []
    current: Optional[int] = node_id
    while current is not None and parent[current] is not None:
        node = by_id[current]
        moves.append(
            {
                "uci": node["uci"],
                "san": node["san"],
                "name": node.get("name"),
                "comment": node.get("comment"),
                "classification": node.get("classification"),
                "fast_forward": True if phase == "review" else current in seen_set,
            }
        )
        current = parent[current]
    moves.reverse()
    return moves


def _question_step(
    state: State,
    node_id: int,
    by_id: Dict[int, Dict[str, Any]],
    parent: Dict[int, Optional[int]],
    phase: str,
) -> Step:
    node = by_id[node_id]
    return {
        "kind": "question",
        "node_id": node_id,
        "fen": node["fen"],
        "lead_in": _lead_in(node_id, by_id, parent, state["seen"], phase),
        "correct_move": {
            "id": node["children"][0]["id"],
            "uci": node["children"][0]["uci"],
            "san": node["children"][0]["san"],
            "name": node["children"][0].get("name"),
            "comment": node["children"][0].get("comment"),
            "classification": node["children"][0].get("classification"),
        },
        "phase": phase,
        "progress": {
            "answered": state["answered"],
            "total": state["questions_total"],
            "pending": len(state["pending"]),
        },
    }


def _finished_step(state: State) -> Step:
    total = state["questions_total"]
    correct = state["first_try_correct"]
    accuracy = round(correct / total * 100, 2) if total else 0.0
    return {
        "kind": "finished",
        "summary": {
            "questions_total": total,
            "first_try_correct": correct,
            "accuracy": accuracy,
        },
    }


def _next_step(state: State) -> Step:
    by_id, parent, _ = _index_tree(state["tree"])
    order = state["order"]
    allowed_raw = state.get("allowed_question_ids")
    allowed_ids = set(allowed_raw) if allowed_raw is not None else None

    while state["phase"] == "traversal":
        if state["cursor"] >= len(order):
            if state["pending"]:
                state["phase"] = "review"
                state["review_queue"] = _pending_in_dfs_order(state["pending"], order)
                state["review_index"] = 0
                break
            return _finished_step(state)

        node_id = order[state["cursor"]]
        node = by_id[node_id]
        if _is_question(node, state["color"]) and (
            allowed_ids is None or node_id in allowed_ids
        ):
            state["awaiting"] = node_id
            return _question_step(state, node_id, by_id, parent, "traversal")

        if node_id not in state["seen"]:
            state["seen"].append(node_id)
        state["cursor"] += 1

    while state["phase"] == "review":
        if state["review_index"] >= len(state["review_queue"]):
            if state["pending"]:
                state["review_queue"] = _pending_in_dfs_order(state["pending"], order)
                state["review_index"] = 0
            else:
                return _finished_step(state)

        question_id = state["review_queue"][state["review_index"]]
        state["awaiting"] = question_id
        return _question_step(state, question_id, by_id, parent, "review")

    return _finished_step(state)


def start(
    tree: TrainingNode,
    color: str,
    rng: random.Random,
    question_filter: Optional[set[int]] = None,
    from_node_id: Optional[int] = None,
) -> Tuple[State, Step]:
    serialized = _serialize_tree(tree, rng)
    by_id, parent, full_order = _index_tree(serialized)

    if from_node_id is not None and from_node_id not in by_id:
        raise ValueError("La posicion inicial del entrenamiento no existe.")

    scope_root_id = from_node_id if from_node_id is not None else serialized["id"]
    order = (
        _scope_order(full_order, parent, scope_root_id)
        if from_node_id is not None
        else full_order
    )
    initial_seen = (
        _ancestor_ids(scope_root_id, parent)
        if from_node_id is not None
        else []
    )

    allowed_ids: List[int] = []
    for node_id in order:
        node = by_id[node_id]
        if not _is_question(node, color):
            continue
        if question_filter is not None and node_id not in question_filter:
            continue
        allowed_ids.append(node_id)

    state: State = {
        "color": color,
        "tree": serialized,
        "order": order,
        "cursor": 0,
        "seen": initial_seen,
        "pending": [],
        "phase": "traversal",
        "review_queue": [],
        "review_index": 0,
        "awaiting": None,
        "questions_total": len(allowed_ids),
        "first_try_correct": 0,
        "answered": 0,
        "allowed_question_ids": allowed_ids,
        "scope_root_id": scope_root_id,
    }

    step = _next_step(state)
    return state, step


def answer(
    state: State,
    node_id: int,
    move_uci: str,
    hint_used: bool = False,
) -> Tuple[AnswerResult, State, Step]:
    new_state = copy.deepcopy(state)
    by_id, _, _ = _index_tree(new_state["tree"])
    order = new_state["order"]

    if new_state.get("awaiting") != node_id:
        raise ValueError("No se esperaba una respuesta para ese nodo.")

    question = by_id[node_id]
    if not question["children"]:
        raise ValueError("La pregunta no tiene una jugada correcta.")

    correct_move = question["children"][0]
    move_correct = move_uci.strip().lower() == correct_move["uci"]
    correct = move_correct and not hint_used
    result: AnswerResult = {
        "correct": correct,
        "move_correct": move_correct,
        "hint_used": hint_used,
        "correct_move_san": correct_move["san"],
        "correct_move_uci": correct_move["uci"],
        "node_id": node_id,
    }

    if new_state["phase"] == "traversal":
        if node_id not in new_state["seen"]:
            new_state["seen"].append(node_id)
        if correct_move["id"] not in new_state["seen"]:
            new_state["seen"].append(correct_move["id"])
        new_state["cursor"] = order.index(correct_move["id"]) + 1
        new_state["answered"] += 1
        if correct:
            new_state["first_try_correct"] += 1
        elif node_id not in new_state["pending"]:
            new_state["pending"].append(node_id)
    elif new_state["phase"] == "review":
        if correct and node_id in new_state["pending"]:
            new_state["pending"].remove(node_id)
        new_state["review_index"] += 1

    new_state["awaiting"] = None
    next_step = _next_step(new_state)
    return result, new_state, next_step