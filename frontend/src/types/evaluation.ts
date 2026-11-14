export type Evaluation = {
  cp?: number | null;
  mate?: number | null;
  source?: "manual" | "engine" | "llm";
};

export type EvaluationJobState = "running" | "done" | "cancelled" | "error";

export interface EvaluationStatus {
  total: number;
  missing: number;
  running: boolean;
  job_id: string | null;
  evaluator: "stockfish" | "llm";
}

export interface EvaluationJob {
  state: EvaluationJobState;
  done: number;
  total: number;
  errors: number;
  message: string | null;
}

export interface TrackedEvaluationJob extends EvaluationJob {
  jobId: string;
  openingId: number;
  openingName: string;
}
