import { useMemo } from "react";

import { getClassification } from "../types/classifications";
import type { Evaluation } from "../types/evaluation";
import type { TreeNode } from "../types/node";
import { formatEvaluation } from "../utils/evaluation";
import ClassificationBadge from "./ClassificationBadge";
import EvaluationSourceBadge from "./EvaluationSourceBadge";

interface VariationTreeProps {
  root: TreeNode;
  currentNodeId: number;
  onSelect: (nodeId: number) => void;
}

export function formatMoveLabel(node: TreeNode): string {
  if (!node.san) {
    return "Inicio";
  }
  const moveNumber = Math.ceil(node.ply / 2);
  const prefix = node.ply % 2 === 1 ? `${moveNumber}.` : `${moveNumber}...`;
  return `${prefix} ${node.san}`;
}

function hasEvaluation(evaluation: Evaluation | null): boolean {
  if (!evaluation) {
    return false;
  }
  return (
    typeof evaluation.cp === "number" ||
    (typeof evaluation.mate === "number" && evaluation.mate !== 0)
  );
}

function evaluationTone(
  evaluation: Evaluation,
): "white" | "black" | "equal" {
  if (typeof evaluation.mate === "number" && evaluation.mate !== 0) {
    return evaluation.mate > 0 ? "white" : "black";
  }
  if (typeof evaluation.cp === "number") {
    if (evaluation.cp > 0) {
      return "white";
    }
    if (evaluation.cp < 0) {
      return "black";
    }
  }
  return "equal";
}

function collectMainLine(root: TreeNode): Set<number> {
  const ids = new Set<number>();
  let current: TreeNode | undefined = root;
  while (current) {
    ids.add(current.id);
    current = current.children[0];
  }
  return ids;
}

interface BranchProps {
  node: TreeNode;
  mainLineIds: Set<number>;
  currentNodeId: number;
  onSelect: (nodeId: number) => void;
  isRoot?: boolean;
}

function Branch({
  node,
  mainLineIds,
  currentNodeId,
  onSelect,
  isRoot = false,
}: BranchProps) {
  const children = [...node.children].sort(
    (left, right) => left.order_index - right.order_index,
  );
  const isCurrent = node.id === currentNodeId;
  const classification = getClassification(node.classification);
  const showEvaluation =
    node.evaluation !== null && hasEvaluation(node.evaluation);

  return (
    <div className={isRoot ? "variation-root" : "variation-node"}>
      <button
        type="button"
        className={[
          "variation-button",
          mainLineIds.has(node.id) ? "variation-button--main" : "",
          isRoot ? "variation-button--root" : "",
          isCurrent ? "variation-button--current" : "",
        ]
          .filter(Boolean)
          .join(" ")}
        onClick={() => onSelect(node.id)}
        aria-current={isCurrent ? "true" : undefined}
      >
        <span
          className="variation-move"
          style={
            classification && !isCurrent
              ? { color: classification.color }
              : undefined
          }
        >
          {formatMoveLabel(node)}
        </span>
        <ClassificationBadge
          classification={node.classification}
          size="sm"
        />
        {showEvaluation && node.evaluation && (
          <span
            className={`variation-evaluation variation-evaluation--${evaluationTone(
              node.evaluation,
            )}`}
          >
            {formatEvaluation(node.evaluation)}
          </span>
        )}
        <EvaluationSourceBadge evaluation={node.evaluation} />
        {node.name && (
          <span className="variation-name"> · {node.name}</span>
        )}
        {node.comment && (
          <span
            className="variation-comment-icon"
            title={node.comment}
            aria-label="Tiene observaciones"
          >
            ✎
          </span>
        )}
      </button>

      {children.length > 0 && (
        <ul className="variation-list">
          {children.map((child, index) => (
            <li
              key={child.id}
              className={
                index === 0
                  ? "variation-item"
                  : "variation-item variation-item--branch"
              }
            >
              <Branch
                node={child}
                mainLineIds={mainLineIds}
                currentNodeId={currentNodeId}
                onSelect={onSelect}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function VariationTree({
  root,
  currentNodeId,
  onSelect,
}: VariationTreeProps) {
  const mainLineIds = useMemo(() => collectMainLine(root), [root]);

  return (
    <div className="variation-tree">
      <Branch
        node={root}
        mainLineIds={mainLineIds}
        currentNodeId={currentNodeId}
        onSelect={onSelect}
        isRoot
      />
    </div>
  );
}

export default VariationTree;