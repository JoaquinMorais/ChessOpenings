from typing import Protocol

from config.settings import settings
from utils.evaluators.stockfish import EvaluationResult, StockfishEvaluator


class EvaluatorConfigurationError(RuntimeError):
    pass


class Evaluator(Protocol):
    is_external: bool

    def evaluate(self, fen: str) -> EvaluationResult: ...

    def close(self) -> None: ...


def get_evaluator() -> Evaluator:
    if settings.evaluator == "stockfish":
        return StockfishEvaluator(
            settings.stockfish_path,
            settings.eval_movetime_ms,
        )
    raise EvaluatorConfigurationError(
        "El evaluator LLM no esta implementado todavia."
    )


def is_external_evaluator() -> bool:
    return settings.evaluator == "llm"


__all__ = [
    "Evaluator",
    "EvaluatorConfigurationError",
    "EvaluationResult",
    "StockfishEvaluator",
    "get_evaluator",
    "is_external_evaluator",
]
