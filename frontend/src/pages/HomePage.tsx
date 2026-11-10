import { useCallback, useEffect, useState } from "react";

import { ApiError, apiFetch } from "../api/client";
import type { HealthResponse } from "../types/api";

type HealthState =
  | { status: "loading" }
  | { status: "ok"; response: HealthResponse }
  | { status: "error"; message: string };

function HomePage() {
  const [health, setHealth] = useState<HealthState>({ status: "loading" });

  const loadHealth = useCallback(async () => {
    setHealth({ status: "loading" });
    try {
      const response = await apiFetch<HealthResponse>("/health");
      setHealth({ status: "ok", response });
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "No se pudo conectar con el servidor.";
      setHealth({ status: "error", message });
    }
  }, []);

  useEffect(() => {
    void loadHealth();
  }, [loadHealth]);

  return (
    <section className="page">
      <div className="page-heading">
        <p className="eyebrow">Panel principal</p>
        <h2>Bienvenido</h2>
        <p>Entrena tus aperturas y revisa tu progreso desde un solo lugar.</p>
      </div>

      <article className={`health-card health-card--${health.status}`}>
        <div>
          <p className="card-label">Estado del servidor</p>
          {health.status === "loading" && <h3>Comprobando conexión...</h3>}
          {health.status === "ok" && <h3>Servidor disponible</h3>}
          {health.status === "error" && <h3>No se pudo conectar</h3>}
        </div>

        {health.status === "ok" && (
          <p className="health-detail">
            Respuesta: <code>{health.response.status}</code>
          </p>
        )}

        {health.status === "error" && (
          <div className="health-error">
            <p>{health.message}</p>
            <button type="button" onClick={() => void loadHealth()}>
              Reintentar
            </button>
          </div>
        )}
      </article>
    </section>
  );
}

export default HomePage;