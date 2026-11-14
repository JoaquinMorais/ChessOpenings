import { useState } from "react";

interface DeleteSeedDialogProps {
  openingName: string;
  seedVisibility: "public" | "private" | null;
  busy: boolean;
  error: string | null;
  onDeleteOnly: () => void;
  onDeleteWithSeed: () => void;
  onCancel: () => void;
}

function DeleteSeedDialog({
  openingName,
  seedVisibility,
  busy,
  error,
  onDeleteOnly,
  onDeleteWithSeed,
  onCancel,
}: DeleteSeedDialogProps) {
  const [confirmName, setConfirmName] = useState("");
  const isPrivate = seedVisibility === "private";
  const canDeleteWithSeed =
    !isPrivate || confirmName.trim() === openingName;

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
          Si la eliminás solo de la base, no volverá a aparecer al
          reiniciar. El archivo seguirá guardado en el seed.
        </p>

        {isPrivate && (
          <div className="form-field">
            <p className="form-error">
              El archivo private no está en git. Para borrarlo también del
              seed, escribí el nombre exacto de la apertura.
            </p>
            <label>
              <span>Escribí “{openingName}”</span>
              <input
                type="text"
                value={confirmName}
                onChange={(event) => setConfirmName(event.target.value)}
                placeholder={openingName}
                disabled={busy}
              />
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
            disabled={busy || !canDeleteWithSeed}
          >
            {busy ? "Eliminando..." : "Eliminar también del seed"}
          </button>
        </div>
      </section>
    </div>
  );
}

export default DeleteSeedDialog;
