import { apiFetch } from "./client";
import type {
  MovePayload,
  NodeRead,
  NodeUpdatePayload,
  TreeNode,
} from "../types/node";

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

export function makeMain(nodeId: number): Promise<NodeRead> {
  return apiFetch<NodeRead>(`/nodes/${nodeId}/make-main`, {
    method: "POST",
  });
}

export function deleteNode(nodeId: number): Promise<void> {
  return apiFetch<void>(`/nodes/${nodeId}`, {
    method: "DELETE",
  });
}
export function updateNode(
  nodeId: number,
  payload: NodeUpdatePayload,
): Promise<NodeRead> {
  return apiFetch<NodeRead>(`/nodes/${nodeId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
