import { Chessboard } from "react-chessboard";

interface OpeningBoardProps {
  fen: string;
  orientation: "white" | "black";
  disabled: boolean;
  onPieceDrop: (sourceSquare: string, targetSquare: string) => boolean;
}

function OpeningBoard({
  fen,
  orientation,
  disabled,
  onPieceDrop,
}: OpeningBoardProps) {
  return (
    <div className="board-wrapper">
      <Chessboard
        position={fen}
        boardOrientation={orientation}
        onPieceDrop={(sourceSquare, targetSquare) =>
          onPieceDrop(sourceSquare, targetSquare)
        }
        arePiecesDraggable={!disabled}
      />
    </div>
  );
}

export default OpeningBoard;