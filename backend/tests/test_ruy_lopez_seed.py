import json
from collections import Counter
from pathlib import Path

from sqlmodel import Session, select

from models.node import Node
from utils.opening_io import export_opening, import_opening
from utils.seed_files import seed_file_exists, seed_file_path

SEED_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "seed_import"
    / "ruy-lopez-espanola.json"
)
OPENING_NAME = "Ruy Lopez (Apertura Espanola)"


def _mainline(nodes: list[Node], root: Node) -> list[Node]:
    line: list[Node] = []
    current = root
    for expected_san in ("e4", "e5", "Nf3", "Nc6", "Bb5"):
        children = sorted(
            [node for node in nodes if node.parent_id == current.id],
            key=lambda node: node.order_index,
        )
        assert children, f"Falta la jugada {expected_san}"
        current = children[0]
        assert current.move_san == expected_san
        line.append(current)
    return line


def test_ruy_lopez_seed_import_and_round_trip(session: Session):
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    opening = import_opening(session, data)

    assert opening.name == OPENING_NAME
    assert opening.color == "white"
    assert seed_file_exists(OPENING_NAME)
    assert seed_file_path(OPENING_NAME) == SEED_PATH

    nodes = session.exec(
        select(Node).where(Node.opening_id == opening.id)
    ).all()
    root = next(node for node in nodes if node.parent_id is None)
    mainline = _mainline(nodes, root)
    bb5 = mainline[-1]

    rival_responses = sorted(
        [node for node in nodes if node.parent_id == bb5.id],
        key=lambda node: node.order_index,
    )
    assert len(rival_responses) >= 9
    assert rival_responses[0].move_san == "a6"
    assert rival_responses[0].order_index == 0

    child_counts = Counter(
        node.parent_id for node in nodes if node.parent_id is not None
    )
    for node in nodes:
        if node.ply % 2 == 0:
            assert child_counts[node.id] <= 1, (
                f"La posicion blanca del nodo {node.id} tiene mas de un hijo"
            )

    first_export = export_opening(session, opening.id)
    session.delete(opening)
    session.commit()

    second_opening = import_opening(session, first_export)
    second_export = export_opening(session, second_opening.id)
    assert second_export == first_export
