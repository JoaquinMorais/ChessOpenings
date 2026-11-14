from typing import Any, Optional

from pydantic import ValidationError

from schemas.node_schema import Evaluation


def evaluation_to_columns(
    evaluation: Evaluation | None,
) -> tuple[Optional[int], Optional[int]]:
    if evaluation is None:
        return None, None
    if "cp" in evaluation.model_fields_set:
        return evaluation.cp, None
    return None, evaluation.mate


def parse_evaluation(
    raw: Any,
    fen: str | None = None,
) -> Evaluation | None:
    if raw is None:
        return None

    if (
        isinstance(raw, dict)
        and raw.get("mate") == 0
        and raw.get("source") == "engine"
        and fen is not None
    ):
        fields = fen.split()
        side = fields[1] if len(fields) > 1 else "w"
        raw = {key: value for key, value in raw.items() if key != "mate"}
        raw["cp"] = -9999 if side == "w" else 9999

    try:
        return Evaluation.model_validate(raw)
    except ValidationError as exc:
        message = _validation_message(exc)
        raise ValueError(message) from exc


def _validation_message(exc: ValidationError) -> str:
    for error in exc.errors():
        message = str(error.get("msg") or "")
        prefix = "Value error, "
        if message.startswith(prefix):
            return message[len(prefix) :]

    return "La evaluacion debe ser un objeto con exactamente una clave: cp o mate."
