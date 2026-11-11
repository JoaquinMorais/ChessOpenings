import type { Evaluation } from "../types/evaluation";

const CP_LIMIT = 99.99;
const MATE_LIMIT = 99;
const WHITE_ADVANTAGE_FACTOR = 0.00368208;

export class EvaluationParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "EvaluationParseError";
  }
}

export interface EvaluationPreset {
  label: string;
  description: string;
  evaluation: Evaluation;
}

export const EVAL_PRESETS: EvaluationPreset[] = [
  {
    label: "=",
    description: "Igualdad",
    evaluation: { cp: 0 },
  },
  {
    label: "⩲",
    description: "Blancas ligeramente mejor",
    evaluation: { cp: 50 },
  },
  {
    label: "±",
    description: "Blancas mejor",
    evaluation: { cp: 100 },
  },
  {
    label: "+-",
    description: "Blancas ganando",
    evaluation: { cp: 300 },
  },
  {
    label: "⩱",
    description: "Negras ligeramente mejor",
    evaluation: { cp: -50 },
  },
  {
    label: "∓",
    description: "Negras mejor",
    evaluation: { cp: -100 },
  },
  {
    label: "-+",
    description: "Negras ganando",
    evaluation: { cp: -300 },
  },
];

export function parseEvaluation(text: string): Evaluation | null {
  const value = text.trim();
  if (!value) {
    return null;
  }

  if (value === "=") {
    return { cp: 0 };
  }

  const mateMatch = value.match(/^([+-])?([M#])([+-])?(\d{1,3})$/i);
  if (mateMatch) {
    const [, prefixSign, , innerSign, digits] = mateMatch;
    const sign = prefixSign === "-" || innerSign === "-" ? -1 : 1;
    const mate = Number(digits) * sign;
    if (mate === 0 || Math.abs(mate) > MATE_LIMIT) {
      throw new EvaluationParseError(
        "El mate debe ser un número entre -99 y 99, distinto de 0.",
      );
    }
    return { mate };
  }

  if (/^[+-]?\d+[.,]\d{3,}$/.test(value)) {
    throw new EvaluationParseError(
      "La evaluación puede tener como máximo dos decimales.",
    );
  }

  if (!/^[+-]?\d+(?:[.,]\d{1,2})?$/.test(value)) {
    throw new EvaluationParseError(
      "Evaluación inválida. Usá un número, '=' o un mate como M3.",
    );
  }

  const pawns = Number(value.replace(",", "."));
  if (!Number.isFinite(pawns) || Math.abs(pawns) > CP_LIMIT) {
    throw new EvaluationParseError(
      "La evaluación debe estar entre -99.99 y 99.99 peones.",
    );
  }

  const cp = Math.round(pawns * 100);
  return { cp: cp === 0 ? 0 : cp };
}

export function formatEvaluation(evaluation: Evaluation | null): string {
  if (!evaluation) {
    return "Sin evaluacion";
  }

  if (typeof evaluation.mate === "number" && evaluation.mate !== 0) {
    return evaluation.mate > 0
      ? `M${evaluation.mate}`
      : `-M${Math.abs(evaluation.mate)}`;
  }

  if (typeof evaluation.cp === "number") {
    const pawns = evaluation.cp / 100;
    const absolute = Math.abs(pawns).toFixed(2);
    if (pawns > 0) {
      return `+${absolute}`;
    }
    if (pawns < 0) {
      return `-${absolute}`;
    }
    return absolute;
  }

  return "Sin evaluacion";
}

export function whitePercent(evaluation: Evaluation | null): number {
  if (!evaluation) {
    return 50;
  }

  if (typeof evaluation.mate === "number" && evaluation.mate !== 0) {
    return evaluation.mate > 0 ? 100 : 0;
  }

  if (typeof evaluation.cp === "number") {
    const percent =
      100 / (1 + Math.exp(-WHITE_ADVANTAGE_FACTOR * evaluation.cp));
    return Math.min(100, Math.max(0, percent));
  }

  return 50;
}

/*
Casos de referencia (no hay runner de tests frontend instalado):

parseEvaluation("0.35") -> { cp: 35 }
parseEvaluation("+0.35") -> { cp: 35 }
parseEvaluation("-1,2") -> { cp: -120 }
parseEvaluation("=") -> { cp: 0 }
parseEvaluation("0") -> { cp: 0 }
parseEvaluation("#3") -> { mate: 3 }
parseEvaluation("M3") -> { mate: 3 }
parseEvaluation("-M2") -> { mate: -2 }
parseEvaluation("#-2") -> { mate: -2 }
parseEvaluation("") -> null
parseEvaluation("abc") -> EvaluationParseError
parseEvaluation("100") -> EvaluationParseError
parseEvaluation("1.234") -> EvaluationParseError

formatEvaluation({ cp: 35 }) -> "+0.35"
formatEvaluation({ cp: -120 }) -> "-1.20"
formatEvaluation({ cp: 0 }) -> "0.00"
formatEvaluation({ mate: 3 }) -> "M3"
formatEvaluation({ mate: -2 }) -> "-M2"
formatEvaluation(null) -> "Sin evaluacion"

whitePercent(null) -> 50
whitePercent({ cp: 0 }) -> 50
whitePercent({ mate: 3 }) -> 100
whitePercent({ mate: -2 }) -> 0
whitePercent({ cp: 100 }) -> 59.0... (fórmula del documento)
*/
