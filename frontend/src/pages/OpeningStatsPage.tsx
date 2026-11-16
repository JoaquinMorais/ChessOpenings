import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { getOpening } from "../api/openings";
import { getOpeningStats } from "../api/stats";
import AccuracyChart from "../components/AccuracyChart";
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

const DAY_FORMATTER = new Intl.DateTimeFormat("es", {
  day: "2-digit",
  month: "2-digit",
});

type StatsPeriod = "week" | "month" | "year" | "total";

const PERIOD_OPTIONS: { value: StatsPeriod; label: string }[] = [
  { value: "week", label: "Semana" },
  { value: "month", label: "Mes" },
  { value: "year", label: "Año" },
  { value: "total", label: "Total" },
];

function periodBounds(
  period: StatsPeriod,
): { start: Date; end: Date } | null {
  if (period === "total") {
    return null;
  }
  const now = new Date();
  if (period === "week") {
    const start = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate(),
    );
    const offset = (start.getDay() + 6) % 7;
    start.setDate(start.getDate() - offset);
    const end = new Date(start);
    end.setDate(end.getDate() + 7);
    return { start, end };
  }
  if (period === "month") {
    return {
      start: new Date(now.getFullYear(), now.getMonth(), 1),
      end: new Date(now.getFullYear(), now.getMonth() + 1, 1),
    };
  }
  return {
    start: new Date(now.getFullYear(), 0, 1),
    end: new Date(now.getFullYear() + 1, 0, 1),
  };
}

function parseDate(value: string): Date | null {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function dayKey(date: Date): string {
  return `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`;
}

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
  const [period, setPeriod] = useState<StatsPeriod>("total");

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

  const sessions = useMemo(() => stats?.sessions ?? [], [stats]);

  const filteredSessions = useMemo(() => {
    const bounds = periodBounds(period);
    if (!bounds) {
      return sessions;
    }
    return sessions.filter((session) => {
      const date = parseDate(session.finished_at);
      return (
        date !== null &&
        date >= bounds.start &&
        date < bounds.end
      );
    });
  }, [period, sessions]);

  const sessionPoints = useMemo(
    () =>
      filteredSessions.map((session, index) => ({
        label: String(index + 1),
        value: session.accuracy,
      })),
    [filteredSessions],
  );

  const dayPoints = useMemo(() => {
    const groups = new Map<
      string,
      { date: Date; total: number; count: number }
    >();
    for (const session of filteredSessions) {
      const date = parseDate(session.finished_at);
      if (!date) {
        continue;
      }
      const key = dayKey(date);
      const group = groups.get(key);
      if (group) {
        group.total += session.accuracy;
        group.count += 1;
      } else {
        groups.set(key, {
          date,
          total: session.accuracy,
          count: 1,
        });
      }
    }
    return [...groups.values()]
      .sort((left, right) => left.date.getTime() - right.date.getTime())
      .map((group) => ({
        label: DAY_FORMATTER.format(group.date),
        value: group.total / group.count,
      }));
  }, [filteredSessions]);

  const sessionAverage =
    filteredSessions.length > 0
      ? filteredSessions.reduce(
          (sum, session) => sum + session.accuracy,
          0,
        ) / filteredSessions.length
      : null;

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

      <section className="panel stats-history">
        <div className="panel-heading">
          <p className="card-label">Entrenamientos</p>
          <h3>Historial de entrenamientos completos</h3>
          <p className="editor-info">
            Solo se incluyen sesiones terminadas. El acierto se calcula
            con los aciertos al primer intento sobre las preguntas de la
            sesión.
          </p>
        </div>

        {sessions.length === 0 ? (
          <div className="state-card state-card--empty">
            <h3>Todavía no completaste entrenamientos</h3>
            <p>
              Cuando termines una sesión entera, vas a ver acá su
              porcentaje y la evolución en los gráficos.
            </p>
            <Link
              className="button"
              to={`/openings/${opening.id}/train`}
            >
              Entrenar ahora
            </Link>
          </div>
        ) : (
          <>
            <div
              className="stats-period-filter"
              role="group"
              aria-label="Período de entrenamientos"
            >
              {PERIOD_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={`stats-period-option${
                    period === option.value ? " is-selected" : ""
                  }`}
                  aria-pressed={period === option.value}
                  onClick={() => setPeriod(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>

            {filteredSessions.length === 0 ? (
              <div className="state-card state-card--empty">
                <h3>No hay entrenamientos completos en este período</h3>
                <p>Probá con otro período o volvé al total.</p>
                <button
                  type="button"
                  className="button"
                  onClick={() => setPeriod("total")}
                >
                  Ver total
                </button>
              </div>
            ) : (
              <>
                <p className="stats-history-summary">
                  <strong>{filteredSessions.length}</strong> entrenamiento(s)
                  completo(s) en el período
                  {sessionAverage !== null &&
                    ` · promedio ${formatAccuracy(sessionAverage)}`}
                </p>

                <div className="stats-charts">
                  <AccuracyChart
                    title="Acierto por día"
                    description="Promedio de los entrenamientos completados cada día del período."
                    points={dayPoints}
                  />
                  <AccuracyChart
                    title="Acierto por entrenamiento"
                    description="Evolución de cada sesión completada en el período, en orden."
                    points={sessionPoints}
                  />
                </div>

                <div className="stats-table-wrapper">
                  <table className="stats-table stats-session-table">
                    <thead>
                      <tr>
                        <th scope="col">#</th>
                        <th scope="col">Finalizado</th>
                        <th scope="col">Preguntas</th>
                        <th scope="col">Aciertos 1er intento</th>
                        <th scope="col">Acierto</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredSessions.map((session, index) => (
                        <tr key={session.id}>
                          <td>{index + 1}</td>
                          <td>{formatDateTime(session.finished_at)}</td>
                          <td>{session.questions_total}</td>
                          <td>{session.first_try_correct}</td>
                          <td>{formatAccuracy(session.accuracy)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </>
        )}
      </section>

      {trainedPositions > 0 && (
        <h3 className="stats-section-title">Detalle por posición</h3>
      )}

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