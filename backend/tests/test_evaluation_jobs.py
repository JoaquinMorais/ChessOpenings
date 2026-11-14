import json
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from config.settings import settings
from models.node import Node
from utils import evaluation_jobs
from utils.seed_files import seed_file_path

BASE = "/api/openings"


class FakeEvaluator:
    is_external = False

    def __init__(
        self,
        results: dict[str, dict] | None = None,
        fail_fens: set[str] | None = None,
        gate: threading.Event | None = None,
        block_at_call: int | None = None,
    ) -> None:
        self.results = results or {}
        self.fail_fens = fail_fens or set()
        self.gate = gate
        self.block_at_call = block_at_call
        self.calls: list[str] = []
        self.closed = False
        self._lock = threading.Lock()

    def evaluate(self, fen: str) -> dict:
        with self._lock:
            call_index = len(self.calls)
            self.calls.append(fen)
        if (
            self.gate is not None
            and self.block_at_call is not None
            and call_index >= self.block_at_call
        ):
            self.gate.wait(timeout=10)
        if fen in self.fail_fens:
            raise RuntimeError("Fake evaluator failure")
        return self.results.get(fen, {"cp": 5})

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def seed_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    from utils import seed_files

    path = tmp_path / "seed"
    monkeypatch.setattr(seed_files, "SEED_IMPORT_DIR", path)
    return path


def _create_opening(
    client: TestClient,
    name: str,
    moves: tuple[str, ...] = ("e4", "e5"),
) -> tuple[int, list[dict]]:
    opening = client.post(BASE, json={"name": name, "color": "white"}).json()
    opening_id = opening["id"]
    root = client.get(f"{BASE}/{opening_id}/tree").json()
    nodes = [root]
    parent_id = root["id"]
    for move in moves:
        response = client.post(
            f"{BASE}/{opening_id}/moves",
            json={"parent_id": parent_id, "move": move},
        )
        assert response.status_code in (200, 201)
        node = response.json()
        nodes.append(node)
        parent_id = node["id"]
    return opening_id, nodes


def _save_seed(
    client: TestClient,
    opening_id: int,
    *,
    visibility: str = "public",
    evaluate: bool = True,
):
    return client.post(
        f"{BASE}/{opening_id}/seed",
        json={
            "visibility": visibility,
            "evaluate": evaluate,
        },
    )


def _wait_job(
    client: TestClient,
    job_id: str,
    *,
    timeout: float = 10,
    min_done: int | None = None,
) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        if min_done is not None:
            if data["done"] >= min_done:
                return data
        elif data["state"] != "running":
            return data
        time.sleep(0.01)
    raise AssertionError(f"Job {job_id} did not reach the expected state")


def _wait_status_not_running(
    client: TestClient,
    opening_id: int,
    *,
    timeout: float = 10,
) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(
            f"{BASE}/{opening_id}/evaluation-status"
        )
        assert response.status_code == 200
        data = response.json()
        if not data["running"]:
            return data
        time.sleep(0.01)
    raise AssertionError("Evaluation status stayed running")


def _install_fake(
    monkeypatch: pytest.MonkeyPatch,
    fake: FakeEvaluator,
) -> None:
    monkeypatch.setattr(evaluation_jobs, "get_evaluator", lambda: fake)


def test_job_only_missing_does_not_overwrite_and_rewrites_seed(
    client: TestClient,
    session: Session,
    seed_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    opening_id, nodes = _create_opening(client, "Job Missing")
    root, e4, e5 = nodes
    response = client.patch(
        f"/api/nodes/{e4['id']}",
        json={"evaluation": {"cp": 35}},
    )
    assert response.status_code == 200

    fake = FakeEvaluator()
    _install_fake(monkeypatch, fake)
    response = _save_seed(client, opening_id)
    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] is not None
    assert payload["message"] is None

    job = _wait_job(client, payload["job_id"])
    assert job["state"] == "done"
    assert job["done"] == 2
    assert job["total"] == 2
    assert job["errors"] == 0

    session.expire_all()
    stored = {
        node_id: session.get(Node, node_id)
        for node_id in (root["id"], e4["id"], e5["id"])
    }
    assert stored[root["id"]].eval_source == "engine"
    assert stored[e4["id"]].eval_source == "manual"
    assert stored[e4["id"]].eval_cp == 35
    assert stored[e5["id"]].eval_source == "engine"

    assert e4["fen"] not in fake.calls
    assert fake.closed is True

    path = seed_file_path("Job Missing", seed_dir)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["opening"]["tree"]["evaluation"]["source"] == "engine"
    assert (
        data["opening"]["tree"]["children"][0]["evaluation"]["source"]
        == "manual"
    )
    assert (
        data["opening"]["tree"]["children"][0]["children"][0]["evaluation"][
            "source"
        ]
        == "engine"
    )

    status = _wait_status_not_running(client, opening_id)
    assert status["missing"] == 0
    assert status["running"] is False
    assert status["job_id"] is None
    assert status["evaluator"] == "stockfish"


