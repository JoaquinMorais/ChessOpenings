import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import type { FormEvent } from "react";

import { ApiError } from "../api/client";
import { updateNode } from "../api/nodes";
import {
  CLASSIFICATIONS,
  type ClassificationKey,
} from "../types/classifications";
import type { NodeRead, TreeNode } from "../types/node";
import ClassificationBadge from "./ClassificationBadge";

interface CurrentMovePanelProps {
  node: TreeNode;
  isRoot: boolean;
  highlightClassification?: boolean;
  onSaved: (node: NodeRead) => void;
}

export interface CurrentMovePanelHandle {
  flush: () => Promise<boolean>;
  classify: (key: ClassificationKey) => void;
}

type SaveStatus = "saved" | "saving" | "error";

interface SaveValues {
  name: string;
  comment: string;
  classification: ClassificationKey | null;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Ocurrió un error inesperado.";
}

const CurrentMovePanel = forwardRef<CurrentMovePanelHandle, CurrentMovePanelProps>(
  function CurrentMovePanel(
    { node, isRoot, highlightClassification = false, onSaved },
    ref,
  ) {
    const [name, setName] = useState(node.name ?? "");
    const [comment, setComment] = useState(node.comment ?? "");
    const [classification, setClassification] =
      useState<ClassificationKey | null>(node.classification);
    const [status, setStatus] = useState<SaveStatus>("saved");
    const [error, setError] = useState<string | null>(null);
    const snapshotRef = useRef<SaveValues>({
      name: node.name ?? "",
      comment: node.comment ?? "",
      classification: node.classification,
    });
    const savingPromiseRef = useRef<Promise<boolean> | null>(null);

    useEffect(() => {
      const next: SaveValues = {
        name: node.name ?? "",
        comment: node.comment ?? "",
        classification: node.classification,
      };
      setName(next.name);
      setComment(next.comment);
      setClassification(next.classification);
      snapshotRef.current = next;
      setStatus("saved");
      setError(null);
    }, [node.id]);

    const currentValues: SaveValues = {
      name,
      comment,
      classification,
    };
    const isDirty =
      !isRoot &&
      (currentValues.name !== snapshotRef.current.name ||
        currentValues.comment !== snapshotRef.current.comment ||
        currentValues.classification !== snapshotRef.current.classification);

    const save = useCallback(
      async (overrides?: Partial<SaveValues>): Promise<boolean> => {
        if (isRoot) {
          return true;
        }
        if (savingPromiseRef.current) {
          return savingPromiseRef.current;
        }

        const values: SaveValues = {
          name: overrides?.name ?? name,
          comment: overrides?.comment ?? comment,
          classification:
            overrides?.classification !== undefined
              ? overrides.classification
              : classification,
        };
        const snapshot = snapshotRef.current;
        const dirty =
          values.name !== snapshot.name ||
          values.comment !== snapshot.comment ||
          values.classification !== snapshot.classification;
        if (!dirty) {
          return true;
        }

        const promise = (async () => {
          setStatus("saving");
          setError(null);
          try {
            const updated = await updateNode(node.id, values);
            const next: SaveValues = {
              name: updated.name ?? "",
              comment: updated.comment ?? "",
              classification: updated.classification ?? null,
            };
            setName(next.name);
            setComment(next.comment);
            setClassification(next.classification);
            snapshotRef.current = next;
            setStatus("saved");
            onSaved(updated);
            return true;
          } catch (saveError) {
            setStatus("error");
            setError(getErrorMessage(saveError));
            return false;
          } finally {
            savingPromiseRef.current = null;
          }
        })();

        savingPromiseRef.current = promise;
        return promise;
      },
      [classification, comment, isRoot, name, node.id, onSaved],
    );

    const classify = useCallback(
      (key: ClassificationKey) => {
        if (isRoot || status === "saving") {
          return;
        }
        const next = classification === key ? null : key;
        setClassification(next);
        void save({ classification: next });
      },
      [classification, isRoot, save, status],
    );

    useImperativeHandle(
      ref,
      () => ({ flush: () => save(), classify }),
      [classify, save],
    );

    const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      void save();
    };

    const statusLabel = isRoot
      ? ""
      : status === "saving"
        ? "Guardando..."
        : status === "error"
          ? `Error: ${error ?? "No se pudo guardar."}`
          : isDirty
            ? "Sin guardar"
            : "Guardado";
    const statusVariant =
      status === "error"
        ? "error"
        : status === "saving"
          ? "saving"
          : isDirty
            ? "dirty"
            : "saved";

    return (
      <section className="panel current-move-panel">
        <div className="panel-heading">
          <p className="card-label">Jugada actual</p>
          <h3>{node.san ?? "Inicio"}</h3>
        </div>

        {isRoot ? (
          <p className="editor-info">
            La posición inicial no se puede editar.
          </p>
        ) : (
          <form className="current-move-form" onSubmit={handleSubmit}>
            <label className="form-field">
              <span>Nombre de la rama</span>
              <input
                value={name}
                maxLength={80}
                onChange={(event) => setName(event.target.value)}
                placeholder="Ej. Variante Alapin"
              />
            </label>

            <label className="form-field">
              <span>Observaciones</span>
              <textarea
                value={comment}
                rows={3}
                onChange={(event) => setComment(event.target.value)}
                placeholder="Notas, ideas o recordatorios sobre esta jugada"
              />
            </label>

            <div className="current-move-footer">
              <span
                className={`save-status save-status--${statusVariant}`}
                role="status"
              >
                {statusLabel}
              </span>
              <button
                type="submit"
                className="button button--small"
                disabled={!isDirty || status === "saving"}
              >
                Guardar
              </button>
            </div>
          </form>
        )}

        <div
          className={`classification-row ${
            highlightClassification && !isRoot
              ? "classification-row--invite"
              : ""
          }`}
        >
          <p className="card-label">Clasificación</p>
          <div className="classification-options">
            {CLASSIFICATIONS.map((item, index) => (
              <button
                key={item.key}
                type="button"
                className={`classification-option ${
                  classification === item.key ? "is-selected" : ""
                }`}
                onClick={() => classify(item.key)}
                disabled={isRoot || status === "saving"}
                title={`${item.label} (${index === 9 ? "0" : index + 1})`}
                aria-pressed={classification === item.key}
              >
                <ClassificationBadge
                  classification={item.key}
                  size="md"
                />
              </button>
            ))}
          </div>
          {highlightClassification && !isRoot && (
            <p className="classification-hint">
              Clasificá esta jugada nueva.
            </p>
          )}
        </div>
      </section>
    );
  },
);

export default CurrentMovePanel;