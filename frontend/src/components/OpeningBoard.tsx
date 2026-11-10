import type { CSSProperties } from "react";
import { Chessboard } from "react-chessboard";

interface OpeningBoardProps {
  fen: string;
  orientation: "white" | "black";
  disabled: boolean;
  squareStyles?: Record<string, CSSProperties>;
  boardWidth?: number;
  onPieceDrop: (sourceSquare: string, targetSquare: string) => boolean;
}

function OpeningBoard({
  fen,
  orientation,
  disabled,
  squareStyles,
  boardWidth,
  onPieceDrop,
}: OpeningBoardProps) {
  return (
    <div className="board-wrapper">
      <Chessboard
        position={fen}
        boardOrientation={orientation}
        customSquareStyles={squareStyles}
        boardWidth={boardWidth}
        onPieceDrop={(sourceSquare, targetSquare) =>
          onPieceDrop(sourceSquare, targetSquare)
        }
        arePiecesDraggable={!disabled}
      />
    </div>
  );
}

export default OpeningBoard;