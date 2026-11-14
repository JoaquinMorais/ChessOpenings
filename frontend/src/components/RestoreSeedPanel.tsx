import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../api/client";
import { listSeedFiles, restoreSeedFile } from "../api/openings";
import type { SeedFileInfo, SeedFileState } from "../types/opening";

interface RestoreSeedPanelProps {
  onRestored: () => void | Promise<void>;
  onClose: () => void;
}

type FilesState =
  | { status: "loading" }
  | { status: "ok"; files: SeedFileInfo[] }
  | { status: "error"; message: string };

const STATE_LABELS: Record<SeedFileState, string> = {
  in_db: "En la base",
  deleted_locally: "Borrada localmente",
  new: "Nueva",
};

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Ocurrió un error inesperado.";
}

function RestoreSeedPanel({
  onRestored,
  onClose,
}: RestoreSeedPanelProps) {
  const [filesState, setFilesState] = useState<FilesState>({
    status: "loading",
  });
  const [restoringKey, setRestoringKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadFiles = useCallback(async () => {
    setFilesState({ status: "loading" });
    try {
      const files = await listSeedFiles();
      setFilesState({
        status: "ok",
        files: files.filter((file) => file.state !== "in_db"),
      });
    } catch (loadError) {
      setFilesState({
        status: "error",
        message: getErrorMessage(loadError),
      });
    }
  }, []);

  useEffect(() => {
    void loadFiles();
  }, [loadFiles]);

  const handleRestore = async (file: SeedFileInfo) => {
    setRestoringKey(file.file_key);
    setError(null);
    setSuccess(null);
    try {
      const restored = await restoreSeedFile(file.file_key);
      setSuccess(`Apertura restaurada: "${restored.name}".`);
      await loadFiles();
      await onRestored();
    } catch (restoreError) {
      setError(getErrorMessage(restoreError));
    } finally {
      setRestoringKey(null);
    }
  };

  return (
    <section className="panel restore-panel">
      <div className="restore-panel-heading">
        <div>
          <p className="card-label">Seed</p>
          <h3>Restaurar desde seed</h3>
          <p className="restore-panel-description">
            Archivos del seed que no están en la base o que borraste
            localmente.
          </p>
        </div>
        <button
          type="button"
          className="button button--small button--ghost"
          onClick={onClose}
        >
          Cerrar
        </button>
      </div>

      {success && (
        <div className="alert alert--success" role="status">
          <p>{success}</p>
          <button type="button" onClick={() => setSuccess(null)}>
            Cerrar
          </button>
        </div>
      )}

      {error && (
        <div className="alert" role="alert">
          <p>{error}</p>
          <button type="button" onClick={() => setError(null)}>
            Cerrar
          </button>
        </div>
      )}

      {filesState.status === "loading" && (
        <p className="state-message">Cargando archivos del seed...</p>
      )}

      {filesState.status === "error" && (
        <div className="state-card state-card--error">
          <p>{filesState.message}</p>
          <button
            type="button"
            className="button"
            onClick={() => void loadFiles()}
          >
            Reintentar
          </button>
        </div>
      )}

      {filesState.status === "ok" && filesState.files.length === 0 && (
        <p className="state-message">
          No hay archivos pendientes de restaurar.
        </p>
      )}

      {filesState.status === "ok" && filesState.files.length > 0 && (
        <ul className="restore-list">
          {filesState.files.map((file) => (
            <li key={file.file_key} className="restore-item">
              <div className="restore-item-main">
                <h4>{file.name}</h4>
                <div className="restore-meta">
                  <span
                    className={`seed-badge seed-badge--${file.visibility}`}
                  >
                    {file.visibility === "public" ? "Publica" : "Privada"}
                  </span>
                  <span className="restore-state">
                    {STATE_LABELS[file.state]}
                  </span>
                </div>
              </div>
              <button
                type="button"
                className="button button--small"
                onClick={() => void handleRestore(file)}
                disabled={restoringKey !== null}
              >
                {restoringKey === file.file_key
                  ? "Restaurando..."
                  : "Restaurar"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default RestoreSeedPanel;
