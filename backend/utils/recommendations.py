import threading
from collections import OrderedDict

from config.settings import settings
from utils.recommenders import (
    RecommendationError,
    RecommendedMove,
    StockfishRecommender,
)

_CACHE_MAX = 128
_cache: OrderedDict[str, list[RecommendedMove]] = OrderedDict()
_lock = threading.Lock()


def get_recommendations(fen: str) -> list[RecommendedMove]:
    with _lock:
        cached = _cache.get(fen)
        if cached is not None:
            _cache.move_to_end(fen)
            return cached

        recommender = StockfishRecommender(
            settings.stockfish_path,
            settings.recommendation_movetime_ms,
        )
        try:
            moves = recommender.recommend(fen)
        except RecommendationError:
            raise
        except Exception as exc:
            raise RecommendationError(
                "No se pudieron obtener recomendaciones de Stockfish."
            ) from exc
        finally:
            recommender.close()

        _cache[fen] = moves
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)
        return moves


def clear_recommendations_cache() -> None:
    with _lock:
        _cache.clear()
