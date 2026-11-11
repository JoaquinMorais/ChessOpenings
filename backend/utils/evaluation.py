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


def parse_evaluation(raw: Any) -> Evaluation | None:
    if raw is None:
        return None

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
