import { apiFetch } from "./client";
import type { NodeRecommendations } from "../types/recommendation";

export function getRecommendations(
  nodeId: number,
): Promise<NodeRecommendations> {
  return apiFetch<NodeRecommendations>(
    `/nodes/${nodeId}/recommendations`,
  );
}
