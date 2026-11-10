import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { Chess, type Square } from "chess.js";
import { Chessboard } from "react-chessboard";

export interface BoardLastMove {
  from: string;
  to: string;
}

export interface BoardBadge {
  symbol: string;
  color: string;
}

export type BoardMove =
  | string
  | { from: string; to: string; promotion?: string };

interface ChessBoardViewProps {
  fen: string;
  orientation: "white" | "black";
  onMove: (move: BoardMove) => boolean | Promise<boolean>;
  lastMove: BoardLastMove | null;
  disabled: boolean;
  boardWidth?: number;
  lastMoveBadge?: BoardBadge | null;
}

const MOVE_DOT =
  "radial-gradient(circle, rgba(31, 61, 43, 0.38) 18%, transparent 19%)";
const CAPTURE_RING =
  "radial-gradient(circle, transparent 54%, rgba(31, 61, 43, 0.38) 56%, rgba(31, 61, 43, 0.38) 68%, transparent 70%)";

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function badgeBackground(symbol: string, color: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text x="82" y="26" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="30" font-weight="700" fill="${escapeXml(
    color,
  )}">${escapeXml(symbol)}</text></svg>`;
  return `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;
}

function toUci(move: BoardMove): string {
  return typeof move === "string"
    ? move
    : `${move.from}${move.to}${move.promotion ?? ""}`;
}

function ChessBoardView({
  fen,
  orientation,
  onMove,
  lastMove,
  disabled,
  boardWidth,
  lastMoveBadge,
}: ChessBoardViewProps) {
  const [selectedSquare, setSelectedSquare] = useState<Square | null>(null);
  const game = useMemo(() => new Chess(fen), [fen]);

  useEffect(() => {
    setSelectedSquare(null);
  }, [fen, disabled]);

  const legalMoves = useMemo(() => {
    if (!selectedSquare || disabled) {
      return [];
    }
    return game.moves({ square: selectedSquare, verbose: true });
  }, [game, selectedSquare, disabled]);

  const squareStyles = useMemo(() => {
    const styles: Record<string, CSSProperties> = {};

    if (lastMove) {
      styles[lastMove.from] = {
        ...(styles[lastMove.from] ?? {}),
        backgroundColor: "rgba(247, 197, 49, 0.5)",
      };
      styles[lastMove.to] = {
        ...(styles[lastMove.to] ?? {}),
        backgroundColor: "rgba(247, 197, 49, 0.5)",
      };
    }

    if (!disabled) {
      for (const move of legalMoves) {
        const isCapture =
          move.flags.includes("c") || move.flags.includes("e");
        styles[move.to] = {
          ...(styles[move.to] ?? {}),
          backgroundImage: isCapture ? CAPTURE_RING : MOVE_DOT,
          backgroundSize: "100% 100%",
          backgroundPosition: "center",
        };
      }
    }

    if (lastMoveBadge && lastMove) {
      const badge = badgeBackground(lastMoveBadge.symbol, lastMoveBadge.color);
      const existing = styles[lastMove.to] ?? {};
      styles[lastMove.to] = {
        ...existing,
        backgroundImage: existing.backgroundImage
          ? `${badge}, ${existing.backgroundImage}`
          : badge,
        backgroundSize: existing.backgroundSize ?? "100% 100%",
        backgroundPosition: existing.backgroundPosition ?? "center",
      };
    }

    return styles;
  }, [disabled, lastMove, lastMoveBadge, legalMoves]);

  const isPromotionMove = (from: Square, to: Square): boolean => {
    const piece = game.get(from);
    return (
      piece?.type === "p" && (to[1] === "8" || to[1] === "1")
    );
  };

  const selectSquare = (square: Square) => {
    const piece = game.get(square);
    if (!piece || piece.color !== game.turn()) {
      setSelectedSquare(null);
      return;
    }
    setSelectedSquare(square);
  };

  const executeMove = (
    from: Square,
    to: Square,
    promotion?: string,
  ): boolean => {
    const result = onMove(toUci({ from, to, promotion }));
    if (typeof result === "boolean") {
      return result;
    }
    void result.catch(() => undefined);
    return true;
  };

  const handleSquareClick = (square: Square) => {
    if (disabled) {
      return;
    }

    if (!selectedSquare) {
      selectSquare(square);
      return;
    }

    if (square === selectedSquare) {
      setSelectedSquare(null);
      return;
    }

    const target = legalMoves.find((move) => move.to === square);
    if (target) {
      const promotion = isPromotionMove(selectedSquare, square) ? "q" : undefined;
      executeMove(selectedSquare, square, promotion);
      setSelectedSquare(null);
      return;
    }

    const piece = game.get(square);
    if (piece && piece.color === game.turn()) {
      setSelectedSquare(square);
      return;
    }

    setSelectedSquare(null);
  };

  const handlePieceDrop = (
    sourceSquare: Square,
    targetSquare: Square,
  ): boolean => {
    setSelectedSquare(null);

    if (disabled) {
      return false;
    }

    const piece = game.get(sourceSquare);
    if (!piece || piece.color !== game.turn()) {
      return false;
    }

    const moves = game.moves({ square: sourceSquare, verbose: true });
    if (!moves.some((move) => move.to === targetSquare)) {
      return false;
    }

    const promotion = isPromotionMove(sourceSquare, targetSquare)
      ? "q"
      : undefined;
    return executeMove(sourceSquare, targetSquare, promotion);
  };

  const hasSquareStyles = Object.keys(squareStyles).length > 0;
  const resolvedBoardWidth = boardWidth ?? 400;

  return (
    <div className="board-wrapper">
      <Chessboard
        position={fen}
        boardOrientation={orientation}
        boardWidth={resolvedBoardWidth}
        customSquareStyles={hasSquareStyles ? squareStyles : undefined}
        onSquareClick={(square) => handleSquareClick(square as Square)}
        onPieceDragBegin={(_piece, sourceSquare) => {
          if (!disabled) {
            setSelectedSquare(sourceSquare as Square);
          }
        }}
        onPieceDragEnd={() => setSelectedSquare(null)}
        onPieceDrop={(sourceSquare, targetSquare) =>
          handlePieceDrop(
            sourceSquare as Square,
            targetSquare as Square,
          )
        }
        isDraggablePiece={({ piece }) =>
          !disabled && piece[0] === game.turn()
        }
        arePiecesDraggable={!disabled}
      />
    </div>
  );
}

export default ChessBoardView;