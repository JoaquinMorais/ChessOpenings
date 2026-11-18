from typing import Optional, TypedDict

import chess
import chess.engine

from utils.evaluators.stockfish import EvaluationResult


class RecommendationError(RuntimeError):
    pass


class RecommendedMove(TypedDict):
    rank: int
    uci: str
    san: str
    evaluation: EvaluationResult
    depth: Optional[int]


def _score_to_evaluation(
    score: chess.engine.PovScore,
    board: chess.Board,
) -> EvaluationResult:
    white_score = score.white()
    if white_score.is_mate():
        mate = white_score.mate()
        if mate is None:
            raise RecommendationError(
                "Stockfish devolvio un mate invalido."
            )
        if mate == 0:
            return {
                "cp": -9999 if board.turn == chess.WHITE else 9999
            }
        return {"mate": int(mate)}

    cp = white_score.score()
    if cp is None:
        raise RecommendationError(
            "Stockfish devolvio una evaluacion invalida."
        )
    return {"cp": max(-9999, min(9999, int(cp)))}


class StockfishRecommender:
    def __init__(
        self,
        path: str,
        movetime_ms: int,
        multipv: int = 3,
    ) -> None:
        self.path = path
        self.movetime_ms = movetime_ms
        self.multipv = multipv
        self._engine: Optional[chess.engine.SimpleEngine] = None

    def _get_engine(self) -> chess.engine.SimpleEngine:
        if self._engine is None:
            self._engine = chess.engine.SimpleEngine.popen_uci(self.path)
        return self._engine

    def recommend(self, fen: str) -> list[RecommendedMove]:
        board = chess.Board(fen)
        if board.is_game_over():
            return []

        engine = self._get_engine()
        limit = chess.engine.Limit(
            time=max(self.movetime_ms, 1) / 1000
        )
        infos = engine.analyse(
            board,
            limit,
            multipv=self.multipv,
        )
        if isinstance(infos, dict):
            infos = [infos]

        moves: list[RecommendedMove] = []
        for index, info in enumerate(infos):
            score = info.get("score")
            pv = info.get("pv") or []
            if score is None or not pv:
                continue
            move = pv[0]
            if move not in board.legal_moves:
                continue
            moves.append(
                {
                    "rank": int(info.get("multipv", index + 1)),
                    "uci": move.uci(),
                    "san": board.san(move),
                    "evaluation": _score_to_evaluation(score, board),
                    "depth": info.get("depth"),
                }
            )

        moves.sort(key=lambda item: item["rank"])
        return moves[: self.multipv]

    def close(self) -> None:
        if self._engine is None:
            return
        try:
            self._engine.quit()
        finally:
            self._engine = None
