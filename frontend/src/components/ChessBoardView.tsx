import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { CSSProperties } from "react";
import { Chess, type Square } from "chess.js";
import { Chessboard } from "react-chessboard";
import { TouchBackend } from "react-dnd-touch-backend";

import MoveBadgeOverlay from "./MoveBadgeOverlay";
import RecommendationArrowsOverlay from "./RecommendationArrowsOverlay";

export interface BoardLastMove {
  from: string;
  to: string;
}

export interface BoardBadge {
  square: string;
  classification: string;
}

export interface BoardArrow {
  from: string;
  to: string;
  color?: string;
  covered?: boolean;
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
  pickupEnabled?: boolean;
  boardWidth?: number;
  responsive?: boolean;
  badge?: BoardBadge | null;
  hintSquare?: string | null;
  recommendationArrows?: BoardArrow[];
}

const MOVE_DOT =
  "radial-gradient(circle, rgba(31, 61, 43, 0.38) 18%, transparent 19%)";
const CAPTURE_RING =
  "radial-gradient(circle, transparent 54%, rgba(31, 61, 43, 0.38) 56%, rgba(31, 61, 43, 0.38) 68%, transparent 70%)";
const MARK_RING =
  "radial-gradient(circle at center, transparent 0 52%, rgba(202, 52, 49, 0.92) 54%, rgba(202, 52, 49, 0.92) 66%, transparent 68%)";

const PROMOTION_OPTIONS: Array<{
  value: "q" | "r" | "b" | "n";
  label: string;
}> = [
  { value: "q", label: "Reina" },
  { value: "r", label: "Torre" },
  { value: "b", label: "Alfil" },
  { value: "n", label: "Caballo" },
];

