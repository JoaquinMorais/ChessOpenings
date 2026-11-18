import type { Evaluation } from "./evaluation";

export interface RecommendationMove {
  rank: number;
  uci: string;
  san: string;
  evaluation: Evaluation;
  depth: number | null;
  covered?: boolean;
}

export interface NodeRecommendations {
  node_id: number;
  fen: string;
  side_to_move: "white" | "black";
  moves: RecommendationMove[];
}

export const RECOMMENDATION_COLORS = [
  "#1e40af",
  "#2563eb",
  "#7dd3fc",
] as const;

export function recommendationColor(rank: number): string {
  if (rank <= 1) {
    return RECOMMENDATION_COLORS[0];
  }
  if (rank === 2) {
    return RECOMMENDATION_COLORS[1];
  }
  return RECOMMENDATION_COLORS[2];
}
