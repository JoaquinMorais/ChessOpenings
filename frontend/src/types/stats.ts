export interface PositionStat {
  node_id: number;
  path_san: string;
  attempts: number;
  correct: number;
  accuracy: number | null;
  last_practiced_at: string | null;
}

export interface TrainingSessionSummary {
  id: number;
  started_at: string;
  finished_at: string;
  questions_total: number;
  first_try_correct: number;
  accuracy: number;
}

export interface OpeningStats {
  opening_id: number;
  accuracy: number | null;
  positions: PositionStat[];
  sessions: TrainingSessionSummary[];
}

export type SortDirection = "asc" | "desc";