import { useMemo } from "react";

import type { TreeNode } from "../types/node";

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
        {formatMoveLabel(node)}
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