def test_cancel_preserves_progress(
    client: TestClient,
    session: Session,
    seed_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    opening_id, nodes = _create_opening(
        client,
        "Job Cancel",
        moves=("e4", "e5", "Nf3"),
    )
    gate = threading.Event()
    fake = FakeEvaluator(gate=gate, block_at_call=1)
    _install_fake(monkeypatch, fake)
    response = _save_seed(client, opening_id)
    job_id = response.json()["job_id"]
    assert job_id is not None

    try:
        _wait_job(client, job_id, min_done=1)
        cancel = client.post(f"/api/jobs/{job_id}/cancel")
        assert cancel.status_code == 200
    finally:
        gate.set()

    job = _wait_job(client, job_id)
    assert job["state"] == "cancelled"
    assert 1 <= job["done"] < job["total"]

    session.expire_all()
    evaluated = session.exec(
        select(Node).where(
            Node.opening_id == opening_id,
            Node.eval_cp.is_not(None),
        )
    ).all()
    assert evaluated
    assert len(evaluated) < len(nodes)
    assert fake.closed is True


def test_second_job_for_same_opening_is_409(
    client: TestClient,
    seed_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    opening_id, _ = _create_opening(client, "Job Conflict", moves=("e4",))
    gate = threading.Event()
    fake = FakeEvaluator(gate=gate, block_at_call=0)
    _install_fake(monkeypatch, fake)

    try:
        first = _save_seed(client, opening_id)
        assert first.status_code == 200
        job_id = first.json()["job_id"]
        assert job_id is not None

        second = _save_seed(client, opening_id)
        assert second.status_code == 409
        assert "valoracion en curso" in second.json()["detail"]

        status = client.get(f"{BASE}/{opening_id}/evaluation-status").json()
        assert status["running"] is True
        assert status["job_id"] == job_id
    finally:
        gate.set()

    job = _wait_job(client, job_id)
    assert job["state"] == "done"
    assert fake.closed is True


def test_failed_node_does_not_stop_job(
    client: TestClient,
    session: Session,
    seed_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    opening_id, nodes = _create_opening(client, "Job Error")
    root, e4, e5 = nodes
    fake = FakeEvaluator(fail_fens={e4["fen"]})
    _install_fake(monkeypatch, fake)
    response = _save_seed(client, opening_id)
    job_id = response.json()["job_id"]

    job = _wait_job(client, job_id)
    assert job["state"] == "done"
    assert job["errors"] == 1
    assert job["done"] == job["total"]

    session.expire_all()
    failed = session.get(Node, e4["id"])
    assert failed is not None
    assert failed.eval_cp is None
    assert failed.eval_mate is None
    assert failed.eval_source is None
    assert session.get(Node, root["id"]).eval_source == "engine"
    assert session.get(Node, e5["id"]).eval_source == "engine"


def test_no_missing_nodes_does_not_create_job(
    client: TestClient,
    session: Session,
    seed_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    opening_id, nodes = _create_opening(
        client, "Job Already Done", moves=("e4",)
    )
    root, e4 = nodes
    client.patch(
        f"/api/nodes/{root['id']}",
        json={"evaluation": {"cp": 10}},
    )
    client.patch(
        f"/api/nodes/{e4['id']}",
        json={"evaluation": {"mate": 2}},
    )

    fake = FakeEvaluator()
    _install_fake(monkeypatch, fake)
    response = _save_seed(client, opening_id)
    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] is None
    assert payload["message"] == "La apertura ya esta valorada."

    status = client.get(f"{BASE}/{opening_id}/evaluation-status").json()
    assert status["missing"] == 0
    assert status["running"] is False
    assert fake.calls == []


def test_jobs_endpoints_not_found_and_finished_cancel(
    client: TestClient,
    seed_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    assert client.get("/api/jobs/does-not-exist").status_code == 404
    assert (
        client.post("/api/jobs/does-not-exist/cancel").status_code
        == 404
    )

    opening_id, _ = _create_opening(client, "Job Finished", moves=("e4",))
    _install_fake(monkeypatch, FakeEvaluator())
    response = _save_seed(client, opening_id)
    job_id = response.json()["job_id"]
    _wait_job(client, job_id)

    cancel = client.post(f"/api/jobs/{job_id}/cancel")
    assert cancel.status_code == 409
    assert "ya termino" in cancel.json()["detail"]


@pytest.mark.skipif(
    not Path(settings.stockfish_path).is_file(),
    reason="Stockfish binary not available",
)
def test_stockfish_integration(client: TestClient, seed_dir: Path):
    opening_id, _ = _create_opening(client, "Stockfish Integration")
    response = _save_seed(client, opening_id)
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert job_id is not None

    job = _wait_job(client, job_id, timeout=30)
    assert job["state"] == "done"
    assert job["errors"] == 0
    assert job["done"] == job["total"]

    tree = client.get(f"{BASE}/{opening_id}/tree").json()
    nodes = [tree, tree["children"][0], tree["children"][0]["children"][0]]
    for node in nodes:
        assert node["evaluation"]["source"] == "engine"
        assert "cp" in node["evaluation"] or "mate" in node["evaluation"]


def test_private_external_evaluator_requires_allow_external(
    client: TestClient,
    seed_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    opening_id, _ = _create_opening(client, "External Private")
    monkeypatch.setattr("routes.io.is_external_evaluator", lambda: True)

    response = client.post(
        f"{BASE}/{opening_id}/seed",
        json={
            "visibility": "private",
            "evaluate": True,
            "allow_external": False,
        },
    )
    assert response.status_code == 409
    assert "allow_external" in response.json()["detail"]
    assert not seed_file_path("External Private", seed_dir).exists()


@pytest.mark.skipif(
    not Path(settings.stockfish_path).is_file(),
    reason="Stockfish binary not available",
)
def test_stockfish_checkmate_returns_cp_not_mate_zero():
    from utils.evaluators import StockfishEvaluator

    evaluator = StockfishEvaluator(settings.stockfish_path, 100)
    try:
        result = evaluator.evaluate(
            "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
        )
    finally:
        evaluator.close()
    assert result == {"cp": -9999}
