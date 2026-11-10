import { useId, useState } from "react";
import type { FormEvent } from "react";

import type { OpeningColor } from "../types/opening";

interface OpeningFormValues {
  name: string;
  color: OpeningColor;
}

interface OpeningFormProps {
  mode: "create" | "rename";
  initialName?: string;
  initialColor?: OpeningColor;
  submitting: boolean;
  error: string | null;
  onSubmit: (values: OpeningFormValues) => void;
  onCancel: () => void;
}

function OpeningForm({
  mode,
  initialName = "",
  initialColor = "white",
  submitting,
  error,
  onSubmit,
  onCancel,
}: OpeningFormProps) {
  const fieldId = useId();
  const [name, setName] = useState(initialName);
  const [color, setColor] = useState<OpeningColor>(initialColor);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      setLocalError("El nombre es obligatorio.");
      return;
    }
    setLocalError(null);
    onSubmit({ name: trimmedName, color });
  };

  const errorMessage = localError ?? error;
  const submitLabel =
    mode === "create"
      ? submitting
        ? "Creando..."
        : "Crear opening"
      : submitting
        ? "Guardando..."
        : "Guardar nombre";

  return (
    <form className="opening-form" onSubmit={handleSubmit}>
      <div className="form-field">
        <label htmlFor={`${fieldId}-name`}>Nombre</label>
        <input
          id={`${fieldId}-name`}
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={120}
          autoFocus
        />
      </div>

      {mode === "create" && (
        <fieldset className="form-field">
          <legend>Color</legend>
          <div className="color-options">
            <label>
              <input
                type="radio"
                name={`${fieldId}-color`}
                value="white"
                checked={color === "white"}
                onChange={() => setColor("white")}
              />
              Blancas
            </label>
            <label>
              <input
                type="radio"
                name={`${fieldId}-color`}
                value="black"
                checked={color === "black"}
                onChange={() => setColor("black")}
              />
              Negras
            </label>
          </div>
        </fieldset>
      )}

      {errorMessage && (
        <p className="form-error" role="alert">
          {errorMessage}
        </p>
      )}

      <div className="form-actions">
        <button
          type="button"
          className="button button--ghost"
          onClick={onCancel}
          disabled={submitting}
        >
          Cancelar
        </button>
        <button type="submit" className="button" disabled={submitting}>
          {submitLabel}
        </button>
      </div>
    </form>
  );
}

export default OpeningForm;