import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { listOpenings } from "../api/openings";
import type { OpeningColor, OpeningSummary } from "../types/opening";

type ListState =
  | { status: "loading" }
  | { status: "ok"; openings: OpeningSummary[] }
  | { status: "error"; message: string };

const COLOR_LABELS: Record<OpeningColor, string> = {
  white: "Blancas",
  black: "Negras",
};

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Ocurrió un error inesperado.";
}

function formatAccuracy(accuracy: number | null): string {
  return accuracy === null ? "Sin datos" : `${accuracy.toFixed(1)}%`;
}

function StatsIndexPage() {
  const [list, setList] = useState<ListState>({ status: "loading" });

  const loadOpenings = useCallback(async () => {
    setList({ status: "loading" });
    try {
      const openings = await listOpenings();
      setList({ status: "ok", openings });
    } catch (error) {
      setList({ status: "error", message: getErrorMessage(error) });
    }
  }, []);

  useEffect(() => {
    void loadOpenings();
  }, [loadOpenings]);

  return (
    <section className="page">
      <div className="page-heading">
        <p className="eyebrow">Estadísticas</p>
        <h2>Elegir apertura</h2>
        <p>Seleccioná un repertorio para ver su detalle de entrenamiento.</p>
      </div>

      {list.status === "loading" && (
        <p className="state-message">Cargando aperturas...</p>
      )}

      {list.status === "error" && (
        <div className="state-card state-card--error">
          <p>{list.message}</p>
          <button
            type="button"
            className="button"
            onClick={() => void loadOpenings()}
          >
            Reintentar
          </button>
        </div>
      )}

      {list.status === "ok" && list.openings.length === 0 && (
        <div className="state-card state-card--empty">
          <h3>No hay aperturas todavía</h3>
          <p>Creá una apertura primero para ver estadísticas.</p>
          <Link className="button" to="/openings">
            Ir a aperturas
          </Link>
        </div>
      )}

      {list.status === "ok" && list.openings.length > 0 && (
        <ul className="opening-list">
          {list.openings.map((opening) => (
            <li key={opening.id} className="opening-card">
              <div className="opening-summary">
                <span
                  className={`color-icon color-icon--${opening.color}`}
                  role="img"
                  aria-label={COLOR_LABELS[opening.color]}
                />
                <div>
                  <h3>{opening.name}</h3>
                  <p className="opening-meta">
                    <span>{COLOR_LABELS[opening.color]}</span>
                    <span>Acierto: {formatAccuracy(opening.accuracy)}</span>
                  </p>
                </div>
              </div>
              <div className="opening-actions">
                <Link
                  className="button button--small button--ghost"
                  to={`/openings/${opening.id}/stats`}
                >
                  Ver estadísticas
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default StatsIndexPage;