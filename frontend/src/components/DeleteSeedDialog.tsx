import { useState } from "react";

import PrivateSeedConfirmation from "./PrivateSeedConfirmation";
import type { SeedVisibility } from "../types/opening";

interface DeleteSeedDialogProps {
  openingName: string;
  seedVisibility: SeedVisibility | null;
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
        <p className="eyebrow">Seed</p>
        <h3 id="delete-seed-title">
          Borrar “{openingName}”
        </h3>
        <p>Esta apertura está guardada en el seed.</p>

        <div className="seed-delete-help">
          <p>
            <strong>Borrar solo de la base:</strong> se mantiene en el
            seed; volverá si se crea una base nueva.
          </p>
          <p>
            <strong>Borrar también del seed:</strong> se elimina la
            apertura y su archivo guardado.
          </p>
        </div>

        {isPrivate && (
          <PrivateSeedConfirmation
            openingName={openingName}
            value={confirmName}
            onChange={setConfirmName}
            disabled={busy}
          />
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
            {busy ? "Borrando..." : "Borrar solo de la base"}
          </button>
          <button
            type="button"
            className="button button--danger"
            onClick={onDeleteWithSeed}
            disabled={busy || !canDeleteWithSeed}
          >
            {busy ? "Borrando..." : "Borrar también del seed"}
          </button>
        </div>
      </section>
    </div>
  );
}

export default DeleteSeedDialog;
