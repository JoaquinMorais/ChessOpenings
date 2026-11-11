import type { ClassificationKey } from "./classifications";
import type { Evaluation } from "./evaluation";

export type TrainingMode = "full" | "weak";

export interface TrainingSessionOptions {
  mode?: TrainingMode;
  fromNodeId?: number | null;
}

export interface TrainingMoveInfo {
  id?: number;
  uci: string | null;
  san: string | null;
  name: string | null;
  comment: string | null;
  classification: ClassificationKey | null;
  evaluation: Evaluation | null;
}

export interface TrainingLeadInMove extends TrainingMoveInfo {
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
  evaluation: Evaluation | null;
  lead_in: TrainingLeadInMove[];
  correct_move: TrainingMoveInfo;
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
  hint_used?: boolean;
}

export interface TrainingAnswer {
  correct: boolean;
  correct_move_san: string | null;
  correct_move_uci: string | null;
  correct_move: TrainingMoveInfo;
  next_step: TrainingStep;
}