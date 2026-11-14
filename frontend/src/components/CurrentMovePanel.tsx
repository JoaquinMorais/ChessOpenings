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
import type { Evaluation } from "../types/evaluation";
import type {
  NodeRead,
  NodeUpdatePayload,
  TreeNode,
} from "../types/node";
import {
  EVAL_PRESETS,
  formatEvaluation,
  parseEvaluation,
} from "../utils/evaluation";
import ClassificationBadge from "./ClassificationBadge";
import EvaluationSourceBadge from "./EvaluationSourceBadge";

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
  evaluationText: string;
}

interface SnapshotValues extends SaveValues {
  evaluation: Evaluation | null;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Ocurrió un error inesperado.";
}

function parseEvaluationText(text: string): {
  evaluation: Evaluation | null;
  error: string | null;
} {
  try {
    return { evaluation: parseEvaluation(text), error: null };
  } catch (error) {
    return {
      evaluation: null,
      error:
        error instanceof Error ? error.message : "Evaluación inválida.",
    };
  }
}

function evaluationSignature(evaluation: Evaluation | null): string {
  if (!evaluation) {
    return "";
  }
  if (typeof evaluation.mate === "number" && evaluation.mate !== 0) {
    return `mate:${evaluation.mate}`;
  }
  if (typeof evaluation.cp === "number") {
    return `cp:${evaluation.cp}`;
  }
  return "";
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
    const [evaluationText, setEvaluationText] = useState(
      node.evaluation ? formatEvaluation(node.evaluation) : "",
    );
    const [status, setStatus] = useState<SaveStatus>("saved");
    const [error, setError] = useState<string | null>(null);
    const snapshotRef = useRef<SnapshotValues>({
      name: node.name ?? "",
      comment: node.comment ?? "",
      classification: node.classification,
      evaluationText: node.evaluation ? formatEvaluation(node.evaluation) : "",
      evaluation: node.evaluation,
    });
    const savingPromiseRef = useRef<Promise<boolean> | null>(null);

    useEffect(() => {
      const nextEvaluationText = node.evaluation
        ? formatEvaluation(node.evaluation)
        : "";
      const next: SnapshotValues = {
        name: node.name ?? "",
        comment: node.comment ?? "",
        classification: node.classification,
        evaluationText: nextEvaluationText,
        evaluation: node.evaluation,
      };
      setName(next.name);
      setComment(next.comment);
      setClassification(next.classification);
      setEvaluationText(nextEvaluationText);
      snapshotRef.current = next;
      setStatus("saved");
      setError(null);
    }, [node.id]);

    useEffect(() => {
      if (evaluationText !== snapshotRef.current.evaluationText) {
        return;
      }
      const next = node.evaluation;
      const current = snapshotRef.current.evaluation;
      if (
        evaluationSignature(next) === evaluationSignature(current) &&
        (next?.source ?? "manual") === (current?.source ?? "manual")
      ) {
        return;
      }
      const nextEvaluationText = next ? formatEvaluation(next) : "";
      setEvaluationText(nextEvaluationText);
      snapshotRef.current = {
        ...snapshotRef.current,
        evaluationText: nextEvaluationText,
        evaluation: next,
      };
    }, [evaluationText, node.evaluation]);

    const parsed = parseEvaluationText(evaluationText);
    const metadataDirty =
      !isRoot &&
      (name !== snapshotRef.current.name ||
        comment !== snapshotRef.current.comment ||
        classification !== snapshotRef.current.classification);
    const evaluationDirty = parsed.error
      ? evaluationText !== snapshotRef.current.evaluationText
      : evaluationSignature(parsed.evaluation) !==
        evaluationSignature(snapshotRef.current.evaluation);
    const isDirty = metadataDirty || evaluationDirty;

    const save = useCallback(
      async (overrides?: Partial<SaveValues>): Promise<boolean> => {
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
          evaluationText:
            overrides?.evaluationText ?? evaluationText,
        };
        const currentEvaluation = parseEvaluationText(
          values.evaluationText,
        );
        if (currentEvaluation.error) {
          return false;
        }

        const snapshot = snapshotRef.current;
        const metadataChanged =
          !isRoot &&
          (values.name !== snapshot.name ||
            values.comment !== snapshot.comment ||
            values.classification !== snapshot.classification);
        const evaluationChanged =
          evaluationSignature(currentEvaluation.evaluation) !==
          evaluationSignature(snapshot.evaluation);
        if (!metadataChanged && !evaluationChanged) {
          return true;
        }

        const payload: NodeUpdatePayload = {};
        if (!isRoot) {
          payload.name = values.name;
          payload.comment = values.comment;
          payload.classification = values.classification;
        }
        if (evaluationChanged) {
          payload.evaluation = currentEvaluation.evaluation;
        }

        const promise = (async () => {
          setStatus("saving");
          setError(null);
          try {
            const updated = await updateNode(node.id, payload);
            const nextEvaluationText = updated.evaluation
              ? formatEvaluation(updated.evaluation)
              : "";
            const next: SnapshotValues = {
              name: updated.name ?? "",
              comment: updated.comment ?? "",
              classification: updated.classification ?? null,
              evaluationText: nextEvaluationText,
              evaluation: updated.evaluation ?? null,
            };
            setName(next.name);
            setComment(next.comment);
            setClassification(next.classification);
            setEvaluationText(nextEvaluationText);
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
      [
        classification,
        comment,
        evaluationText,
        isRoot,
        name,
        node.id,
        onSaved,
      ],
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

    const applyEvaluation = useCallback(
      (evaluation: Evaluation | null) => {
        if (status === "saving") {
          return;
        }
        const text = evaluation ? formatEvaluation(evaluation) : "";
        setEvaluationText(text);
        void save({ evaluationText: text });
      },
      [save, status],
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

    const statusLabel =
      status === "saving"
        ? "Guardando..."
        : status === "error"
          ? `Error: ${error ?? "No se pudo guardar."}`
          : parsed.error
            ? `Error: ${parsed.error}`
            : isDirty
              ? "Sin guardar"
              : "Guardado";
    const statusVariant =
      status === "error" || parsed.error
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

        <form className="current-move-form" onSubmit={handleSubmit}>
          {!isRoot && (
            <>
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
            </>
          )}

          {isRoot && (
            <p className="editor-info">
              En la posición inicial solo se puede editar la evaluación.
            </p>
          )}

          <div className="evaluation-row">
            <label className="form-field">
              <span className="evaluation-field-label">
                <span>Evaluación</span>
                <EvaluationSourceBadge evaluation={node.evaluation} />
              </span>
              <input
                type="text"
                value={evaluationText}
                onChange={(event) =>
                  setEvaluationText(event.target.value)
                }
                placeholder="ej. +0.35, -1,2, M3"
                aria-invalid={parsed.error !== null}
                aria-describedby={
                  parsed.error ? "evaluation-error" : undefined
                }
              />
            </label>

            {parsed.error && (
              <p
                id="evaluation-error"
                className="form-error"
                role="alert"
              >
                {parsed.error}
              </p>
            )}

            <div className="evaluation-presets">
              {EVAL_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  className="evaluation-preset"
                  onClick={() => applyEvaluation(preset.evaluation)}
                  disabled={status === "saving"}
                  title={`${preset.description} (${formatEvaluation(
                    preset.evaluation,
                  )})`}
                  aria-label={`${preset.description}: ${formatEvaluation(
                    preset.evaluation,
                  )}`}
                >
                  {preset.label}
                </button>
              ))}
              <button
                type="button"
                className="button button--small button--ghost"
                onClick={() => applyEvaluation(null)}
                disabled={status === "saving"}
              >
                Borrar
              </button>
            </div>
          </div>

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
              disabled={
                !isDirty || status === "saving" || parsed.error !== null
              }
            >
              Guardar
            </button>
          </div>
        </form>

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
