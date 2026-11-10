import { apiFetch } from "./client";
import type { MovePayload, NodeRead, TreeNode } from "../types/node";

export function getTree(openingId: number): Promise<TreeNode> {
  return apiFetch<TreeNode>(`/openings/${openingId}/tree`);
}

export function addMove(
  openingId: number,
  payload: MovePayload,
): Promise<NodeRead> {
  return apiFetch<NodeRead>(`/openings/${openingId}/moves`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}