import { useState } from "react";
import type { FormEvent } from "react";

type SeedVisibility = "public" | "private";

interface SaveSeedDialogProps {
  openingName: string;
  initialVisibility: SeedVisibility | null;
  busy: boolean;
  error: string | null;
  onSubmit: (visibility: SeedVisibility) => void;
  onCancel: () => void;
}

function SaveSeedDialog({
  openingName,
  initialVisibility,
  busy,
  error,
  onSubmit,
  onCancel,
}: SaveSeedDialogProps) {
  const [visibility, setVisibility] = useState<SeedVisibility>(
    initialVisibility ?? "public",
  );
  const isUpdate = initialVisibility !== null;
  const visibilityChanged =
    initialVisibility !== null && visibility !== initialVisibility;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit(visibility);
  };

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
            <button type="submit" className="button" disabled={busy}>
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
