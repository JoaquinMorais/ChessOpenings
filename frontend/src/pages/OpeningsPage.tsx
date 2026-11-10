import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import {
  createOpening,
  deleteOpening,
  listOpenings,
  renameOpening,
} from "../api/openings";
import OpeningForm from "../components/OpeningForm";
import type { OpeningColor, OpeningSummary } from "../types/opening";

type ListState =
  | { status: "loading" }
  | { status: "ok"; openings: OpeningSummary[] }
  | { status: "error"; message: string };

type FormState =
  | { mode: "create" }
  | { mode: "rename"; opening: OpeningSummary }
  | null;

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

function formatMoves(nodeCount: number): number {
  return Math.max(nodeCount - 1, 0);
}

function formatAccuracy(accuracy: number | null): string {
  return accuracy === null ? "—" : `${accuracy.toFixed(1)}%`;
}

function OpeningsPage() {
  const [list, setList] = useState<ListState>({ status: "loading" });
  const [form, setForm] = useState<FormState>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

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

  const openCreateForm = () => {
    setForm({ mode: "create" });
    setFormError(null);
    setActionError(null);
  };

  const openRenameForm = (opening: OpeningSummary) => {
    setForm({ mode: "rename", opening });
    setFormError(null);
    setActionError(null);
  };

  const closeForm = () => {
    setForm(null);
    setFormError(null);
  };

  const handleSubmit = async (values: {
    name: string;
    color: OpeningColor;
  }) => {
    if (!form) {
      return;
    }

    setFormSubmitting(true);
    setFormError(null);
    try {
      if (form.mode === "create") {
        await createOpening({ name: values.name, color: values.color });
      } else {
        await renameOpening(form.opening.id, { name: values.name });
      }
      setForm(null);
      await loadOpenings();
    } catch (error) {
      setFormError(getErrorMessage(error));
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleDelete = async (opening: OpeningSummary) => {
    const confirmed = window.confirm(
      `¿Eliminar la apertura "${opening.name}"? Esta acción no se puede deshacer.`,
    );
    if (!confirmed) {
      return;
    }

    setDeletingId(opening.id);
    setActionError(null);
    try {
      await deleteOpening(opening.id);
      await loadOpenings();
    } catch (error) {
      setActionError(getErrorMessage(error));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <section className="page">
      <div className="page-toolbar">
        <div className="page-heading">
          <p className="eyebrow">Repertorio</p>
          <h2>Aperturas</h2>
          <p>Gestiona tus repertorios y empieza a entrenar.</p>
        </div>
        <button type="button" className="button" onClick={openCreateForm}>
          Nuevo opening
        </button>
      </div>

      {form && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="card-label">
                {form.mode === "create" ? "Nueva apertura" : "Renombrar"}
              </p>
              <h3>
                {form.mode === "create" ? "Crear opening" : form.opening.name}
              </h3>
            </div>
          </div>
          <OpeningForm
            key={
              form.mode === "create" ? "create" : `rename-${form.opening.id}`
            }
            mode={form.mode}
            initialName={form.mode === "rename" ? form.opening.name : ""}
            initialColor={
              form.mode === "rename" ? form.opening.color : "white"
            }
            submitting={formSubmitting}
            error={formError}
            onSubmit={(values) => void handleSubmit(values)}
            onCancel={closeForm}
          />
        </section>
      )}

      {actionError && (
        <div className="alert" role="alert">
          <p>{actionError}</p>
          <button type="button" onClick={() => setActionError(null)}>
            Cerrar
          </button>
        </div>
      )}

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
          <p>Crea tu primer opening para empezar a armar el repertorio.</p>
          <button type="button" className="button" onClick={openCreateForm}>
            Nuevo opening
          </button>
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
                    <span>{formatMoves(opening.node_count)} jugadas</span>
                    <span>Acierto: {formatAccuracy(opening.accuracy)}</span>
                  </p>
                </div>
              </div>

              <div className="opening-actions">
                <Link
                  className="button button--small"
                  to={`/openings/${opening.id}/edit`}
                >
                  Editar
                </Link>
                <Link
                  className="button button--small"
                  to={`/openings/${opening.id}/train`}
                >
                  Entrenar
                </Link>
                <button
                  type="button"
                  className="button button--small button--ghost"
                  onClick={() => openRenameForm(opening)}
                >
                  Renombrar
                </button>
                <button
                  type="button"
                  className="button button--small button--danger"
                  onClick={() => void handleDelete(opening)}
                  disabled={deletingId === opening.id}
                >
                  {deletingId === opening.id ? "Eliminando..." : "Eliminar"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default OpeningsPage;