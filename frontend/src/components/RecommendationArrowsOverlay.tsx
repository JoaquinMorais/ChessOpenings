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

const GOLD = "#d4a017";
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
      const colorHead = arrowGeometry(from, to, 0.32, 0.12);
      const goldHead = arrow.covered
        ? arrowGeometry(from, to, 0.38, 0.15)
        : null;
      if (!colorHead || (arrow.covered && !goldHead)) {
        return null;
      }
      return {
        ...arrow,
        color: arrow.color ?? DEFAULT_COLOR,
        from,
        to,
        colorHead,
        goldHead,
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
        colorHead: ArrowGeometry;
        goldHead: ArrowGeometry | null;
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
            {arrow.goldHead && (
              <>
                <line
                  x1={arrow.from.x}
                  y1={arrow.from.y}
                  x2={arrow.goldHead.base.x}
                  y2={arrow.goldHead.base.y}
                  stroke={GOLD}
                  strokeWidth="0.17"
                  strokeLinecap="round"
                />
                <polygon
                  points={arrow.goldHead.points}
                  fill={GOLD}
                />
              </>
            )}
            <line
              x1={arrow.from.x}
              y1={arrow.from.y}
              x2={arrow.colorHead.base.x}
              y2={arrow.colorHead.base.y}
              stroke={arrow.color}
              strokeWidth={arrow.covered ? "0.11" : "0.12"}
              strokeLinecap="round"
            />
            <polygon
              points={arrow.colorHead.points}
              fill={arrow.color}
            />
          </Fragment>
        ))}
      </svg>
    </div>
  );
}

export default RecommendationArrowsOverlay;
