import chess
import pytest
from fastapi.testclient import TestClient

from utils.tree import apply_move

BASE = "/api/openings"


def _board_after(moves: list[str]) -> chess.Board:
    board = chess.Board()
    for move in moves:
        board.push_san(move)
    return board


def _create_opening(client: TestClient, name: str, color: str) -> int:
    response = client.post(BASE, json={"name": name, "color": color})
    assert response.status_code == 201
    return response.json()["id"]


def _root_id(client: TestClient, opening_id: int) -> int:
    response = client.get(f"{BASE}/{opening_id}/tree")
    assert response.status_code == 200
    return response.json()["id"]


def _add_move(client: TestClient, opening_id: int, parent_id: int, move: str) -> dict:
    response = client.post(
        f"{BASE}/{opening_id}/moves",
        json={"parent_id": parent_id, "move": move},
    )
    assert response.status_code in (200, 201)
    return response.json()


def _add_line(
    client: TestClient, opening_id: int, root_id: int, moves: list[str]
) -> dict:
    parent_id = root_id
    last: dict = {}
    for move in moves:
        last = _add_move(client, opening_id, parent_id, move)
        parent_id = last["id"]
    return last


def _leaf(tree: dict) -> dict:
    node = tree
    while node["children"]:
        node = node["children"][0]
    return node


def test_en_passant_apply_move():
    board = _board_after(["e4", "a6", "e5", "d5"])
    result = apply_move(board.fen(), board.ply(), "exd6")

    assert result.san == "exd6"
    assert result.uci == "e5d6"

    after = chess.Board(result.fen)
    assert after.piece_at(chess.D5) is None
    assert after.piece_at(chess.D6) == chess.Piece(chess.PAWN, chess.WHITE)


def test_castling_short_apply_move():
    board = _board_after(["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5"])
    result = apply_move(board.fen(), board.ply(), "e1g1")

    assert result.san == "O-O"
    assert result.uci == "e1g1"

    after = chess.Board(result.fen)
    assert after.piece_at(chess.G1) == chess.Piece(chess.KING, chess.WHITE)
    assert after.piece_at(chess.F1) == chess.Piece(chess.ROOK, chess.WHITE)


def test_castling_long_apply_move():
    board = _board_after(
        ["d4", "d5", "Nc3", "Nc6", "Bf4", "Bf5", "Qd2", "Qd7"]
    )
    result = apply_move(board.fen(), board.ply(), "e1c1")

    assert result.san == "O-O-O"
    assert result.uci == "e1c1"

    after = chess.Board(result.fen)
    assert after.piece_at(chess.C1) == chess.Piece(chess.KING, chess.WHITE)
    assert after.piece_at(chess.D1) == chess.Piece(chess.ROOK, chess.WHITE)


@pytest.mark.parametrize(
    "uci,san,piece_type",
    [
        ("a7a8q", "a8=Q", chess.QUEEN),
        ("a7a8r", "a8=R", chess.ROOK),
        ("a7a8b", "a8=B", chess.BISHOP),
        ("a7a8n", "a8=N", chess.KNIGHT),
    ],
)
def test_promotion_apply_move(uci: str, san: str, piece_type: int):
    board = _board_after(
        ["a4", "b5", "axb5", "a6", "bxa6", "Nc6", "a7", "Rb8"]
    )
    result = apply_move(board.fen(), board.ply(), uci)

    assert result.san == san
    assert result.uci == uci

    after = chess.Board(result.fen)
    assert after.piece_at(chess.A8) == chess.Piece(piece_type, chess.WHITE)


def test_en_passant_api(client: TestClient):
    opening_id = _create_opening(client, "Special EP", "white")
    root_id = _root_id(client, opening_id)
    node = _add_line(
        client,
        opening_id,
        root_id,
        ["e4", "a6", "e5", "d5", "exd6"],
    )

    assert node["move_san"] == "exd6"
    assert node["move_uci"] == "e5d6"


def test_castling_short_api(client: TestClient):
    opening_id = _create_opening(client, "Special O-O", "white")
    root_id = _root_id(client, opening_id)
    node = _add_line(
        client,
        opening_id,
        root_id,
        ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "O-O"],
    )

    assert node["move_san"] == "O-O"
    assert node["move_uci"] == "e1g1"


def test_castling_long_api(client: TestClient):
    opening_id = _create_opening(client, "Special O-O-O", "white")
    root_id = _root_id(client, opening_id)
    node = _add_line(
        client,
        opening_id,
        root_id,
        ["d4", "d5", "Nc3", "Nc6", "Bf4", "Bf5", "Qd2", "Qd7", "O-O-O"],
    )

    assert node["move_san"] == "O-O-O"
    assert node["move_uci"] == "e1c1"


def test_promotion_api(client: TestClient):
    opening_id = _create_opening(client, "Special Promotion", "white")
    root_id = _root_id(client, opening_id)
    node = _add_line(
        client,
        opening_id,
        root_id,
        ["a4", "b5", "axb5", "a6", "bxa6", "Nc6", "a7", "Rb8", "a8=Q"],
    )

    assert node["move_san"] == "a8=Q"
    assert node["move_uci"] == "a7a8q"


@pytest.mark.parametrize(
    "name,moves,san,uci",
    [
        (
            "Round Trip En Passant",
            ["e4", "a6", "e5", "d5", "exd6"],
            "exd6",
            "e5d6",
        ),
        (
            "Round Trip Castle Short",
            ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "O-O"],
            "O-O",
            "e1g1",
        ),
        (
            "Round Trip Castle Long",
            ["d4", "d5", "Nc3", "Nc6", "Bf4", "Bf5", "Qd2", "Qd7", "O-O-O"],
            "O-O-O",
            "e1c1",
        ),
        (
            "Round Trip Promotion",
            ["a4", "b5", "axb5", "a6", "bxa6", "Nc6", "a7", "Rb8", "a8=Q"],
            "a8=Q",
            "a7a8q",
        ),
    ],
)
def test_export_import_round_trip_special_moves(
    client: TestClient,
    name: str,
    moves: list[str],
    san: str,
    uci: str,
):
    opening_id = _create_opening(client, name, "white")
    root_id = _root_id(client, opening_id)
    _add_line(client, opening_id, root_id, moves)

    exported = client.get(f"{BASE}/{opening_id}/export").json()
    assert client.delete(f"{BASE}/{opening_id}").status_code == 204

    response = client.post(f"{BASE}/import", json=exported)
    assert response.status_code == 201
    imported_id = response.json()["id"]

    tree = client.get(f"{BASE}/{imported_id}/tree").json()
    leaf = _leaf(tree)
    assert leaf["san"] == san
    assert leaf["uci"] == uci

    re_exported = client.get(f"{BASE}/{imported_id}/export").json()
    assert re_exported == exported