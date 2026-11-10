export interface PositionStat {
  node_id: number;
  path_san: string;
  attempts: number;
  correct: number;
  accuracy: number | null;
  last_practiced_at: string | null;
}

export interface OpeningStats {
  opening_id: number;
  accuracy: number | null;
  positions: PositionStat[];
}

export type SortDirection = "asc" | "desc";