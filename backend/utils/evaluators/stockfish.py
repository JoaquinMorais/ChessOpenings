from typing import Optional, TypedDict

import chess
import chess.engine


class EvaluationResult(TypedDict, total=False):
    cp: int
    mate: int


class StockfishEvaluator:
    is_external = False

    def __init__(self, path: str, movetime_ms: int) -> None:
        self.path = path
        self.movetime_ms = movetime_ms
        self._engine: Optional[chess.engine.SimpleEngine] = None

    def _get_engine(self) -> chess.engine.SimpleEngine:
        if self._engine is None:
            self._engine = chess.engine.SimpleEngine.popen_uci(self.path)
        return self._engine

    def evaluate(self, fen: str) -> EvaluationResult:
        engine = self._get_engine()
        board = chess.Board(fen)
        limit = chess.engine.Limit(time=max(self.movetime_ms, 1) / 1000)
        info = engine.analyse(board, limit)
        score = info.get("score")
        if score is None:
            raise RuntimeError("Stockfish no devolvio una valoracion.")

        white_score = score.white()
        if white_score.is_mate():
            mate = white_score.mate()
            if mate is None:
                raise RuntimeError("Stockfish devolvio un mate invalido.")
            if mate == 0:
                return {
                    "cp": -9999 if board.turn == chess.WHITE else 9999
                }
            return {"mate": int(mate)}

        cp = white_score.score()
        if cp is None:
            raise RuntimeError("Stockfish devolvio una evaluacion invalida.")
        return {"cp": max(-9999, min(9999, int(cp)))}

    def close(self) -> None:
        if self._engine is None:
            return
        try:
            self._engine.quit()
        finally:
            self._engine = None
