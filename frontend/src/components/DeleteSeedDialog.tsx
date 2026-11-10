interface DeleteSeedDialogProps {
  openingName: string;
  busy: boolean;
  error: string | null;
  onDeleteOnly: () => void;
  onDeleteWithSeed: () => void;
  onCancel: () => void;
}

function DeleteSeedDialog({
  openingName,
  busy,
  error,
  onDeleteOnly,
  onDeleteWithSeed,
  onCancel,
}: DeleteSeedDialogProps) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-seed-title"
      >
        <p className="eyebrow">Opening en seed</p>
        <h3 id="delete-seed-title">
          Eliminar “{openingName}”
        </h3>
        <p>
          Esta apertura está guardada en <code>seed_import</code>. Si la
          eliminás solo de la base, volverá a aparecer al reiniciar.
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
            className="button button--ghost"
            onClick={onDeleteOnly}
            disabled={busy}
          >
            {busy ? "Eliminando..." : "Eliminar solo de la base"}
          </button>
          <button
            type="button"
            className="button button--danger"
            onClick={onDeleteWithSeed}
            disabled={busy}
          >
            {busy ? "Eliminando..." : "Eliminar también del seed"}
          </button>
        </div>
      </section>
    </div>
  );
}

export default DeleteSeedDialog;