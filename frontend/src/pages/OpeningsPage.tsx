import { useCallback, useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import {
  createOpening,
  deleteOpening,
  getOpeningExport,
  importOpening,
  listOpenings,
  renameOpening,
} from "../api/openings";
import ImportConflictDialog from "../components/ImportConflictDialog";
import OpeningForm from "../components/OpeningForm";
import type { OpeningColor, OpeningSummary } from "../types/opening";

type ListState =
  | { status: "loading" }
  | { status: "ok"; openings: OpeningSummary[] }
  | { status: "error"; message: string };

type FormState =
  | { mode: "create" }
  | { mode: "rename"; opening: OpeningSummary }
  | null;

const COLOR_LABELS: Record<OpeningColor, string> = {
  white: "Blancas",
  black: "Negras",
};

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Ocurrió un error inesperado.";
}

function formatMoves(nodeCount: number): number {
  return Math.max(nodeCount - 1, 0);
}

function formatAccuracy(accuracy: number | null): string {
  return accuracy === null ? "—" : `${accuracy.toFixed(1)}%`;
}

function sanitizeFileName(name: string): string {
  const sanitized = name.replace(/[\\/:*?"<>|]/g, "_").trim();
  return sanitized || "opening";
}

function OpeningsPage() {
  const [list, setList] = useState<ListState>({ status: "loading" });
  const [form, setForm] = useState<FormState>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [exportingId, setExportingId] = useState<number | null>(null);
  const [ioError, setIoError] = useState<string | null>(null);
  const [ioSuccess, setIoSuccess] = useState<string | null>(null);
  const [pendingImport, setPendingImport] = useState<{
    payload: unknown;
    fileName: string;
  } | null>(null);
  const [importBusy, setImportBusy] = useState(false);
  const [conflictError, setConflictError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadOpenings = useCallback(async () => {
    setList({ status: "loading" });
    try {
      const openings = await listOpenings();
      setList({ status: "ok", openings });
    } catch (error) {
      setList({ status: "error", message: getErrorMessage(error) });
    }
  }, []);

  useEffect(() => {
    void loadOpenings();
  }, [loadOpenings]);

  const openCreateForm = () => {
    setForm({ mode: "create" });
    setFormError(null);
    setActionError(null);
  };

  const openRenameForm = (opening: OpeningSummary) => {
    setForm({ mode: "rename", opening });
    setFormError(null);
    setActionError(null);
  };

  const closeForm = () => {
    setForm(null);
    setFormError(null);
  };

  const handleSubmit = async (values: {
    name: string;
    color: OpeningColor;
  }) => {
    if (!form) {
      return;
    }

    setFormSubmitting(true);
    setFormError(null);
    try {
      if (form.mode === "create") {
        await createOpening({ name: values.name, color: values.color });
      } else {
        await renameOpening(form.opening.id, { name: values.name });
      }
      setForm(null);
      await loadOpenings();
    } catch (error) {
      setFormError(getErrorMessage(error));
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleDelete = async (opening: OpeningSummary) => {
    const confirmed = window.confirm(
      `¿Eliminar la apertura "${opening.name}"? Esta acción no se puede deshacer.`,
    );
    if (!confirmed) {
      return;
    }

    setDeletingId(opening.id);
    setActionError(null);
    try {
      await deleteOpening(opening.id);
      await loadOpenings();
    } catch (error) {
      setActionError(getErrorMessage(error));
    } finally {
      setDeletingId(null);
    }
  };

  const handleExport = async (opening: OpeningSummary) => {
    setExportingId(opening.id);
    setIoError(null);
    setIoSuccess(null);
    try {
      const data = await getOpeningExport(opening.id);
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${sanitizeFileName(opening.name)}.json`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
      setIoSuccess(`Apertura exportada: "${opening.name}".`);
    } catch (error) {
      setIoError(getErrorMessage(error));
    } finally {
      setExportingId(null);
    }
  };

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";

    if (!file) {
      return;
    }

    setIoError(null);
    setIoSuccess(null);

    let payload: unknown;
    try {
      payload = JSON.parse(await file.text());
    } catch {
      setIoError("El archivo no contiene un JSON válido.");
      return;
    }

    setImportBusy(true);
    try {
      const imported = await importOpening(payload);
      setIoSuccess(`Opening importado como "${imported.name}".`);
      await loadOpenings();
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setPendingImport({ payload, fileName: file.name });
        setConflictError(null);
      } else {
        setIoError(getErrorMessage(error));
      }
    } finally {
      setImportBusy(false);
    }
  };

  const handleConflict = async (mode: "replace" | "duplicate") => {
    if (!pendingImport) {
      return;
    }

    setImportBusy(true);
    setConflictError(null);
    try {
      const imported = await importOpening(pendingImport.payload, mode);
      setPendingImport(null);
      setIoError(null);
      setIoSuccess(`Opening importado como "${imported.name}".`);
      await loadOpenings();
    } catch (error) {
      setConflictError(getErrorMessage(error));
    } finally {
      setImportBusy(false);
    }
  };

  const handleCancelConflict = () => {
    if (importBusy) {
      return;
    }
    setPendingImport(null);
    setConflictError(null);
  };

  return (
    <section className="page">
      <div className="page-toolbar">
        <div className="page-heading">
          <p className="eyebrow">Repertorio</p>
          <h2>Aperturas</h2>
          <p>Gestiona tus repertorios y empieza a entrenar.</p>
        </div>
        <div className="toolbar-actions">
          <button
            type="button"
            className="button button--ghost"
            onClick={() => fileInputRef.current?.click()}
            disabled={importBusy || pendingImport !== null}
          >
            {importBusy ? "Importando..." : "Importar"}
          </button>
          <button type="button" className="button" onClick={openCreateForm}>
            Nuevo opening
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,application/json"
            className="file-input"
            onChange={(event) => void handleFileChange(event)}
          />
        </div>
      </div>

      {form && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="card-label">
                {form.mode === "create" ? "Nueva apertura" : "Renombrar"}
              </p>
              <h3>
                {form.mode === "create" ? "Crear opening" : form.opening.name}
              </h3>
            </div>
          </div>
          <OpeningForm
            key={
              form.mode === "create" ? "create" : `rename-${form.opening.id}`
            }
            mode={form.mode}
            initialName={form.mode === "rename" ? form.opening.name : ""}
            initialColor={
              form.mode === "rename" ? form.opening.color : "white"
            }
            submitting={formSubmitting}
            error={formError}
            onSubmit={(values) => void handleSubmit(values)}
            onCancel={closeForm}
          />
        </section>
      )}

      {actionError && (
        <div className="alert" role="alert">
          <p>{actionError}</p>
          <button type="button" onClick={() => setActionError(null)}>
            Cerrar
          </button>
        </div>
      )}

      {ioSuccess && (
        <div className="alert alert--success" role="status">
          <p>{ioSuccess}</p>
          <button type="button" onClick={() => setIoSuccess(null)}>
            Cerrar
          </button>
        </div>
      )}

      {ioError && (
        <div className="alert" role="alert">
          <p>{ioError}</p>
          <button type="button" onClick={() => setIoError(null)}>
            Cerrar
          </button>
        </div>
      )}

      {list.status === "loading" && (
        <p className="state-message">Cargando aperturas...</p>
      )}

      {list.status === "error" && (
        <div className="state-card state-card--error">
          <p>{list.message}</p>
          <button
            type="button"
            className="button"
            onClick={() => void loadOpenings()}
          >
            Reintentar
          </button>
        </div>
      )}

      {list.status === "ok" && list.openings.length === 0 && (
        <div className="state-card state-card--empty">
          <h3>No hay aperturas todavía</h3>
          <p>Crea tu primer opening para empezar a armar el repertorio.</p>
          <button type="button" className="button" onClick={openCreateForm}>
            Nuevo opening
          </button>
        </div>
      )}

      {list.status === "ok" && list.openings.length > 0 && (
        <ul className="opening-list">
          {list.openings.map((opening) => (
            <li key={opening.id} className="opening-card">
              <div className="opening-summary">
                <span
                  className={`color-icon color-icon--${opening.color}`}
                  role="img"
                  aria-label={COLOR_LABELS[opening.color]}
                />
                <div>
                  <h3>{opening.name}</h3>
                  <p className="opening-meta">
                    <span>{COLOR_LABELS[opening.color]}</span>
                    <span>{formatMoves(opening.node_count)} jugadas</span>
                    <span>Acierto: {formatAccuracy(opening.accuracy)}</span>
                  </p>
                </div>
              </div>

              <div className="opening-actions">
                <Link
                  className="button button--small"
                  to={`/openings/${opening.id}/edit`}
                >
                  Editar
                </Link>
                <Link
                  className="button button--small"
                  to={`/openings/${opening.id}/train`}
                >
                  Entrenar
                </Link>
                <Link
                  className="button button--small button--ghost"
                  to={`/openings/${opening.id}/stats`}
                >
                  Estadísticas
                </Link>
                <button
                  type="button"
                  className="button button--small button--ghost"
                  onClick={() => void handleExport(opening)}
                  disabled={exportingId === opening.id}
                >
                  {exportingId === opening.id ? "Exportando..." : "Exportar"}
                </button>
                <button
                  type="button"
                  className="button button--small button--ghost"
                  onClick={() => openRenameForm(opening)}
                >
                  Renombrar
                </button>
                <button
                  type="button"
                  className="button button--small button--danger"
                  onClick={() => void handleDelete(opening)}
                  disabled={deletingId === opening.id}
                >
                  {deletingId === opening.id ? "Eliminando..." : "Eliminar"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {pendingImport && (
        <ImportConflictDialog
          fileName={pendingImport.fileName}
          busy={importBusy}
          error={conflictError}
          onReplace={() => void handleConflict("replace")}
          onDuplicate={() => void handleConflict("duplicate")}
          onCancel={handleCancelConflict}
        />
      )}
    </section>
  );
}

export default OpeningsPage;