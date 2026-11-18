import type { RecommendationMove } from "../types/recommendation";
import { recommendationColor } from "../types/recommendation";

interface RecommendationPanelProps {
  isUserTurn: boolean;
  loading: boolean;
  error: string | null;
  moves: RecommendationMove[];
}

function RecommendationPanel({
  isUserTurn,
  loading,
  error,
  moves,
}: RecommendationPanelProps) {

  return (
    <section className="panel recommendation-panel">
      <div className="recommendation-heading">
        <p className="card-label">Recomendaciones</p>
        <span className="recommendation-source">Stockfish</span>
      </div>

      {isUserTurn ? (
        <p className="editor-info">
          Se muestran cuando mueve el rival.
        </p>
      ) : loading ? (
        <p className="editor-info" role="status">
          Analizando posición...
        </p>
      ) : error ? (
        <p className="recommendation-error" role="alert">
          {error}
        </p>
      ) : moves.length === 0 ? (
        <p className="editor-info">Sin jugadas legales.</p>
      ) : (
        <>
          <p className="editor-info">
            Las flechas muestran las mejores jugadas del rival.
          </p>
          <ul className="recommendation-list">
            {moves.map((move) => (
              <li key={`${move.rank}-${move.uci}`} className="recommendation-item">
                <span
                  className="recommendation-dot"
                  style={{ backgroundColor: recommendationColor(move.rank) }}
                  aria-hidden="true"
                />
                <span>Top {move.rank}</span>
                <strong>{move.san}</strong>
                {move.covered && (
                  <span className="recommendation-covered">Cubierta</span>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

export default RecommendationPanel;
