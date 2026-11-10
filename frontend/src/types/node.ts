export interface TreeNode {
  id: number;
  san: string | null;
  uci: string | null;
  fen: string;
  ply: number;
  order_index: number;
  comment: string | null;
  children: TreeNode[];
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
  comment: string | null;
}

export interface MovePayload {
  parent_id: number;
  move: string;
}