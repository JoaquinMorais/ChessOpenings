import { apiFetch } from "./client";
import type {
  OpeningCreatePayload,
  OpeningRenamePayload,
  OpeningSummary,
} from "../types/opening";

export function listOpenings(): Promise<OpeningSummary[]> {
  return apiFetch<OpeningSummary[]>("/openings");
}

export function getOpening(openingId: number): Promise<OpeningSummary> {
  return apiFetch<OpeningSummary>(`/openings/${openingId}`);
}

export function createOpening(
  payload: OpeningCreatePayload,
): Promise<OpeningSummary> {
  return apiFetch<OpeningSummary>("/openings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function renameOpening(
  openingId: number,
  payload: OpeningRenamePayload,
): Promise<OpeningSummary> {
  return apiFetch<OpeningSummary>(`/openings/${openingId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteOpening(openingId: number): Promise<void> {
  return apiFetch<void>(`/openings/${openingId}`, {
    method: "DELETE",
  });
}