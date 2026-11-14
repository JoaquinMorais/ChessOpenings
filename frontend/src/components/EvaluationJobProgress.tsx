import { useState } from "react";

import type { TrackedEvaluationJob } from "../types/evaluation";

interface EvaluationJobProgressProps {
  job: TrackedEvaluationJob;
  onCancel?: (jobId: string) => Promise<void>;
  compact?: boolean;
}

const STATE_LABELS = {
  running: "Valorando posiciones...",
  done: "Valoración completada.",
  cancelled: "Valoración cancelada.",
  error: "No se pudo completar la valoración.",
} as const;

function EvaluationJobProgress({
  job,
  onCancel,
  compact = false,
}: EvaluationJobProgressProps) {
  const [cancelling, setCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const percent =
    job.total > 0
      ? Math.min(100, Math.round((job.done / job.total) * 100))
      : 0;

  const handleCancel = async () => {
    if (!onCancel || cancelling || job.state !== "running") {
      return;
    }
    setCancelling(true);
    setCancelError(null);
    try {
      await onCancel(job.jobId);
    } catch (error) {
      setCancelError(
        error instanceof Error
          ? error.message
          : "No se pudo cancelar la valoración.",
      );
    } finally {
      setCancelling(false);
    }
  };

  return (
    <div
      className={`evaluation-job-progress${
        compact ? " evaluation-job-progress--compact" : ""
      }`}
    >
      <div className="evaluation-job-progress__header">
        <strong>{STATE_LABELS[job.state]}</strong>
        <span>
          {job.done}/{job.total}
          {job.errors > 0 ? ` · ${job.errors} errores` : ""}
        </span>
      </div>
      <div
        className="evaluation-job-progress__bar"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={job.total}
        aria-valuenow={job.done}
        aria-label="Progreso de valoración"
      >
        <span
          className="evaluation-job-progress__fill"
          style={{ width: `${percent}%` }}
        />
      </div>
      {job.message && (
        <p className="evaluation-job-progress__message">{job.message}</p>
      )}
      {cancelError && (
        <p className="form-error" role="alert">
          {cancelError}
        </p>
      )}
      {job.state === "running" && onCancel && (
        <button
          type="button"
          className="button button--small button--ghost"
          onClick={() => void handleCancel()}
          disabled={cancelling}
        >
          {cancelling ? "Cancelando..." : "Cancelar valoración"}
        </button>
      )}
    </div>
  );
}

export default EvaluationJobProgress;
