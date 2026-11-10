import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Chess } from "chess.js";

import { ApiError } from "../api/client";
import { addMove, deleteNode, getTree, makeMain } from "../api/nodes";
import { getOpening } from "../api/openings";
import ChessBoardView from "../components/ChessBoardView";
import type { BoardLastMove, BoardMove } from "../components/ChessBoardView";
import VariationTree, {
  formatMoveLabel,
} from "../components/VariationTree";
import type { NodeRead, TreeNode } from "../types/node";
import type { OpeningSummary } from "../types/opening";

interface TreeIndex {
  byId: Map<number, TreeNode>;
  parentById: Map<number, number | null>;
}

const COLOR_LABELS = {
  white: "Blancas",
  black: "Negras",
} as const;

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Ocurrió un error inesperado.";
}

function indexTree(root: TreeNode): TreeIndex {
  const byId = new Map<number, TreeNode>();
  const parentById = new Map<number, number | null>();

  const visit = (node: TreeNode, parentId: number | null) => {
    byId.set(node.id, node);
    parentById.set(node.id, parentId);
    node.children.forEach((child) => visit(child, node.id));
  };

  visit(root, null);
  return { byId, parentById };
}

function insertChild(
  root: TreeNode,
  parentId: number,
  child: TreeNode,
): TreeNode {
  if (root.id === parentId) {
    if (root.children.some((existing) => existing.id === child.id)) {
      return root;
    }
    return {
      ...root,
      children: [...root.children, child].sort(
        (left, right) => left.order_index - right.order_index,
      ),
    };
  }

  return {
    ...root,
    children: root.children.map((existing) =>
      insertChild(existing, parentId, child),
    ),
  };
}

function toTreeNode(node: NodeRead): TreeNode {
  return {
    id: node.id,
    san: node.move_san,
    uci: node.move_uci,
    fen: node.fen,
    ply: node.ply,
    order_index: node.order_index,
    comment: node.comment,
    children: [],
  };
}

function countSubtree(node: TreeNode): number {
  return (
    1 +
    node.children.reduce(
      (total, child) => total + countSubtree(child),
      0,
    )
  );
}

function uciToLastMove(uci: string | null): BoardLastMove | null {
  if (!uci) {
    return null;
  }
  return { from: uci.slice(0, 2), to: uci.slice(2, 4) };
}

