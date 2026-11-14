import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useEvaluationJobs } from "../contexts/EvaluationJobsContext";
import {
  createOpening,
  deleteOpening,
  deleteOpeningSeed,
  getOpeningExport,
  getOpeningPgnExport,
  importOpening,
  importOpeningPgn,
  listOpenings,
  renameOpening,
  saveOpeningSeed,
  setOpeningFavorite,
} from "../api/openings";
import DeleteSeedDialog from "../components/DeleteSeedDialog";
import EvaluationJobProgress from "../components/EvaluationJobProgress";
import FavoriteButton from "../components/FavoriteButton";
import ImportConflictDialog from "../components/ImportConflictDialog";
import ImportPgnDialog from "../components/ImportPgnDialog";
import OpeningForm from "../components/OpeningForm";
import RemoveSeedDialog from "../components/RemoveSeedDialog";
import RestoreSeedPanel from "../components/RestoreSeedPanel";
import SaveSeedDialog from "../components/SaveSeedDialog";
import type {
  OpeningColor,
  OpeningPgnImportPayload,
  OpeningSummary,
  SeedSaveOptions,
} from "../types/opening";

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
  const navigate = useNavigate();
  const [list, setList] = useState<ListState>({ status: "loading" });
  const [form, setForm] = useState<FormState>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [exportingId, setExportingId] = useState<number | null>(null);
  const [exportingPgnId, setExportingPgnId] = useState<number | null>(null);
  const [pgnDialogOpen, setPgnDialogOpen] = useState(false);
  const [pgnImporting, setPgnImporting] = useState(false);
  const [pgnError, setPgnError] = useState<string | null>(null);
  const [seedingId, setSeedingId] = useState<number | null>(null);
  const [favoriteBusyId, setFavoriteBusyId] = useState<number | null>(null);
  const [pendingSeedSave, setPendingSeedSave] =
    useState<OpeningSummary | null>(null);
  const [seedSaveError, setSeedSaveError] = useState<string | null>(null);
  const [seedSaveExternalRequired, setSeedSaveExternalRequired] =
    useState(false);
  const [seedSaveJobId, setSeedSaveJobId] = useState<string | null>(null);
  const [removingSeedId, setRemovingSeedId] = useState<number | null>(null);
  const [pendingSeedRemove, setPendingSeedRemove] =
    useState<OpeningSummary | null>(null);
  const [removeSeedError, setRemoveSeedError] = useState<string | null>(null);
  const [pendingSeedDelete, setPendingSeedDelete] =
    useState<OpeningSummary | null>(null);
  const [deleteSeedError, setDeleteSeedError] = useState<string | null>(null);
  const [showRestore, setShowRestore] = useState(false);
  const [ioError, setIoError] = useState<string | null>(null);
  const [ioSuccess, setIoSuccess] = useState<string | null>(null);
  const [pendingImport, setPendingImport] = useState<{
    payload: unknown;
    fileName: string;
  } | null>(null);
  const [importBusy, setImportBusy] = useState(false);
  const [conflictError, setConflictError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { jobs, trackJob, cancelJob, lastFinished } =
    useEvaluationJobs();

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

  useEffect(() => {
    if (!lastFinished) {
      return;
    }
    if (lastFinished.state === "error") {
      setIoError(
        lastFinished.message ?? "No se pudo completar la valoración.",
      );
      return;
    }
    if (lastFinished.state === "cancelled") {
      setIoSuccess("Valoración cancelada.");
      return;
    }
    if (lastFinished.state === "done") {
      setIoSuccess(
        lastFinished.errors > 0
          ? `Valoración completada con ${lastFinished.errors} errores.`
          : "Valoración completada.",
      );
    }
  }, [lastFinished]);

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
        const created = await createOpening({
          name: values.name,
          color: values.color,
        });
        setForm(null);
        navigate(`/openings/${created.id}/edit`);
        return;
      }

      await renameOpening(form.opening.id, { name: values.name });
      setForm(null);
      await loadOpenings();
    } catch (error) {
      setFormError(getErrorMessage(error));
    } finally {
      setFormSubmitting(false);
    }
  };

  const performDelete = async (
    opening: OpeningSummary,
    deleteSeed: boolean,
    showDialogError: boolean,
  ): Promise<boolean> => {
    setDeletingId(opening.id);
    if (showDialogError) {
      setDeleteSeedError(null);
    } else {
      setActionError(null);
    }

    try {
      if (opening.in_seed) {
        await deleteOpening(
          opening.id,
          deleteSeed ? "both" : "local",
        );
      } else {
        await deleteOpening(opening.id);
      }
      return true;
    } catch (error) {
      const message = getErrorMessage(error);
      if (showDialogError) {
        setDeleteSeedError(message);
      } else {
        setActionError(message);
      }
      return false;
    } finally {
      setDeletingId(null);
    }
  };

  const handleDelete = async (opening: OpeningSummary) => {
    if (opening.in_seed) {
      setPendingSeedDelete(opening);
      setDeleteSeedError(null);
      return;
    }

    const confirmed = window.confirm(
      `¿Eliminar la apertura "${opening.name}"? Esta acción no se puede deshacer.`,
    );
    if (!confirmed) {
      return;
    }

    if (await performDelete(opening, false, false)) {
      await loadOpenings();
    }
  };

  const handleSeedDelete = async (deleteSeed: boolean) => {
    if (!pendingSeedDelete) {
      return;
    }

    if (await performDelete(pendingSeedDelete, deleteSeed, true)) {
      setPendingSeedDelete(null);
      setDeleteSeedError(null);
      await loadOpenings();
    }
  };

  const handleCancelSeedDelete = () => {
    if (deletingId !== null) {
      return;
    }
    setPendingSeedDelete(null);
    setDeleteSeedError(null);
  };

  const openSeedSaveDialog = (opening: OpeningSummary) => {
    setPendingSeedSave(opening);
    setSeedSaveError(null);
    setSeedSaveExternalRequired(false);
    setSeedSaveJobId(null);
  };

  const handleCancelSeedSave = () => {
    if (seedingId !== null) {
      return;
    }
    setPendingSeedSave(null);
    setSeedSaveError(null);
    setSeedSaveExternalRequired(false);
    setSeedSaveJobId(null);
  };

  const handleSeedSaveSubmit = async (options: SeedSaveOptions) => {
    if (!pendingSeedSave) {
      return;
    }

    const opening = pendingSeedSave;
    setSeedingId(opening.id);
    setSeedSaveError(null);
    setSeedSaveExternalRequired(false);
    setIoError(null);
    setIoSuccess(null);
    try {
      const result = await saveOpeningSeed(
        opening.id,
        options.visibility,
        {
          evaluate: options.evaluate,
          allow_external: options.allow_external,
        },
      );
      if (result.job_id) {
        trackJob(
          { id: opening.id, name: opening.name },
          result.job_id,
          options.total,
        );
        setSeedSaveJobId(result.job_id);
        return;
      }
      setPendingSeedSave(null);
      setSeedSaveJobId(null);
      setIoSuccess(result.message ?? `Guardado en ${result.path}.`);
      await loadOpenings();
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.status === 409 &&
        error.message.toLowerCase().includes("allow_external") &&
        !options.allow_external
      ) {
        setSeedSaveExternalRequired(true);
      } else {
        setSeedSaveError(getErrorMessage(error));
      }
    } finally {
      setSeedingId(null);
    }
  };

  const handleToggleFavorite = async (opening: OpeningSummary) => {
    setFavoriteBusyId(opening.id);
    setActionError(null);
    try {
      const updated = await setOpeningFavorite(
        opening.id,
        !opening.is_favorite,
      );
      setList((current) => {
        if (current.status !== "ok") {
          return current;
        }
        return {
          status: "ok",
          openings: current.openings.map((item) =>
            item.id === updated.id ? updated : item,
          ),
        };
      });
      const openings = await listOpenings();
      setList({ status: "ok", openings });
    } catch (error) {
      setActionError(getErrorMessage(error));
    } finally {
      setFavoriteBusyId(null);
    }
  };

  const openSeedRemoveDialog = (opening: OpeningSummary) => {
    setPendingSeedRemove(opening);
    setRemoveSeedError(null);
  };

  const handleCancelSeedRemove = () => {
    if (removingSeedId !== null) {
      return;
    }
    setPendingSeedRemove(null);
    setRemoveSeedError(null);
  };

  const handleConfirmSeedRemove = async () => {
    if (!pendingSeedRemove) {
      return;
    }

    const opening = pendingSeedRemove;
    setRemovingSeedId(opening.id);
    setRemoveSeedError(null);
    setIoError(null);
    setIoSuccess(null);
    try {
      await deleteOpeningSeed(opening.id);
      setPendingSeedRemove(null);
      setIoSuccess(`"${opening.name}" quitado del seed.`);
      await loadOpenings();
    } catch (error) {
      setRemoveSeedError(getErrorMessage(error));
    } finally {
      setRemovingSeedId(null);
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

  const handleExportPgn = async (opening: OpeningSummary) => {
    setExportingPgnId(opening.id);
    setIoError(null);
    setIoSuccess(null);
    try {
      const content = await getOpeningPgnExport(opening.id);
      const blob = new Blob([content], {
        type: "application/x-chess-pgn",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${sanitizeFileName(opening.name)}.pgn`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
      setIoSuccess(`PGN exportado: "${opening.name}".`);
    } catch (error) {
      setIoError(getErrorMessage(error));
    } finally {
      setExportingPgnId(null);
    }
  };

  const handlePgnImport = async (payload: OpeningPgnImportPayload) => {
    setPgnImporting(true);
    setPgnError(null);
    setIoError(null);
    setIoSuccess(null);
    try {
      const imported = await importOpeningPgn(payload);
      setPgnDialogOpen(false);
      setIoSuccess(`Opening PGN importado como "${imported.name}".`);
      await loadOpenings();
    } catch (error) {
      setPgnError(getErrorMessage(error));
    } finally {
      setPgnImporting(false);
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

  const firstNonFavoriteIndex =
    list.status === "ok"
      ? list.openings.findIndex((opening) => !opening.is_favorite)
      : -1;
  const activeSeedJob = seedSaveJobId
    ? jobs[seedSaveJobId] ?? null
    : null;

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
          <button
            type="button"
            className="button button--ghost"
            onClick={() => {
              setPgnDialogOpen(true);
              setPgnError(null);
            }}
          >
            Importar PGN
          </button>
          <button
            type="button"
            className="button button--ghost"
            onClick={() => setShowRestore((visible) => !visible)}
          >
            {showRestore ? "Ocultar restauración" : "Restaurar desde seed"}
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

      {showRestore && (
        <RestoreSeedPanel
          onRestored={loadOpenings}
          onClose={() => setShowRestore(false)}
        />
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
          {list.openings.map((opening, index) => {
            const runningJob = Object.values(jobs).find(
              (job) =>
                job.openingId === opening.id && job.state === "running",
            );
            return (
            <Fragment key={opening.id}>
              {index === firstNonFavoriteIndex &&
                firstNonFavoriteIndex > 0 && (
                  <li
                    className="opening-list-separator"
                    aria-hidden="true"
                  />
                )}
              <li className="opening-card">
                <div className="opening-summary">
                  <span
                    className={`color-icon color-icon--${opening.color}`}
                    role="img"
                    aria-label={COLOR_LABELS[opening.color]}
                  />
                  <div>
                    <div className="opening-title-row">
                      <h3>
                        {opening.name}
                        {opening.seed_visibility && (
                          <span
                            className={`seed-badge seed-badge--${opening.seed_visibility}`}
                          >
                            {opening.seed_visibility === "public"
                              ? "Publica"
                              : "Privada"}
                          </span>
                        )}
                      </h3>
                      <FavoriteButton
                        isFavorite={opening.is_favorite}
                        busy={favoriteBusyId === opening.id}
                        onToggle={() => void handleToggleFavorite(opening)}
                      />
                    </div>
                    <p className="opening-meta">
                      <span>{COLOR_LABELS[opening.color]}</span>
                      <span>{formatMoves(opening.node_count)} jugadas</span>
                      <span>
                        Acierto: {formatAccuracy(opening.accuracy)}
                      </span>
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
                  onClick={() => void handleExportPgn(opening)}
                  disabled={exportingPgnId === opening.id}
                >
                  {exportingPgnId === opening.id
                    ? "Exportando PGN..."
                    : "Exportar PGN"}
                </button>
                <button
                  type="button"
                  className="button button--small button--ghost"
                  onClick={() => openSeedSaveDialog(opening)}
                  disabled={
                    seedingId === opening.id ||
                    removingSeedId === opening.id
                  }
                >
                  {seedingId === opening.id
                    ? "Guardando..."
                    : opening.in_seed
                      ? "Actualizar seed"
                      : "Guardar en seed"}
                </button>
                {opening.in_seed && (
                  <button
                    type="button"
                    className="button button--small button--ghost"
                    onClick={() => openSeedRemoveDialog(opening)}
                    disabled={
                      seedingId === opening.id ||
                      removingSeedId === opening.id
                    }
                  >
                    {removingSeedId === opening.id
                      ? "Quitando..."
                      : "Quitar del seed"}
                  </button>
                )}
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
                {runningJob && (
                  <EvaluationJobProgress
                    job={runningJob}
                    onCancel={cancelJob}
                    compact
                  />
                )}
              </li>
            </Fragment>
            );
          })}
        </ul>
      )}

      {pgnDialogOpen && (
        <ImportPgnDialog
          busy={pgnImporting}
          error={pgnError}
          onImport={(payload) => void handlePgnImport(payload)}
          onCancel={() => {
            if (pgnImporting) {
              return;
            }
            setPgnDialogOpen(false);
            setPgnError(null);
          }}
        />
      )}

      {pendingSeedDelete && (
        <DeleteSeedDialog
          openingName={pendingSeedDelete.name}
          seedVisibility={pendingSeedDelete.seed_visibility}
          busy={deletingId === pendingSeedDelete.id}
          error={deleteSeedError}
          onDeleteOnly={() => void handleSeedDelete(false)}
          onDeleteWithSeed={() => void handleSeedDelete(true)}
          onCancel={handleCancelSeedDelete}
        />
      )}

      {pendingSeedSave && (
        <SaveSeedDialog
          key={pendingSeedSave.id}
          openingId={pendingSeedSave.id}
          openingName={pendingSeedSave.name}
          initialVisibility={pendingSeedSave.seed_visibility}
          busy={seedingId === pendingSeedSave.id}
          error={seedSaveError}
          externalRequired={seedSaveExternalRequired}
          job={activeSeedJob}
          onSubmit={(options) => void handleSeedSaveSubmit(options)}
          onCancelJob={cancelJob}
          onCancel={handleCancelSeedSave}
        />
      )}

      {pendingSeedRemove && (
        <RemoveSeedDialog
          openingName={pendingSeedRemove.name}
          seedVisibility={pendingSeedRemove.seed_visibility}
          busy={removingSeedId === pendingSeedRemove.id}
          error={removeSeedError}
          onConfirm={() => void handleConfirmSeedRemove()}
          onCancel={handleCancelSeedRemove}
        />
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