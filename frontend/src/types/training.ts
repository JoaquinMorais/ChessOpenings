export interface TrainingLeadInMove {
  uci: string;
  san: string | null;
  fast_forward: boolean;
}

export interface TrainingProgress {
  answered: number;
  total: number;
  pending: number;
}

export interface TrainingQuestionStep {
  kind: "question";
  node_id: number;
  fen: string;
  lead_in: TrainingLeadInMove[];
  phase: "traversal" | "review";
  progress: TrainingProgress;
}

export interface TrainingFinishedStep {
  kind: "finished";
  summary: {
    questions_total: number;
    first_try_correct: number;
    accuracy: number;
  };
}

export type TrainingStep = TrainingQuestionStep | TrainingFinishedStep;

export interface TrainingSession {
  id: number;
  opening_id: number;
  started_at: string;
  finished_at: string | null;
  questions_total: number;
  first_try_correct: number;
  step: TrainingStep | null;
}

export interface TrainingAnswerPayload {
  node_id: number;
  move: string;
}

export interface TrainingAnswer {
  correct: boolean;
  correct_move_san: string | null;
  correct_move_uci: string | null;
  next_step: TrainingStep;
}