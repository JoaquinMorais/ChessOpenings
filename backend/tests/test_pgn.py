from fastapi.testclient import TestClient

BASE = "/api/openings"


def _import_pgn(
    client: TestClient,
    pgn: str,
    color: str,
    name: str | None = None,
    on_own_branch: str = "error",
):
    payload = {"pgn": pgn, "color": color}
    if name is not None:
        payload["name"] = name
    return client.post(
        f"{BASE}/import-pgn?on_own_branch={on_own_branch}",
        json=payload,
    )


def _mainline(tree: dict) -> list[dict]:
    nodes = []
    node = tree
    while node["children"]:
        node = node["children"][0]
        nodes.append(node)
    return nodes


def test_import_pgn_variations_and_comments(client: TestClient):
    pgn = """
[Event "Estudio PGN"]
[Result "*"]

1. e4 {Comentario e4} (1. d4 {Comentario d4} 1... d5 2. c4)
1... e5 {Comentario e5} 2. Nf3 {Comentario Nf3} (2. Bc4 {Comentario Bc4} 2... Nf6) *
"""
    response = _import_pgn(client, pgn, "black")
    assert response.status_code == 201
    opening = response.json()
    assert opening["name"] == "Estudio PGN"

    tree = client.get(f"{BASE}/{opening['id']}/tree").json()
    assert [child["uci"] for child in tree["children"]] == ["e2e4", "d2d4"]
    e4 = tree["children"][0]
    d4 = tree["children"][1]
    assert e4["comment"] == "Comentario e4"
    assert d4["comment"] == "Comentario d4"
    assert e4["children"][0]["comment"] == "Comentario e5"
    assert [child["san"] for child in e4["children"][0]["children"]] == [
        "Nf3",
        "Bc4",
    ]
    assert e4["children"][0]["children"][0]["comment"] == "Comentario Nf3"
    assert e4["children"][0]["children"][1]["comment"] == "Comentario Bc4"

    exported = client.get(f"{BASE}/{opening['id']}/export.pgn")
    assert exported.status_code == 200
    assert "attachment" in exported.headers["content-disposition"]
    content = exported.text
    assert "Estudio PGN" in content
    assert "Comentario e4" in content
    assert "(" in content


def test_import_pgn_own_branch_conflict(client: TestClient):
    pgn = '[Event "Conflicto"]\n\n1. e4 (1. d4) 1... e5 *\n'
    response = _import_pgn(client, pgn, "white")
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "posición inicial" in detail
    assert "e4" in detail
    assert "d4" in detail

    response = _import_pgn(client, pgn, "white", on_own_branch="first")
    assert response.status_code == 201
    opening_id = response.json()["id"]
    tree = client.get(f"{BASE}/{opening_id}/tree").json()
    assert [child["uci"] for child in tree["children"]] == ["e2e4"]


def test_import_pgn_invalid_and_name_conflicts(client: TestClient):
    assert _import_pgn(client, "esto no es pgn", "white").status_code == 422

    pgn_without_name = "1. e4 e5 *"
    assert _import_pgn(client, pgn_without_name, "white").status_code == 422

    pgn = '[Event "Duplicado PGN"]\n\n1. e4 e5 *\n'
    assert _import_pgn(client, pgn, "white").status_code == 201
    assert _import_pgn(client, pgn, "white").status_code == 409


def test_import_pgn_multipart_file(client: TestClient):
    pgn = '[Event "Archivo PGN"]\n\n1. e4 e5 *\n'
    response = client.post(
        f"{BASE}/import-pgn",
        files={"file": ("archivo.pgn", pgn, "application/x-chess-pgn")},
        data={"color": "white"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Archivo PGN"


def test_import_export_pgn_all_classifications_round_trip(client: TestClient):
    pgn = """
[Event "All Classifications"]
[Result "*"]

1. e4 $3 e5 $1 2. Nf3 $2 Nc6 $4 3. Bb5 $6 a6 {[%cls best]}
4. Ba4 {[%cls excellent] Comentario visible} Nf6 {[%cls good]}
5. O-O {[%cls book]} Be7 {[%cls miss]} *
"""
    response = _import_pgn(client, pgn, "white")
    assert response.status_code == 201
    opening_id = response.json()["id"]

    tree = client.get(f"{BASE}/{opening_id}/tree").json()
    line = _mainline(tree)
    expected = [
        ("e4", "brilliant", None),
        ("e5", "great", None),
        ("Nf3", "mistake", None),
        ("Nc6", "blunder", None),
        ("Bb5", "inaccuracy", None),
        ("a6", "best", None),
        ("Ba4", "excellent", "Comentario visible"),
        ("Nf6", "good", None),
        ("O-O", "book", None),
        ("Be7", "miss", None),
    ]
    assert [
        (node["san"], node["classification"], node["comment"])
        for node in line
    ] == expected

    exported = client.get(f"{BASE}/{opening_id}/export.pgn")
    assert exported.status_code == 200
    content = exported.text
    for nag in ("$3", "$1", "$2", "$4", "$6"):
        assert nag in content
    for tag in ("best", "excellent", "good", "book", "miss"):
        assert f"[%cls {tag}]" in content
    assert "Comentario visible" in content

    assert client.delete(f"{BASE}/{opening_id}").status_code == 204
    reimported = _import_pgn(client, content, "white")
    assert reimported.status_code == 201
    reimported_id = reimported.json()["id"]
    tree2 = client.get(f"{BASE}/{reimported_id}/tree").json()
    line2 = _mainline(tree2)
    assert [
        (node["san"], node["classification"], node["comment"])
        for node in line2
    ] == expected