interface PromotionState {
  from: Square;
  to: Square;
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
  pickupEnabled,
  boardWidth,
  responsive = false,
  badge,
  hintSquare,
  recommendationArrows,
}: ChessBoardViewProps) {
  const [selectedSquare, setSelectedSquare] = useState<Square | null>(null);
  const [promotion, setPromotion] = useState<PromotionState | null>(null);
  const [responsiveWidth, setResponsiveWidth] = useState<number | null>(null);
  const [markedSquares, setMarkedSquares] = useState<Set<Square>>(
    () => new Set(),
  );
  const [isDraggingPiece, setIsDraggingPiece] = useState(false);
  const boardRef = useRef<HTMLDivElement>(null);
  const dragDotElementsRef = useRef<HTMLElement[]>([]);
  const isDraggingPieceRef = useRef(false);
  const suppressNextDropRef = useRef(false);
  const dndManagerRef = useRef<Parameters<typeof TouchBackend>[0] | null>(
    null,
  );
  const dndBackend = useMemo<typeof TouchBackend>(
    () => (manager, context, options) => {
      dndManagerRef.current = manager;
      return TouchBackend(manager, context, options);
    },
    [],
  );
  const game = useMemo(() => new Chess(fen), [fen]);
  const pickupAvailable = pickupEnabled ?? !disabled;
  const canPickUp = pickupAvailable && !promotion;
  const canCommit = !disabled && !promotion;
  const canCommitRef = useRef(canCommit);
  const onMoveRef = useRef(onMove);
  canCommitRef.current = canCommit;
  onMoveRef.current = onMove;

  const clearDragDots = useCallback(() => {
    for (const element of dragDotElementsRef.current) {
      element.classList.remove("board-square-move", "board-square-capture");
    }
    dragDotElementsRef.current = [];
  }, []);

  const cancelDragging = useCallback(() => {
    if (!isDraggingPieceRef.current) {
      return;
    }
    suppressNextDropRef.current = true;
    dndManagerRef.current?.getActions().endDrag();
    isDraggingPieceRef.current = false;
    setIsDraggingPiece(false);
    setSelectedSquare(null);
    clearDragDots();
  }, [clearDragDots]);

  useEffect(() => {
    setSelectedSquare(null);
    setPromotion(null);
    setMarkedSquares(new Set());
    isDraggingPieceRef.current = false;
    suppressNextDropRef.current = false;
    setIsDraggingPiece(false);
    clearDragDots();
  }, [fen, pickupAvailable, clearDragDots]);

  useEffect(() => {
    const handleRightButton = (event: MouseEvent | PointerEvent) => {
      if (event.button !== 2 || !isDraggingPieceRef.current) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      cancelDragging();
    };

    const handleContextMenu = (event: MouseEvent) => {
      if (!isDraggingPieceRef.current) {
        return;
      }
      event.preventDefault();
      cancelDragging();
    };

    const handleDrop = (event: DragEvent) => {
      if (
        !isDraggingPieceRef.current ||
        (event.button !== 2 && event.buttons !== 2)
      ) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      cancelDragging();
    };

    window.addEventListener("pointerdown", handleRightButton, true);
    window.addEventListener("mousedown", handleRightButton, true);
    window.addEventListener("pointerup", handleRightButton, true);
    window.addEventListener("mouseup", handleRightButton, true);
    window.addEventListener("contextmenu", handleContextMenu, true);
    window.addEventListener("drop", handleDrop, true);
    return () => {
      window.removeEventListener("pointerdown", handleRightButton, true);
      window.removeEventListener("mousedown", handleRightButton, true);
      window.removeEventListener("pointerup", handleRightButton, true);
      window.removeEventListener("mouseup", handleRightButton, true);
      window.removeEventListener("contextmenu", handleContextMenu, true);
      window.removeEventListener("drop", handleDrop, true);
    };
  }, [cancelDragging]);

  useLayoutEffect(() => {
    if (!responsive) {
      setResponsiveWidth(null);
      return;
    }

    const board = boardRef.current;
    if (!board) {
      return;
    }

    const updateWidth = () => {
      const styles = window.getComputedStyle(board);
      const padding =
        Number.parseFloat(styles.paddingLeft) +
        Number.parseFloat(styles.paddingRight);
      const width = Math.floor(board.clientWidth - padding);
      if (width > 0) {
        setResponsiveWidth((current) =>
          current === width ? current : width,
        );
      }
    };

    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    observer.observe(board);
    return () => observer.disconnect();
  }, [responsive]);

  const legalMoves = useMemo(() => {
    if (!selectedSquare || !canPickUp) {
      return [];
    }
    return game.moves({ square: selectedSquare, verbose: true });
  }, [game, selectedSquare, canPickUp]);

  const applyDragDots = (sourceSquare: Square) => {
    clearDragDots();
    if (!canPickUp) {
      return;
    }

    const piece = game.get(sourceSquare);
    if (!piece || piece.color !== game.turn()) {
      return;
    }

    const board = boardRef.current;
    if (!board) {
      return;
    }

    const moves = game.moves({ square: sourceSquare, verbose: true });
    for (const move of moves) {
      const squareElement = board.querySelector(
        `[data-square="${move.to}"] > div`,
      );
      if (!(squareElement instanceof HTMLElement)) {
        continue;
      }
      const isCapture =
        move.flags.includes("c") || move.flags.includes("e");
      squareElement.classList.add(
        isCapture ? "board-square-capture" : "board-square-move",
      );
      dragDotElementsRef.current.push(squareElement);
    }
  };

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

    if (canPickUp) {
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

    if (hintSquare) {
      styles[hintSquare] = {
        ...(styles[hintSquare] ?? {}),
        boxShadow: "inset 0 0 0 4px rgba(92, 139, 176, 0.9)",
      };
    }

    for (const square of markedSquares) {
      const current = styles[square] ?? {};
      const currentImage = current.backgroundImage;
      styles[square] = {
        ...current,
        backgroundImage: currentImage
          ? `${MARK_RING}, ${currentImage}`
          : MARK_RING,
        backgroundSize: currentImage
          ? `100% 100%, ${current.backgroundSize ?? "100% 100%"}`
          : "100% 100%",
        backgroundPosition: currentImage
          ? `center, ${current.backgroundPosition ?? "center"}`
          : "center",
        backgroundRepeat: "no-repeat",
      };
    }

    return styles;
  }, [canPickUp, hintSquare, lastMove, legalMoves, markedSquares]);

  const isPromotionMove = (from: Square, to: Square): boolean => {
    const piece = game.get(from);
    return (
      piece?.type === "p" && (to[1] === "8" || to[1] === "1")
    );
  };

  const findCastlingTarget = (from: Square, to: Square): Square | null => {
    const king = game.get(from);
    const rook = game.get(to);
    if (
      king?.type !== "k" ||
      rook?.type !== "r" ||
      rook.color !== king.color
    ) {
      return null;
    }

    const rank = king.color === "w" ? "1" : "8";
    let target: Square | null = null;
    if (from === `e${rank}` && to === `h${rank}`) {
      target = `g${rank}` as Square;
    } else if (from === `e${rank}` && to === `a${rank}`) {
      target = `c${rank}` as Square;
    }

    if (!target) {
      return null;
    }

    const castleMove = game
      .moves({ square: from, verbose: true })
      .find(
        (move) =>
          move.to === target &&
          (move.flags.includes("k") || move.flags.includes("q")),
      );
    return castleMove ? target : null;
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
    const result = onMoveRef.current(toUci({ from, to, promotion }));
    if (typeof result === "boolean") {
      return result;
    }
    void result.catch(() => undefined);
    return true;
  };

  const handlePromotionSelect = (piece: "q" | "r" | "b" | "n") => {
    if (!promotion) {
      return;
    }
    const { from, to } = promotion;
    setPromotion(null);
    executeMove(from, to, piece);
  };

  const handleSquareClick = (square: Square) => {
    setMarkedSquares(new Set());
    if (!canPickUp) {
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

    const castleTarget = findCastlingTarget(selectedSquare, square);
    if (castleTarget) {
      if (!canCommit) {
        return;
      }
      executeMove(selectedSquare, castleTarget);
      setSelectedSquare(null);
      return;
    }

    const target = legalMoves.find((move) => move.to === square);
    if (target) {
      if (!canCommit) {
        return;
      }
      if (isPromotionMove(selectedSquare, square)) {
        setPromotion({ from: selectedSquare, to: square });
        setSelectedSquare(null);
        return;
      }
      executeMove(selectedSquare, square);
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

  const handleSquareRightClick = (square: Square) => {
    if (promotion) {
      return;
    }

    if (isDraggingPieceRef.current) {
      cancelDragging();
      return;
    }

    if (selectedSquare) {
      setSelectedSquare(null);
      clearDragDots();
      return;
    }

    setMarkedSquares((current) => {
      const next = new Set(current);
      if (next.has(square)) {
        next.delete(square);
      } else {
        next.add(square);
      }
      return next;
    });
  };

  const handlePieceDragBegin = (sourceSquare: Square) => {
    suppressNextDropRef.current = false;
    isDraggingPieceRef.current = true;
    setIsDraggingPiece(true);
    setSelectedSquare(null);
    setMarkedSquares(new Set());
    applyDragDots(sourceSquare);
  };

  const handlePieceDragEnd = () => {
    isDraggingPieceRef.current = false;
    setIsDraggingPiece(false);
    setSelectedSquare(null);
    clearDragDots();
  };

  const handlePieceDrop = (
    sourceSquare: Square,
    targetSquare: Square,
  ): boolean => {
    setSelectedSquare(null);
    clearDragDots();

    if (suppressNextDropRef.current) {
      suppressNextDropRef.current = false;
      isDraggingPieceRef.current = false;
      setIsDraggingPiece(false);
      return false;
    }

    if (!canCommitRef.current) {
      return false;
    }

    const piece = game.get(sourceSquare);
    if (!piece || piece.color !== game.turn()) {
      return false;
    }

    const effectiveTarget =
      findCastlingTarget(sourceSquare, targetSquare) ?? targetSquare;
    const moves = game.moves({ square: sourceSquare, verbose: true });
    if (!moves.some((move) => move.to === effectiveTarget)) {
      return false;
    }

    if (isPromotionMove(sourceSquare, effectiveTarget)) {
      setPromotion({ from: sourceSquare, to: effectiveTarget });
      return false;
    }

    return executeMove(sourceSquare, effectiveTarget);
  };

  const hasSquareStyles = Object.keys(squareStyles).length > 0;
  const resolvedBoardWidth = responsive ? responsiveWidth : boardWidth ?? 400;
  const arrowsAllowed = !selectedSquare && !isDraggingPiece && !promotion;

  return (
    <div className="board-wrapper" ref={boardRef}>
      <div
        className="board-area"
        onContextMenu={(event) => event.preventDefault()}
      >
        {resolvedBoardWidth !== null && (
          <Chessboard
            key={responsive ? resolvedBoardWidth : undefined}
            id={canPickUp ? "board-enabled" : "board-disabled"}
            position={fen}
            boardOrientation={orientation}
            boardWidth={resolvedBoardWidth}
            customSquareStyles={hasSquareStyles ? squareStyles : undefined}
            customDndBackend={dndBackend}
            customDndBackendOptions={{
              enableMouseEvents: true,
              enableTouchEvents: true,
            }}
            areArrowsAllowed={arrowsAllowed}
            onSquareClick={(square) =>
              handleSquareClick(square as Square)
            }
            onSquareRightClick={(square) =>
              handleSquareRightClick(square as Square)
            }
            onPieceDragBegin={(_piece, sourceSquare) =>
              handlePieceDragBegin(sourceSquare as Square)
            }
            onPieceDragEnd={handlePieceDragEnd}
            onPieceDrop={(sourceSquare, targetSquare) =>
              handlePieceDrop(
                sourceSquare as Square,
                targetSquare as Square,
              )
            }
            isDraggablePiece={({ piece }) =>
              canPickUp && piece[0] === game.turn()
            }
            arePiecesDraggable={canPickUp}
          />
        )}

        <RecommendationArrowsOverlay
          arrows={recommendationArrows ?? []}
          orientation={orientation}
        />

        <MoveBadgeOverlay
          square={badge?.square ?? null}
          classification={badge?.classification ?? null}
          orientation={orientation}
        />
      </div>

      {promotion && (
        <div className="promotion-overlay" role="presentation">
          <section
            className="promotion-dialog"
            role="dialog"
            aria-modal="true"
            aria-label="Elegir pieza para promocionar"
          >
            <p className="card-label">Promoción</p>
            <h3>Elegí una pieza</h3>
            <div className="promotion-options">
              {PROMOTION_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className="button button--ghost"
                  onClick={() => handlePromotionSelect(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <button
              type="button"
              className="button button--small"
              onClick={() => setPromotion(null)}
            >
              Cancelar
            </button>
          </section>
        </div>
      )}
    </div>
  );
}

export default ChessBoardView;