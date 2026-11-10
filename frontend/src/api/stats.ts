import { apiFetch } from "./client";
import type { OpeningStats } from "../types/stats";

export function getOpeningStats(openingId: number): Promise<OpeningStats> {
  return apiFetch<OpeningStats>(`/openings/${openingId}/stats`);
}