function OpeningEditorPage() {
  const { id } = useParams<{ id: string }>();
  const openingId = Number(id);
  const [opening, setOpening] = useState<OpeningSummary | null>(null);
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [currentNodeId, setCurrentNodeId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [moveError, setMoveError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [branchBusy, setBranchBusy] = useState(false);

  const loadEditor = useCallback(async () => {
    if (!id || !Number.isInteger(openingId) || openingId <= 0) {
      setLoading(false);
      setLoadError("La apertura no existe.");
      return;
    }

    setLoading(true);
    setLoadError(null);
    setMoveError(null);
    setActionError(null);
    try {
      const [openingData, treeData] = await Promise.all([
        getOpening(openingId),
        getTree(openingId),
      ]);
      setOpening(openingData);
      setTree(treeData);
      setCurrentNodeId(treeData.id);
    } catch (error) {
      setLoadError(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [id, openingId]);

  useEffect(() => {
    void loadEditor();
  }, [loadEditor]);

  const refreshTree = useCallback(
    async (preferredId: number | null, fallbackId: number | null) => {
      if (!Number.isInteger(openingId) || openingId <= 0) {
        return;
      }
      const treeData = await getTree(openingId);
      const nextIndex = indexTree(treeData);
      setTree(treeData);

      const candidates = [preferredId, fallbackId, treeData.id];
      const nextId =
        candidates.find(
          (candidate): candidate is number =>
            candidate !== null && nextIndex.byId.has(candidate),
        ) ?? treeData.id;
      setCurrentNodeId(nextId);
    },
    [openingId],
  );

  const index = useMemo(() => (tree ? indexTree(tree) : null), [tree]);
  const currentNode =
    index && currentNodeId !== null
      ? index.byId.get(currentNodeId) ?? null
      : null;
  const currentFen = currentNode?.fen ?? tree?.fen ?? null;
  const currentLastMove = uciToLastMove(currentNode?.uci ?? null);
  const turn = currentFen ? new Chess(currentFen).turn() : null;
  const isUserTurn =
    opening && turn
      ? turn === (opening.color === "white" ? "w" : "b")
      : false;
  const orientation = opening?.color === "black" ? "black" : "white";
  const principalChild = currentNode?.children[0] ?? null;
  const canGoBack =
    currentNode !== null &&
    index !== null &&
    index.parentById.get(currentNode.id) != null;
  const canGoForward = principalChild !== null;
  const atStart = tree !== null && currentNode?.id === tree.id;
  const currentParentId =
    currentNode && index
      ? index.parentById.get(currentNode.id) ?? null
      : null;
  const currentIsMain = currentNode?.order_index === 0;
  const rivalResponses = !isUserTurn ? currentNode?.children ?? [] : [];

  const saveMove = useCallback(
    async (openingId: number, parentId: number, uci: string) => {
      setSaving(true);
      setMoveError(null);
      setActionError(null);
      try {
        const created = await addMove(openingId, {
          parent_id: parentId,
          move: uci,
        });
        const child = toTreeNode(created);
        setTree((previous) =>
          previous ? insertChild(previous, parentId, child) : previous,
        );
        setCurrentNodeId(created.id);
      } catch (error) {
        setMoveError(getErrorMessage(error));
      } finally {
        setSaving(false);
      }
    },
    [],
  );

  const handleMove = (move: BoardMove): boolean => {
    if (!opening || !currentNode || saving || branchBusy) {
      return false;
    }

    const uci =
      typeof move === "string"
        ? move
        : `${move.from}${move.to}${move.promotion ?? ""}`;
    const existing = currentNode.children.find((child) => child.uci === uci);
    if (existing) {
      setCurrentNodeId(existing.id);
      setMoveError(null);
      setActionError(null);
      return true;
    }

    void saveMove(opening.id, currentNode.id, uci);
    return true;
  };

  const goBack = () => {
    if (!currentNode || !index) {
      return;
    }
    const parentId = index.parentById.get(currentNode.id);
    if (parentId != null) {
      setCurrentNodeId(parentId);
      setMoveError(null);
    }
  };

  const goForward = () => {
    if (principalChild) {
      setCurrentNodeId(principalChild.id);
      setMoveError(null);
    }
  };

  const goStart = () => {
    if (tree) {
      setCurrentNodeId(tree.id);
      setMoveError(null);
    }
  };

  const handleMakeMain = async () => {
    if (
      !currentNode ||
      currentParentId === null ||
      currentIsMain ||
      branchBusy
    ) {
      return;
    }

    setBranchBusy(true);
    setActionError(null);
    setMoveError(null);
    try {
      await makeMain(currentNode.id);
      await refreshTree(currentNode.id, currentParentId);
    } catch (error) {
      setActionError(getErrorMessage(error));
    } finally {
      setBranchBusy(false);
    }
  };

  const handleDeleteBranch = async () => {
    if (!currentNode || currentParentId === null || branchBusy) {
      return;
    }

    const totalMoves = countSubtree(currentNode);
    const moveLabel = currentNode.san
      ? `"${currentNode.san}"`
      : "esta rama";
    const moveCount =
      totalMoves === 1 ? "1 jugada" : `${totalMoves} jugadas`;
    const confirmed = window.confirm(
      `¿Eliminar ${moveLabel}? Se borrarán ${moveCount}, incluyendo sus subramas.`,
    );
    if (!confirmed) {
      return;
    }

    setBranchBusy(true);
    setActionError(null);
    setMoveError(null);
    try {
      await deleteNode(currentNode.id);
      setCurrentNodeId(currentParentId);
      await refreshTree(null, currentParentId);
    } catch (error) {
      setActionError(getErrorMessage(error));
    } finally {
      setBranchBusy(false);
    }
  };

  if (loading) {
    return (
      <section className="page">
        <div className="state-card">
          <p>Cargando editor...</p>
        </div>
      </section>
    );
  }

  if (loadError) {
    return (
      <section className="page">
        <div className="page-heading">
          <p className="eyebrow">Editor</p>
          <h2>No se pudo cargar el editor</h2>
          <p>{loadError}</p>
        </div>
        <div className="state-card state-card--error">
          <div className="form-actions">
            <Link className="button button--ghost" to="/openings">
              Volver a aperturas
            </Link>
            <button
              type="button"
              className="button"
              onClick={() => void loadEditor()}
            >
              Reintentar
            </button>
          </div>
        </div>
      </section>
    );
  }

  if (!opening || !tree || !currentNode || !currentFen) {
    return (
      <section className="page">
        <div className="state-card">
          <p>Cargando editor...</p>
        </div>
      </section>
    );
  }

  return (
    <section className="page">
      <div className="page-toolbar">
        <div className="page-heading">
          <p className="eyebrow">Editor</p>
          <h2>{opening.name}</h2>
          <p>
            {COLOR_LABELS[opening.color]} · Jugada {currentNode.ply}
          </p>
        </div>
        <Link className="button button--ghost" to="/openings">
          Volver a aperturas
        </Link>
      </div>

      <div
        className={`turn-banner ${
          isUserTurn ? "turn-banner--user" : "turn-banner--rival"
        }`}
      >
        <strong>{isUserTurn ? "Tu turno" : "Turno del rival"}</strong>
        <span>
          {isUserTurn
            ? `Juegas con ${COLOR_LABELS[opening.color]}.`
            : "Agregando una rama del rival."}
        </span>
      </div>

      {moveError && (
        <div className="alert" role="alert">
          <p>{moveError}</p>
          <button type="button" onClick={() => setMoveError(null)}>
            Cerrar
          </button>
        </div>
      )}

      {actionError && (
        <div className="alert" role="alert">
          <p>{actionError}</p>
          <button type="button" onClick={() => setActionError(null)}>
            Cerrar
          </button>
        </div>
      )}

      <div className="editor-layout">
        <div className="editor-board">
          <ChessBoardView
            fen={currentFen}
            orientation={orientation}
            disabled={saving || branchBusy}
            lastMove={currentLastMove}
            onMove={handleMove}
          />
          {(saving || branchBusy) && (
            <p className="state-message">
              {saving ? "Guardando jugada..." : "Actualizando ramas..."}
            </p>
          )}
        </div>

        <aside className="editor-sidebar">
          <section className="panel">
            <p className="card-label">Navegación</p>
            <div className="editor-controls">
              <button
                type="button"
                className="button button--ghost"
                onClick={goStart}
                disabled={atStart || branchBusy}
              >
                Inicio
              </button>
              <button
                type="button"
                className="button button--ghost"
                onClick={goBack}
                disabled={!canGoBack || branchBusy}
              >
                Atrás
              </button>
              <button
                type="button"
                className="button button--ghost"
                onClick={goForward}
                disabled={!canGoForward || branchBusy}
              >
                Adelante
              </button>
            </div>
          </section>

          <section className="panel editor-tree-panel">
            <p className="card-label">Jugadas</p>
            <VariationTree
              root={tree}
              currentNodeId={currentNode.id}
              onSelect={(nodeId) => {
                if (branchBusy) {
                  return;
                }
                setCurrentNodeId(nodeId);
                setMoveError(null);
                setActionError(null);
              }}
            />
          </section>

          {!isUserTurn && (
            <section className="panel">
              <p className="card-label">Respuestas del rival</p>
              {rivalResponses.length > 0 ? (
                <div className="response-list">
                  {rivalResponses.map((response) => (
                    <button
                      key={response.id}
                      type="button"
                      className="button button--small response-button"
                      onClick={() => {
                        if (branchBusy) {
                          return;
                        }
                        setCurrentNodeId(response.id);
                        setMoveError(null);
                        setActionError(null);
                      }}
                      disabled={branchBusy}
                    >
                      <span>{formatMoveLabel(response)}</span>
                      {response.order_index === 0 && (
                        <span className="response-badge">Principal</span>
                      )}
                    </button>
                  ))}
                </div>
              ) : (
                <p className="editor-info">
                  No hay respuestas cargadas. Juega en el tablero para agregar
                  una rama del rival.
                </p>
              )}
            </section>
          )}

          {currentParentId !== null && (
            <section className="panel">
              <p className="card-label">Rama actual</p>
              <p className="editor-info">{formatMoveLabel(currentNode)}</p>
              <div className="branch-actions">
                <button
                  type="button"
                  className="button button--small"
                  onClick={() => void handleMakeMain()}
                  disabled={branchBusy || currentIsMain}
                >
                  {branchBusy ? "Actualizando..." : "Hacer principal"}
                </button>
                <button
                  type="button"
                  className="button button--small button--danger"
                  onClick={() => void handleDeleteBranch()}
                  disabled={branchBusy}
                >
                  {branchBusy ? "Actualizando..." : "Eliminar rama"}
                </button>
              </div>
              {currentIsMain && (
                <p className="editor-hint">
                  Esta rama ya es la principal.
                </p>
              )}
            </section>
          )}

          <section className="panel">
            <p className="card-label">Posición actual</p>
            <p className="editor-info">
              {currentNode.children.length > 0
                ? `${currentNode.children.length} rama(s) desde esta posición`
                : "Sin jugadas cargadas desde esta posición"}
            </p>
            <p className="editor-move">
              {currentNode.san ? (
                <>
                  Última jugada: <code>{currentNode.san}</code>
                </>
              ) : (
                "Posición inicial"
              )}
            </p>
          </section>
        </aside>
      </div>
    </section>
  );
}

export default OpeningEditorPage;