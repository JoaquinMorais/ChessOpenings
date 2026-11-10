interface ImportConflictDialogProps {
  fileName: string;
  busy: boolean;
  error: string | null;
  onReplace: () => void;
  onDuplicate: () => void;
  onCancel: () => void;
}

function ImportConflictDialog({
  fileName,
  busy,
  error,
  onReplace,
  onDuplicate,
  onCancel,
}: ImportConflictDialogProps) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="import-conflict-title"
      >
        <p className="eyebrow">Conflicto de importación</p>
        <h3 id="import-conflict-title">
          Ya existe una apertura con ese nombre
        </h3>
        <p>
          El archivo <strong>{fileName}</strong> contiene una apertura cuyo
          nombre ya está en uso. ¿Qué querés hacer?
        </p>

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
          <button
            type="button"
            className="button"
            onClick={onDuplicate}
            disabled={busy}
          >
            {busy ? "Importando..." : "Duplicar"}
          </button>
          <button
            type="button"
            className="button button--danger"
            onClick={onReplace}
            disabled={busy}
          >
            {busy ? "Importando..." : "Reemplazar"}
          </button>
        </div>
      </section>
    </div>
  );
}

export default ImportConflictDialog;