from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    evaluator: Literal["stockfish", "llm"] = "stockfish"
    stockfish_path: str = "/usr/games/stockfish"
    eval_movetime_ms: int = 300
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_min_interval_s: float = 1.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()