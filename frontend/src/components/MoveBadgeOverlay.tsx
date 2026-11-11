import { getClassification } from "../types/classifications";
import ClassificationBadge from "./ClassificationBadge";

interface MoveBadgeOverlayProps {
  square: string | null;
  classification: string | null;
  orientation: "white" | "black";
}

const SQUARE_PERCENT = 100 / 8;

function badgePosition(
  square: string,
  orientation: "white" | "black",
): { left: number; top: number } | null {
  if (!/^[a-h][1-8]$/.test(square)) {
    return null;
  }

  const file = square.charCodeAt(0) - "a".charCodeAt(0);
  const rank = Number(square[1]);
  const column = orientation === "white" ? file : 7 - file;
  const row = orientation === "white" ? 8 - rank : rank - 1;

  return {
    left: column * SQUARE_PERCENT,
    top: row * SQUARE_PERCENT,
  };
}

function MoveBadgeOverlay({
  square,
  classification,
  orientation,
}: MoveBadgeOverlayProps) {
  const definition = getClassification(classification);
  if (!square || !definition) {
    return null;
  }

  const position = badgePosition(square, orientation);
  if (!position) {
    return null;
  }

  const smallSymbol = definition.symbol.length > 1;

  return (
    <div className="move-badge-overlay" aria-hidden="true">
      <div
        className="move-badge-cell"
        style={{
          left: `${position.left}%`,
          top: `${position.top}%`,
        }}
      >
        <div
          key={`${square}-${classification}-${orientation}`}
          className={`move-badge ${
            smallSymbol ? "move-badge--small" : ""
          }`}
        >
          <ClassificationBadge
            classification={classification}
            size="fill"
          />
        </div>
      </div>
    </div>
  );
}

export default MoveBadgeOverlay;
