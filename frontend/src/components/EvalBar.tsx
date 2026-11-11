import type { Evaluation } from "../types/evaluation";
import {
  formatEvaluation,
  whitePercent,
} from "../utils/evaluation";

interface EvalBarProps {
  evaluation: Evaluation | null;
  orientation: "white" | "black";
  showLabel?: boolean;
}

function hasEvaluation(evaluation: Evaluation | null): boolean {
  if (!evaluation) {
    return false;
  }
  return (
    typeof evaluation.cp === "number" ||
    (typeof evaluation.mate === "number" && evaluation.mate !== 0)
  );
}

function describeEvaluation(evaluation: Evaluation | null): string {
  if (!hasEvaluation(evaluation) || !evaluation) {
    return "Sin evaluacion";
  }

  const value = formatEvaluation(evaluation);
  if (typeof evaluation.mate === "number" && evaluation.mate !== 0) {
    const side = evaluation.mate > 0 ? "blancas" : "negras";
    return `Evaluacion: ${value} (mate de las ${side} en ${Math.abs(
      evaluation.mate,
    )})`;
  }

  if (typeof evaluation.cp === "number") {
    if (evaluation.cp > 0) {
      return `Evaluacion: ${value} (ventaja de las blancas)`;
    }
    if (evaluation.cp < 0) {
      return `Evaluacion: ${value} (ventaja de las negras)`;
    }
    return `Evaluacion: ${value} (posicion igualada)`;
  }

  return "Sin evaluacion";
}

function EvalBar({
  evaluation,
  orientation,
  showLabel = true,
}: EvalBarProps) {
  const percent = whitePercent(evaluation);
  const labelOnWhiteSide = percent >= 50;
  const labelAtTop =
    orientation === "white" ? !labelOnWhiteSide : labelOnWhiteSide;
  const label = hasEvaluation(evaluation)
    ? formatEvaluation(evaluation)
    : null;
  const description = describeEvaluation(evaluation);

  return (
    <div
      className={[
        "eval-bar",
        orientation === "black" ? "eval-bar--black" : "",
        hasEvaluation(evaluation) ? "" : "eval-bar--empty",
      ]
        .filter(Boolean)
        .join(" ")}
      role="img"
      aria-label={description}
      title={description}
    >
      <div className="eval-bar__zones">
        <div
          className="eval-bar__zone eval-bar__zone--black"
          style={{ flexBasis: `${100 - percent}%` }}
        />
        <div
          className="eval-bar__zone eval-bar__zone--white"
          style={{ flexBasis: `${percent}%` }}
        />
      </div>

      {showLabel && label && (
        <span
          className={[
            "eval-bar__label",
            labelAtTop ? "eval-bar__label--top" : "eval-bar__label--bottom",
            labelOnWhiteSide
              ? "eval-bar__label--white"
              : "eval-bar__label--black",
          ].join(" ")}
        >
          {label}
        </span>
      )}
    </div>
  );
}

export default EvalBar;
