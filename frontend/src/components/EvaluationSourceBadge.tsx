import type { Evaluation } from "../types/evaluation";

const SOURCE_INFO = {
  manual: {
    label: "manual",
    title: "Valoración editada manualmente.",
  },
  engine: {
    label: "motor",
    title: "Valoración generada por el motor Stockfish.",
  },
  llm: {
    label: "IA",
    title:
      "Valoración generada por IA; puede ser poco confiable y no calcula tácticas.",
  },
} as const;

function EvaluationSourceBadge({
  evaluation,
}: {
  evaluation: Evaluation | null;
}) {
  if (!evaluation) {
    return null;
  }
  const source = evaluation.source ?? "manual";
  const info = SOURCE_INFO[source];
  return (
    <span
      className={`evaluation-source evaluation-source--${source}`}
      title={info.title}
    >
      {info.label}
    </span>
  );
}

export default EvaluationSourceBadge;
