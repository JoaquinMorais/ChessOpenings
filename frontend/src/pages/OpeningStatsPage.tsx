import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { getOpening } from "../api/openings";
import { getOpeningStats } from "../api/stats";
import type { OpeningSummary } from "../types/opening";
import type {
  OpeningStats,
  PositionStat,
  SortDirection,
} from "../types/stats";

const COLOR_LABELS = {
  white: "Blancas",
  black: "Negras",
} as const;

const DATE_FORMATTER = new Intl.DateTimeFormat("es", {
  dateStyle: "short",
  timeStyle: "short",
});

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Ocurrió un error inesperado.";
}

function formatAccuracy(accuracy: number | null): string {
  return accuracy === null ? "—" : `${accuracy.toFixed(1)}%`;
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return DATE_FORMATTER.format(date);
}

function comparePositions(
  left: PositionStat,
  right: PositionStat,
  direction: SortDirection,
): number {
  if (left.accuracy === null && right.accuracy === null) {
    return left.node_id - right.node_id;
  }
  if (left.accuracy === null) {
    return 1;
  }
  if (right.accuracy === null) {
    return -1;
  }
  const difference =
    direction === "asc"
      ? left.accuracy - right.accuracy
      : right.accuracy - left.accuracy;
  return difference === 0 ? left.node_id - right.node_id : difference;
}

function OpeningStatsPage() {
  const { id } = useParams<{ id: string }>();
  const openingId = Number(id);
  const [opening, setOpening] = useState<OpeningSummary | null>(null);
  const [stats, setStats] = useState<OpeningStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

  const loadStats = useCallback(async () => {
    if (!id || !Number.isInteger(openingId) || openingId <= 0) {
      setLoading(false);
      setError("La apertura no existe.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const [openingData, statsData] = await Promise.all([
        getOpening(openingId),
        getOpeningStats(openingId),
      ]);
      setOpening(openingData);
      setStats(statsData);
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [id, openingId]);

  useEffect(() => {
    void loadStats();
  }, [loadStats]);

  const sortedPositions = useMemo(() => {
    if (!stats) {
      return [];
    }
    return [...stats.positions].sort((left, right) =>
      comparePositions(left, right, sortDirection),
    );
  }, [stats, sortDirection]);

  const toggleSort = () => {
    setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
  };

  if (loading) {
    return (
      <section className="page">
        <div className="state-card">
          <p>Cargando estadísticas...</p>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="page">
        <div className="page-heading">
          <p className="eyebrow">Estadísticas</p>
          <h2>No se pudieron cargar las estadísticas</h2>
          <p>{error}</p>
        </div>
        <div className="state-card state-card--error">
          <div className="form-actions">
            <Link className="button button--ghost" to="/openings">
              Volver a aperturas
            </Link>
            <button type="button" className="button" onClick={() => void loadStats()}>
              Reintentar
            </button>
          </div>
        </div>
      </section>
    );
  }

  if (!opening || !stats) {
    return (
      <section className="page">
        <div className="state-card">
          <p>Cargando estadísticas...</p>
        </div>
      </section>
    );
  }

  const trainedPositions = stats.positions.length;

  return (
    <section className="page">
      <div className="page-toolbar">
        <div className="page-heading">
          <p className="eyebrow">Estadísticas</p>
          <h2>{opening.name}</h2>
          <p>{COLOR_LABELS[opening.color]}</p>
        </div>
        <div className="toolbar-actions">
          <Link className="button button--ghost" to="/openings">
            Volver
          </Link>
          <Link
            className="button"
            to={`/openings/${opening.id}/train`}
          >
            Entrenar
          </Link>
        </div>
      </div>

      <section className="stats-overview">
        <div>
          <p className="card-label">Acierto global</p>
          <strong className="stats-accuracy">
            {formatAccuracy(stats.accuracy)}
          </strong>
        </div>
        <p className="editor-info">
          {trainedPositions === 0
            ? "Todavía no hay posiciones entrenadas."
            : `${trainedPositions} posición(es) entrenada(s).`}
        </p>
      </section>

      {trainedPositions === 0 ? (
        <div className="state-card state-card--empty">
          <h3>Todavía no entrenaste esta apertura</h3>
          <p>
            Cuando completes una sesión, acá vas a ver el detalle por posición.
          </p>
          <div className="form-actions">
            <Link className="button button--ghost" to="/openings">
              Volver a aperturas
            </Link>
            <Link
              className="button"
              to={`/openings/${opening.id}/train`}
            >
              Entrenar ahora
            </Link>
          </div>
        </div>
      ) : (
        <div className="stats-table-wrapper">
          <table className="stats-table">
            <thead>
              <tr>
                <th scope="col">Posición</th>
                <th scope="col">Intentos</th>
                <th scope="col">Aciertos</th>
                <th
                  scope="col"
                  aria-sort={
                    sortDirection === "asc" ? "ascending" : "descending"
                  }
                >
                  <button
                    type="button"
                    className="sort-button"
                    onClick={toggleSort}
                  >
                    Acierto {sortDirection === "asc" ? "↑" : "↓"}
                  </button>
                </th>
                <th scope="col">Última práctica</th>
              </tr>
            </thead>
            <tbody>
              {sortedPositions.map((position) => (
                <tr key={position.node_id}>
                  <td className="stats-path">
                    {position.path_san || "Posición inicial"}
                  </td>
                  <td>{position.attempts}</td>
                  <td>{position.correct}</td>
                  <td>{formatAccuracy(position.accuracy)}</td>
                  <td>{formatDateTime(position.last_practiced_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default OpeningStatsPage;