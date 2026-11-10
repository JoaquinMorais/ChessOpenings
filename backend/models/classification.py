from enum import Enum


class Classification(str, Enum):
    BRILLIANT = "brilliant"
    GREAT = "great"
    BEST = "best"
    EXCELLENT = "excellent"
    GOOD = "good"
    BOOK = "book"
    INACCURACY = "inaccuracy"
    MISTAKE = "mistake"
    MISS = "miss"
    BLUNDER = "blunder"


CLASSIFICATION_META: dict[Classification, dict[str, str]] = {
    Classification.BRILLIANT: {
        "label": "Brillante",
        "symbol": "!!",
        "color": "#1baca6",
    },
    Classification.GREAT: {
        "label": "Gran jugada",
        "symbol": "!",
        "color": "#5c8bb0",
    },
    Classification.BEST: {
        "label": "Mejor jugada",
        "symbol": "★",
        "color": "#96bc4b",
    },
    Classification.EXCELLENT: {
        "label": "Excelente",
        "symbol": "✓",
        "color": "#81b64c",
    },
    Classification.GOOD: {
        "label": "Buena",
        "symbol": "•",
        "color": "#a0b090",
    },
    Classification.BOOK: {
        "label": "De libro",
        "symbol": "B",
        "color": "#a88865",
    },
    Classification.INACCURACY: {
        "label": "Imprecision",
        "symbol": "?!",
        "color": "#f7c631",
    },
    Classification.MISTAKE: {
        "label": "Error",
        "symbol": "?",
        "color": "#e58f2a",
    },
    Classification.MISS: {
        "label": "Oportunidad perdida",
        "symbol": "✗",
        "color": "#ff7769",
    },
    Classification.BLUNDER: {
        "label": "Error grave",
        "symbol": "??",
        "color": "#ca3431",
    },
}