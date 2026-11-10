export type OpeningColor = "white" | "black";

export interface OpeningSummary {
  id: number;
  name: string;
  color: OpeningColor;
  node_count: number;
  accuracy: number | null;
}

export interface OpeningCreatePayload {
  name: string;
  color: OpeningColor;
}

export interface OpeningRenamePayload {
  name: string;
}