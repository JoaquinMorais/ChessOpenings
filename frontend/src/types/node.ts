import type { ClassificationKey } from "./classifications";
import type { Evaluation } from "./evaluation";

export interface TreeNode {
  id: number;
  san: string | null;
  uci: string | null;
  fen: string;
  ply: number;
  order_index: number;
  name: string | null;
  comment: string | null;
  classification: ClassificationKey | null;
  evaluation: Evaluation | null;
  children: TreeNode[];
}

export interface TranspositionInfo {
  node_id: number;
  path_san: string;
}

export interface NodeRead {
  id: number;
  opening_id: number;
  parent_id: number | null;
  move_san: string | null;
  move_uci: string | null;
  fen: string;
  ply: number;
  order_index: number;
  name: string | null;
  comment: string | null;
  classification: ClassificationKey | null;
  evaluation: Evaluation | null;
  transposition_of: TranspositionInfo | null;
}

export interface NodeUpdatePayload {
  name?: string | null;
  comment?: string | null;
  classification?: ClassificationKey | null;
  evaluation?: Evaluation | null;
}

export interface MovePayload {
  parent_id: number;
  move: string;
}