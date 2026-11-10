import { useState } from "react";
import type { FormEvent } from "react";

import type { OpeningColor } from "../types/opening";

interface ImportPgnDialogProps {
  busy: boolean;
  error: string | null;
  onImport: (payload: {
    pgn: string;
    name?: string;
    color: OpeningColor;
  }) => void;
  onCancel: () => void;
}

function ImportPgnDialog({
  busy,
  error,
  onImport,
  onCancel,
}: ImportPgnDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [pgnText, setPgnText] = useState("");
  const [name, setName] = useState("");
  const [color, setColor] = useState<OpeningColor>("white");
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);

    const text = file ? await file.text() : pgnText;
    if (!text.trim()) {
      setLocalError("Seleccioná un archivo o pegá un PGN.");
      return;
    }

    const trimmedName = name.trim();
    onImport({
      pgn: text,
      color,
      ...(trimmedName ? { name: trimmedName } : {}),
    });
  };

  return (
    <div className="modal-backdrop" role="presentation">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="import-pgn-title"
      >
        <p className="eyebrow">Importar PGN</p>
        <h3 id="import-pgn-title">Traer un estudio o partida</h3>
        <p>
          Se importarán las variantes como ramas y los comentarios como
          observaciones. Si no ponés nombre, se usará el Event del PGN.
        </p>

        <form className="pgn-form" onSubmit={(event) => void handleSubmit(event)}>
          <label className="form-field">
            <span>Archivo PGN</span>
            <input
              type="file"
              accept=".pgn,application/x-chess-pgn,text/plain"
              onChange={(event) =>
                setFile(event.target.files?.[0] ?? null)
              }
            />
          </label>

          <label className="form-field">
            <span>O pegá el PGN</span>
            <textarea
              value={pgnText}
              rows={4}
              onChange={(event) => setPgnText(event.target.value)}
              placeholder='[Event "Mi estudio"]&#10;&#10;1. e4 e5 2. Nf3 ...'
            />
          </label>

          <label className="form-field">
            <span>Nombre (opcional)</span>
            <input
              value={name}
              maxLength={120}
              onChange={(event) => setName(event.target.value)}
              placeholder="Se usará el Event del PGN"
            />
          </label>

          <fieldset className="form-field">
            <legend>Color del repertorio</legend>
            <div className="color-options">
              <label>
                <input
                  type="radio"
                  name="pgn-color"
                  value="white"
                  checked={color === "white"}
                  onChange={() => setColor("white")}
                />
                Blancas
              </label>
              <label>
                <input
                  type="radio"
                  name="pgn-color"
                  value="black"
                  checked={color === "black"}
                  onChange={() => setColor("black")}
                />
                Negras
              </label>
            </div>
          </fieldset>

          {(localError ?? error) && (
            <p className="form-error" role="alert">
              {localError ?? error}
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
              {busy ? "Importando..." : "Importar PGN"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default ImportPgnDialog;