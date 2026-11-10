export type ClassificationKey =
  | "brilliant"
  | "great"
  | "best"
  | "excellent"
  | "good"
  | "book"
  | "inaccuracy"
  | "mistake"
  | "miss"
  | "blunder";

export interface ClassificationDefinition {
  key: ClassificationKey;
  label: string;
  symbol: string;
  color: string;
}

export const CLASSIFICATIONS: ClassificationDefinition[] = [
  { key: "brilliant", label: "Brillante", symbol: "!!", color: "#1baca6" },
  { key: "great", label: "Gran jugada", symbol: "!", color: "#5c8bb0" },
  { key: "best", label: "Mejor jugada", symbol: "★", color: "#96bc4b" },
  { key: "excellent", label: "Excelente", symbol: "✓", color: "#81b64c" },
  { key: "good", label: "Buena", symbol: "•", color: "#a0b090" },
  { key: "book", label: "De libro", symbol: "B", color: "#a88865" },
  { key: "inaccuracy", label: "Imprecision", symbol: "?!", color: "#f7c631" },
  { key: "mistake", label: "Error", symbol: "?", color: "#e58f2a" },
  { key: "miss", label: "Oportunidad perdida", symbol: "✗", color: "#ff7769" },
  { key: "blunder", label: "Error grave", symbol: "??", color: "#ca3431" },
];

const CLASSIFICATIONS_BY_KEY = new Map(
  CLASSIFICATIONS.map((classification) => [classification.key, classification]),
);

export function getClassification(
  key: string | null | undefined,
): ClassificationDefinition | null {
  if (!key) {
    return null;
  }
  return CLASSIFICATIONS_BY_KEY.get(key as ClassificationKey) ?? null;
}