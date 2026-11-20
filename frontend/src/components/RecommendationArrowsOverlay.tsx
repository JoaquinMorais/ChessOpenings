import { Fragment } from "react";

import type { BoardArrow } from "./ChessBoardView";

interface RecommendationArrowsOverlayProps {
  arrows: BoardArrow[];
  orientation: "white" | "black";
}

interface Point {
  x: number;
  y: number;
}

interface ArrowGeometry {
  base: Point;
  points: string;
}

const ACCENT = "#ef4444";
const DEFAULT_COLOR = "#1e40af";

function squareCenter(
  square: string,
  orientation: "white" | "black",
): Point | null {
  if (!/^[a-h][1-8]$/.test(square)) {
    return null;
  }
  const file = square.charCodeAt(0) - "a".charCodeAt(0);
  const rank = Number(square[1]);
  const column = orientation === "white" ? file : 7 - file;
  const row = orientation === "white" ? 8 - rank : rank - 1;
  return { x: column + 0.5, y: row + 0.5 };
}

function arrowGeometry(
  from: Point,
  to: Point,
  headLength: number,
  halfWidth: number,
): ArrowGeometry | null {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const length = Math.hypot(dx, dy);
  if (length === 0) {
    return null;
  }
  const ux = dx / length;
  const uy = dy / length;
  const base = {
    x: to.x - ux * headLength,
    y: to.y - uy * headLength,
  };
  const left = {
    x: base.x - uy * halfWidth,
    y: base.y + ux * halfWidth,
  };
  const right = {
    x: base.x + uy * halfWidth,
    y: base.y - ux * halfWidth,
  };
  return {
    base,
    points: `${to.x},${to.y} ${left.x},${left.y} ${right.x},${right.y}`,
  };
}

function RecommendationArrowsOverlay({
  arrows,
  orientation,
}: RecommendationArrowsOverlayProps) {
  const visibleArrows = arrows
    .map((arrow) => {
      const from = squareCenter(arrow.from, orientation);
      const to = squareCenter(arrow.to, orientation);
      if (!from || !to) {
        return null;
      }
      const head = arrowGeometry(from, to, 0.34, 0.13);
      if (!head) {
        return null;
      }
      return {
        ...arrow,
        color: arrow.color ?? DEFAULT_COLOR,
        from,
        to,
        head,
        key: `${arrow.from}-${arrow.to}-${arrow.color ?? DEFAULT_COLOR}`,
      };
    })
    .filter(
      (
        arrow,
      ): arrow is BoardArrow & {
        color: string;
        from: Point;
        to: Point;
        head: ArrowGeometry;
        key: string;
      } => arrow !== null,
    );

  if (visibleArrows.length === 0) {
    return null;
  }

  return (
    <div className="recommendation-arrows-overlay" aria-hidden="true">
      <svg viewBox="0 0 8 8" preserveAspectRatio="none">
        {visibleArrows.map((arrow) => (
          <Fragment key={arrow.key}>
            {arrow.covered && (
              <line
                x1={arrow.from.x}
                y1={arrow.from.y}
                x2={arrow.head.base.x}
                y2={arrow.head.base.y}
                stroke={ACCENT}
                strokeWidth="0.17"
                strokeLinecap="round"
              />
            )}
            <line
              x1={arrow.from.x}
              y1={arrow.from.y}
              x2={arrow.head.base.x}
              y2={arrow.head.base.y}
              stroke={arrow.color}
              strokeWidth={arrow.covered ? "0.11" : "0.12"}
              strokeLinecap="round"
            />
            <polygon
              points={arrow.head.points}
              fill={arrow.color}
              stroke={arrow.covered ? ACCENT : undefined}
              strokeWidth={arrow.covered ? "0.07" : undefined}
              strokeLinejoin="round"
            />
          </Fragment>
        ))}
      </svg>
    </div>
  );
}

export default RecommendationArrowsOverlay;
