import { useState } from "react";

import PrivateSeedConfirmation from "./PrivateSeedConfirmation";
import type { SeedVisibility } from "../types/opening";

interface RemoveSeedDialogProps {
  openingName: string;
  seedVisibility: SeedVisibility | null;
  busy: boolean;
  error: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}

function RemoveSeedDialog({
  openingName,
  seedVisibility,
  busy,
  error,
  onConfirm,
  onCancel,
}: RemoveSeedDialogProps) {
  const [confirmName, setConfirmName] = useState("");
  const isPrivate = seedVisibility === "private";
  const canConfirm =
    !isPrivate || confirmName.trim() === openingName;

  return (
    <div className="modal-backdrop" role="presentation">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="remove-seed-title"
      >
        <p className="eyebrow">Seed</p>
        <h3 id="remove-seed-title">
          Quitar “{openingName}” del seed
        </h3>
        <p>
          La apertura seguirá en la base de datos, pero se borrará su
          archivo del seed.
        </p>

        {isPrivate ? (
          <PrivateSeedConfirmation
            openingName={openingName}
            value={confirmName}
            onChange={setConfirmName}
            disabled={busy}
          />
        ) : (
          <p className="seed-delete-help">
            El archivo público se eliminará del seed. La apertura seguirá
            en la base de datos.
          </p>
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
            className="button button--danger"
            onClick={onConfirm}
            disabled={busy || !canConfirm}
          >
            {busy ? "Quitando..." : "Quitar del seed"}
          </button>
        </div>
      </section>
    </div>
  );
}

export default RemoveSeedDialog;
