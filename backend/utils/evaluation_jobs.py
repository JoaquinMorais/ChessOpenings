import logging
import threading
import uuid
from dataclasses import dataclass, field
from typing import Callable, Literal, TypedDict

from sqlmodel import Session, select

from config.database import engine
from models.node import Node
from models.opening import Opening
from utils.evaluators import Evaluator, get_evaluator
from utils.seed_files import write_seed_file

logger = logging.getLogger(__name__)

JobState = Literal["running", "done", "cancelled", "error"]


@dataclass
class EvaluationJob:
    id: str
    opening_id: int
    total: int
    state: JobState = "running"
    done: int = 0
    errors: int = 0
    message: str | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)


class JobAlreadyRunning(RuntimeError):
    pass


class JobNotFound(RuntimeError):
    pass


class JobNotRunning(RuntimeError):
    pass


class JobStatus(TypedDict):
    state: JobState
    done: int
    total: int
    errors: int
    message: str | None


_jobs: dict[str, EvaluationJob] = {}
_active_by_opening: dict[int, str] = {}
_lock = threading.Lock()


def _set_state(
    job: EvaluationJob,
    state: JobState,
    message: str | None = None,
) -> None:
    with _lock:
        job.state = state
        job.message = message
        if (
            state != "running"
            and _active_by_opening.get(job.opening_id) == job.id
        ):
            _active_by_opening.pop(job.opening_id, None)


def _advance(
    job: EvaluationJob,
    *,
    done: int = 0,
    errors: int = 0,
    message: str | None = None,
) -> None:
    with _lock:
        job.done += done
        job.errors += errors
        if message is not None:
            job.message = message


def _is_missing(node: Node) -> bool:
    return node.eval_cp is None and node.eval_mate is None


def _apply_result(node: Node, result: dict[str, int]) -> None:
    if "cp" in result and "mate" not in result:
        node.eval_cp = int(result["cp"])
        node.eval_mate = None
    elif "mate" in result and "cp" not in result:
        node.eval_mate = int(result["mate"])
        node.eval_cp = None
    else:
        raise ValueError("El evaluador devolvio una valoracion invalida.")
    node.eval_source = "engine"


def _rewrite_seed(
    session: Session,
    opening_id: int,
    visibility: Literal["public", "private"] | None,
) -> None:
    if visibility is None:
        return
    opening = session.get(Opening, opening_id)
    if opening is None:
        return
    write_seed_file(session, opening, visibility)


def _run_job(
    job: EvaluationJob,
    node_ids: list[int],
    visibility: Literal["public", "private"] | None,
    evaluator_factory: Callable[[], Evaluator],
) -> None:
    session = Session(engine)
    evaluator: Evaluator | None = None
    try:
        evaluator = evaluator_factory()
        final_state: JobState = "done"
        final_message: str | None = None
        for node_id in node_ids:
            if job.cancel_event.is_set():
                final_state = "cancelled"
                final_message = "Valoracion cancelada."
                break

            node = session.get(Node, node_id)
            if node is None or not _is_missing(node):
                _advance(job, done=1)
                continue

            try:
                _apply_result(node, evaluator.evaluate(node.fen))
                session.add(node)
                session.commit()
            except Exception as exc:
                session.rollback()
                _advance(job, errors=1, message=str(exc))
            finally:
                _advance(job, done=1)

        _rewrite_seed(session, job.opening_id, visibility)
        _set_state(job, final_state, final_message)
    except Exception as exc:
        session.rollback()
        logger.exception("Evaluation job %s failed", job.id)
        _set_state(job, "error", str(exc))
    finally:
        if evaluator is not None:
            try:
                evaluator.close()
            except Exception:
                logger.exception("Could not close evaluator for job %s", job.id)
        with _lock:
            if _active_by_opening.get(job.opening_id) == job.id:
                _active_by_opening.pop(job.opening_id, None)
        session.close()


def start_evaluation_job(
    session: Session,
    opening_id: int,
    visibility: Literal["public", "private"] | None,
    evaluator_factory: Callable[[], Evaluator] | None = None,
) -> EvaluationJob | None:
    node_ids = list(
        session.exec(
            select(Node.id)
            .where(
                Node.opening_id == opening_id,
                Node.eval_cp.is_(None),
                Node.eval_mate.is_(None),
            )
            .order_by(Node.id)
        ).all()
    )
    if not node_ids:
        return None

    job = EvaluationJob(
        id=uuid.uuid4().hex,
        opening_id=opening_id,
        total=len(node_ids),
    )
    with _lock:
        if opening_id in _active_by_opening:
            raise JobAlreadyRunning(
                "Ya hay una valoracion en curso para esta apertura."
            )
        _jobs[job.id] = job
        _active_by_opening[opening_id] = job.id

    factory = evaluator_factory or get_evaluator
    thread = threading.Thread(
        target=_run_job,
        args=(job, node_ids, visibility, factory),
        daemon=True,
    )
    thread.start()
    return job


def get_job_status(job_id: str) -> JobStatus | None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        return {
            "state": job.state,
            "done": job.done,
            "total": job.total,
            "errors": job.errors,
            "message": job.message,
        }


def cancel_job(job_id: str) -> JobStatus:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            raise JobNotFound("El job no existe.")
        if job.state != "running":
            raise JobNotRunning("El job ya termino.")
        job.cancel_event.set()
        return {
            "state": job.state,
            "done": job.done,
            "total": job.total,
            "errors": job.errors,
            "message": job.message,
        }


def evaluation_status(
    session: Session,
    opening_id: int,
) -> tuple[int, int, bool, str | None]:
    total = len(
        session.exec(
            select(Node.id).where(Node.opening_id == opening_id)
        ).all()
    )
    missing = len(
        session.exec(
            select(Node.id).where(
                Node.opening_id == opening_id,
                Node.eval_cp.is_(None),
                Node.eval_mate.is_(None),
            )
        ).all()
    )
    with _lock:
        job_id = _active_by_opening.get(opening_id)
        running = job_id is not None
    return total, missing, running, job_id
