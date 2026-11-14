export type OpeningColor = "white" | "black";

export type ImportConflict = "reject" | "replace" | "duplicate";

export type SeedVisibility = "public" | "private";

export type SeedFileState = "in_db" | "deleted_locally" | "new";

export interface SeedFileInfo {
  file_key: string;
  name: string;
  visibility: SeedVisibility;
  state: SeedFileState;
}

export interface OpeningSummary {
  id: number;
  name: string;
  color: OpeningColor;
  node_count: number;
  accuracy: number | null;
  in_seed: boolean;
  seed_visibility: SeedVisibility | null;
}

export interface OpeningCreatePayload {
  name: string;
  color: OpeningColor;
}

export interface OpeningRenamePayload {
  name: string;
}
export interface SeedFileResponse {
  path: string;
}

export interface OpeningPgnImportPayload {
  pgn: string;
  name?: string;
  color: OpeningColor;
}
