import { apiFetch, apiFetchText } from "./client";
import type {
  ImportConflict,
  OpeningCreatePayload,
  OpeningPgnImportPayload,
  OpeningRenamePayload,
  OpeningSummary,
  SeedFileResponse,
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

export function getOpeningExport(openingId: number): Promise<unknown> {
  return apiFetch<unknown>(`/openings/${openingId}/export`);
}

export function importOpening(
  payload: unknown,
  onConflict: ImportConflict = "reject",
): Promise<OpeningSummary> {
  const query = new URLSearchParams({ on_conflict: onConflict });
  return apiFetch<OpeningSummary>(`/openings/import?${query.toString()}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
export function saveOpeningSeed(
  openingId: number,
): Promise<SeedFileResponse> {
  return apiFetch<SeedFileResponse>(`/openings/${openingId}/seed`, {
    method: "POST",
  });
}

export function deleteOpeningSeed(openingId: number): Promise<void> {
  return apiFetch<void>(`/openings/${openingId}/seed`, {
    method: "DELETE",
  });
}

export function importOpeningPgn(
  payload: OpeningPgnImportPayload,
): Promise<OpeningSummary> {
  return apiFetch<OpeningSummary>("/openings/import-pgn", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getOpeningPgnExport(openingId: number): Promise<string> {
  return apiFetchText(`/openings/${openingId}/export.pgn`);
}
