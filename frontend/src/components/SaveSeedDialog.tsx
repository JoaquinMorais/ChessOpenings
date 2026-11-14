import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "../api/client";
import { getEvaluationStatus } from "../api/openings";
import type {
  EvaluationStatus,
  TrackedEvaluationJob,
} from "../types/evaluation";
import type { SeedSaveOptions, SeedVisibility } from "../types/opening";
import EvaluationJobProgress from "./EvaluationJobProgress";

interface SaveSeedDialogProps {
  openingId: number;
  openingName: string;
  initialVisibility: SeedVisibility | null;
  busy: boolean;
  error: string | null;
  externalRequired: boolean;
  job: TrackedEvaluationJob | null;
  onSubmit: (options: SeedSaveOptions) => void;
  onCancelJob: (jobId: string) => Promise<void>;
  onCancel: () => void;
}

type StatusState =
  | { status: "loading" }
  | { status: "ok"; data: EvaluationStatus }
  | { status: "error"; message: string };

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "No se pudo consultar el estado de valoración.";
}

function SaveSeedDialog({
  openingId,
  openingName,
  initialVisibility,
  busy,
  error,
  externalRequired,
  job,
  onSubmit,
  onCancelJob,
  onCancel,
}: SaveSeedDialogProps) {
  const [visibility, setVisibility] = useState<SeedVisibility>(
    initialVisibility ?? "public",
  );
  const [statusState, setStatusState] = useState<StatusState>({
    status: "loading",
  });
  const [evaluate, setEvaluate] = useState(false);
  const [externalConfirmed, setExternalConfirmed] = useState(false);
  const isUpdate = initialVisibility !== null;
  const visibilityChanged =
    initialVisibility !== null && visibility !== initialVisibility;

  const loadStatus = useCallback(async () => {
    setStatusState({ status: "loading" });
    try {
      const data = await getEvaluationStatus(openingId);
      setStatusState({ status: "ok", data });
    } catch (statusError) {
      setStatusState({
        status: "error",
        message: getErrorMessage(statusError),
      });
    }
  }, [openingId]);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    setExternalConfirmed(false);
  }, [visibility, evaluate]);

  const status =
    statusState.status === "ok" ? statusState.data : null;
  const canEvaluate =
    status !== null && status.missing > 0 && !status.running;
  const isExternal = status?.evaluator === "llm";
  const requiresExternal =
    (isExternal || externalRequired) &&
    visibility === "private" &&
    evaluate;
  const canSubmit =
    !busy && (!requiresExternal || externalConfirmed);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit || job) {
      return;
    }
    onSubmit({
      visibility,
      evaluate: evaluate && canEvaluate,
      allow_external: requiresExternal,
      total: status?.missing ?? 0,
    });
  };

  if (job) {
    return (
      <div className="modal-backdrop" role="presentation">
        <section
          className="modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="save-seed-title"
        >
          <p className="eyebrow">Valoración automática</p>
          <h3 id="save-seed-title">Valorando “{openingName}”</h3>
          <p>
            El seed ya fue guardado. Podés cerrar esta ventana y seguir el
            progreso desde la lista de aperturas.
          </p>
          <EvaluationJobProgress
            job={job}
            onCancel={onCancelJob}
          />
          <div className="modal-actions">
            <button
              type="button"
              className="button button--ghost"
              onClick={onCancel}
            >
              Cerrar
            </button>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="save-seed-title"
      >
        <p className="eyebrow">Seed</p>
        <h3 id="save-seed-title">
          {isUpdate ? "Actualizar seed" : "Guardar en seed"}
        </h3>
        <p>
          Elegí dónde guardar <strong>{openingName}</strong>.
        </p>

        <form className="seed-form" onSubmit={handleSubmit}>
          <fieldset className="form-field">
            <legend>Visibilidad</legend>
            <div className="visibility-options">
              <label
                className={`visibility-option${
                  visibility === "public"
                    ? " visibility-option--selected"
                    : ""
                }`}
              >
                <input
                  type="radio"
                  name="seed-visibility"
                  value="public"
                  checked={visibility === "public"}
                  onChange={() => setVisibility("public")}
                  disabled={busy}
                />
                <span className="visibility-option-text">
                  <strong>Publica</strong>
                  <span className="visibility-description">
                    Se guarda en seed_import/public y se sube a git si
                    hacés push. La ve cualquiera que clone el repo.
                  </span>
                </span>
              </label>

              <label
                className={`visibility-option${
                  visibility === "private"
                    ? " visibility-option--selected"
                    : ""
                }`}
              >
                <input
                  type="radio"
                  name="seed-visibility"
                  value="private"
                  checked={visibility === "private"}
                  onChange={() => setVisibility("private")}
                  disabled={busy}
                />
                <span className="visibility-option-text">
                  <strong>Privada</strong>
                  <span className="visibility-description">
                    Se guarda en seed_import/private y git la ignora.
                    Queda solo en tu equipo.
                  </span>
                </span>
              </label>
            </div>
          </fieldset>

          {visibilityChanged && (
            <p className="seed-visibility-warning">
              Al cambiar la visibilidad, el archivo se moverá de
              seed_import/{initialVisibility} a seed_import/{visibility}.
              {visibility === "private"
                ? " Dejará de subirse a git."
                : " Se subirá a git con tu próximo push."}
            </p>
          )}

          <div className="seed-evaluation-option">
            <label>
              <input
                type="checkbox"
                checked={evaluate}
                onChange={(event) => setEvaluate(event.target.checked)}
                disabled={busy || !canEvaluate}
              />
              <span>
                {statusState.status === "loading"
                  ? "Consultando posiciones sin valorar..."
                  : statusState.status === "error"
                    ? "No se pudo consultar el estado de valoración."
                    : status && status.running
                      ? "Hay una valoración en curso."
                      : status && status.missing === 0
                        ? "Ya está valorada."
                        : status
                          ? `Crear valoración de las posiciones sin valorar (${status.missing} de ${status.total})`
                          : "Valoración automática"}
              </span>
            </label>
            {statusState.status === "error" && (
              <button
                type="button"
                className="button button--small button--ghost"
                onClick={() => void loadStatus()}
              >
                Reintentar
              </button>
            )}
          </div>

          {requiresExternal && (
            <div className="seed-external-warning">
              <strong>Las posiciones se enviarán a un servicio externo.</strong>
              <label>
                <input
                  type="checkbox"
                  checked={externalConfirmed}
                  onChange={(event) =>
                    setExternalConfirmed(event.target.checked)
                  }
                  disabled={busy}
                />
                <span>
                  Confirmo el envío de las posiciones a un servicio externo.
                </span>
              </label>
            </div>
          )}

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          <div className="modal-actions">
            <button
              type="button"
              className="button button--ghost"
              onClick={onCancel}
              disabled={busy}
            >
              Cancelar
            </button>
            <button type="submit" className="button" disabled={!canSubmit}>
              {busy
                ? "Guardando..."
                : isUpdate
                  ? "Actualizar seed"
                  : "Guardar en seed"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default SaveSeedDialog;
