import { apiFetch } from "./client";
import type {
  TrainingAnswer,
  TrainingAnswerPayload,
  TrainingSession,
  TrainingSessionOptions,
} from "../types/training";

export function createTrainingSession(
  openingId: number,
  options: TrainingSessionOptions = {},
): Promise<TrainingSession> {
  return apiFetch<TrainingSession>("/training/sessions", {
    method: "POST",
    body: JSON.stringify({
      opening_id: openingId,
      mode: options.mode ?? "full",
      from_node_id: options.fromNodeId ?? null,
    }),
  });
}

export function getTrainingSession(
  sessionId: number,
): Promise<TrainingSession> {
  return apiFetch<TrainingSession>(`/training/sessions/${sessionId}`);
}

export function answerTrainingSession(
  sessionId: number,
  payload: TrainingAnswerPayload,
): Promise<TrainingAnswer> {
  return apiFetch<TrainingAnswer>(`/training/sessions/${sessionId}/answer`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}