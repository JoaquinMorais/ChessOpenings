import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Chess, type Move } from "chess.js";

import { ApiError } from "../api/client";
import { getOpening } from "../api/openings";
import {
  answerTrainingSession,
  createTrainingSession,
  getTrainingSession,
} from "../api/training";
import ChessBoardView from "../components/ChessBoardView";
import type { BoardLastMove, BoardMove } from "../components/ChessBoardView";
import type { OpeningSummary } from "../types/opening";
import type {
  TrainingQuestionStep,
  TrainingSession,
  TrainingStep,
} from "../types/training";

const INITIAL_FEN = new Chess().fen();
const RIVAL_DELAY = 600;
const CORRECT_DELAY = 700;

function getBoardWidth(): number {
  const stacked = window.innerWidth <= 860;
  const reservedWidth = stacked ? 64 : 360 + 96;
  const availableWidth = window.innerWidth - reservedWidth;
  const availableHeight = window.innerHeight - 160;
  return Math.max(280, Math.min(760, availableWidth, availableHeight));
}

const COLOR_LABELS = {
  white: "Blancas",
  black: "Negras",
} as const;

type Phase =
  | "loading"
  | "resume"
  | "animating"
  | "question"
  | "answering"
  | "correct"
  | "incorrect"
  | "finished"
  | "error";

interface IncorrectFeedback {
  correctSan: string;
  nextStep: TrainingStep;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Ocurrió un error inesperado.";
}

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

function trainingSessionKey(openingId: number): string {
  return `chess-openings-training-session-${openingId}`;
}

function uciToLastMove(uci: string | null | undefined): BoardLastMove | null {
  if (!uci) {
    return null;
  }
  return { from: uci.slice(0, 2), to: uci.slice(2, 4) };
}

function lastMoveFromLeadIn(step: TrainingQuestionStep): BoardLastMove | null {
  const move = step.lead_in[step.lead_in.length - 1];
  return move ? uciToLastMove(move.uci) : null;
}

function TrainingPage() {
  const { id } = useParams<{ id: string }>();
  const openingId = Number(id);
  const [opening, setOpening] = useState<OpeningSummary | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [step, setStep] = useState<TrainingStep | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [boardFen, setBoardFen] = useState(INITIAL_FEN);
  const [error, setError] = useState<string | null>(null);
  const [resumeSession, setResumeSession] = useState<TrainingSession | null>(
    null,
  );
  const [feedback, setFeedback] = useState<IncorrectFeedback | null>(null);
  const [lastMove, setLastMove] = useState<BoardLastMove | null>(null);
  const [boardWidth, setBoardWidth] = useState(getBoardWidth);
  const animationTokenRef = useRef(0);
  const startedForRef = useRef<string | null>(null);

  useEffect(() => {
    const handleResize = () => setBoardWidth(getBoardWidth());
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const runStep = useCallback(
    async (nextStep: TrainingStep) => {
      const token = animationTokenRef.current + 1;
      animationTokenRef.current = token;
      setError(null);
      setFeedback(null);
      setLastMove(null);
      setStep(nextStep);

      if (nextStep.kind === "finished") {
        setPhase("finished");
        if (Number.isInteger(openingId) && openingId > 0) {
          window.localStorage.removeItem(trainingSessionKey(openingId));
        }
        return;
      }

      setPhase("animating");
      const game = new Chess();
      setBoardFen(game.fen());

      for (const move of nextStep.lead_in) {
        if (animationTokenRef.current !== token) {
          return;
        }

        let applied: Move | null = null;
        try {
          applied = game.move(move.uci);
        } catch {
          applied = null;
        }
        if (!applied) {
          continue;
        }

        setBoardFen(game.fen());
        setLastMove(uciToLastMove(move.uci));
        if (!move.fast_forward) {
          await sleep(RIVAL_DELAY);
          if (animationTokenRef.current !== token) {
            return;
          }
        }
      }

      if (animationTokenRef.current !== token) {
        return;
      }

      setBoardFen(nextStep.fen);
      setPhase("question");
    },
    [openingId],
  );

  const startSession = useCallback(
    async (nextOpeningId: number) => {
      setPhase("loading");
      setError(null);
      setResumeSession(null);
      setFeedback(null);
      setStep(null);
      setLastMove(null);
      setBoardFen(INITIAL_FEN);

      try {
        const session = await createTrainingSession(nextOpeningId);
        if (!session.step) {
          throw new Error("La sesión no devolvió un paso.");
        }
        window.localStorage.setItem(
          trainingSessionKey(nextOpeningId),
          String(session.id),
        );
        setSessionId(session.id);
        await runStep(session.step);
      } catch (error) {
        setError(getErrorMessage(error));
        setPhase("error");
      }
    },
    [runStep],
  );

  useEffect(() => {
    const loadKey = id ?? "";
    if (startedForRef.current === loadKey) {
      return;
    }
    startedForRef.current = loadKey;

    let cancelled = false;

    const load = async () => {
      if (!id || !Number.isInteger(openingId) || openingId <= 0) {
        setError("La apertura no existe.");
        setPhase("error");
        return;
      }

      setPhase("loading");
      try {
        const openingData = await getOpening(openingId);
        if (cancelled) {
          return;
        }
        setOpening(openingData);

        const key = trainingSessionKey(openingId);
        const stored = window.localStorage.getItem(key);
        if (stored) {
          const storedId = Number(stored);
          if (Number.isInteger(storedId) && storedId > 0) {
            try {
              const session = await getTrainingSession(storedId);
              if (cancelled) {
                return;
              }
              if (session.finished_at === null && session.step) {
                setSessionId(session.id);
                setResumeSession(session);
                setPhase("resume");
                return;
              }
            } catch {
              // La sesión guardada ya no existe: se empieza una nueva.
            }
          }
          window.localStorage.removeItem(key);
        }

        await startSession(openingId);
      } catch (error) {
        if (!cancelled) {
          setError(getErrorMessage(error));
          setPhase("error");
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
      animationTokenRef.current += 1;
    };
  }, [id, openingId, startSession]);

  const submitAnswer = async (
    currentSessionId: number,
    question: TrainingQuestionStep,
    uci: string,
  ) => {
    try {
      const result = await answerTrainingSession(currentSessionId, {
        node_id: question.node_id,
        move: uci,
      });

      if (result.correct) {
        setPhase("correct");
        await sleep(CORRECT_DELAY);
        await runStep(result.next_step);
        return;
      }

      const correctUci = result.correct_move_uci ?? "";
      if (correctUci) {
        const correction = new Chess(question.fen);
        try {
          correction.move(correctUci);
          setBoardFen(correction.fen());
          setLastMove(uciToLastMove(correctUci));
        } catch {
          setBoardFen(question.fen);
          setLastMove(lastMoveFromLeadIn(question));
        }
      } else {
        setBoardFen(question.fen);
        setLastMove(lastMoveFromLeadIn(question));
      }

      setFeedback({
        correctSan: result.correct_move_san ?? "",
        nextStep: result.next_step,
      });
      setPhase("incorrect");
    } catch (error) {
      setBoardFen(question.fen);
      setLastMove(lastMoveFromLeadIn(question));
      setError(getErrorMessage(error));
      setPhase("question");
    }
  };

  const handleMove = (move: BoardMove): boolean => {
    if (
      phase !== "question" ||
      !step ||
      step.kind !== "question" ||
      sessionId === null
    ) {
      return false;
    }

    const question = step;
    const uci =
      typeof move === "string"
        ? move
        : `${move.from}${move.to}${move.promotion ?? ""}`;
    const game = new Chess(question.fen);
    let applied: Move | null = null;
    try {
      applied = game.move(uci);
    } catch {
      applied = null;
    }

    if (!applied) {
      return false;
    }

    setBoardFen(game.fen());
    setLastMove(uciToLastMove(uci));
    setFeedback(null);
    setError(null);
    setPhase("answering");
    void submitAnswer(sessionId, question, uci);
    return true;
  };

  const handleResume = () => {
    if (!resumeSession || !resumeSession.step) {
      return;
    }
    setSessionId(resumeSession.id);
    setResumeSession(null);
    void runStep(resumeSession.step);
  };

  const handleStartOver = () => {
    if (!Number.isInteger(openingId) || openingId <= 0) {
      return;
    }
    setSessionId(null);
    setResumeSession(null);
    void startSession(openingId);
  };

  const handleContinue = () => {
    if (!feedback) {
      return;
    }
    const nextStep = feedback.nextStep;
    setFeedback(null);
    void runStep(nextStep);
  };

  const questionStep = step?.kind === "question" ? step : null;
  const progress = questionStep?.progress ?? null;
  const phaseLabel =
    questionStep?.phase === "traversal"
      ? "Recorrido"
      : questionStep?.phase === "review"
        ? "Repaso"
        : null;
  const progressPercent =
    progress && progress.total > 0
      ? Math.round((progress.answered / progress.total) * 100)
      : 0;
  const orientation = opening?.color === "black" ? "black" : "white";

  if (phase === "error") {
    return (
      <section className="page">
        <div className="page-heading">
          <p className="eyebrow">Entrenamiento</p>
          <h2>No se pudo iniciar el entrenamiento</h2>
          <p>{error}</p>
        </div>
        <div className="state-card state-card--error">
          <div className="form-actions">
            <Link className="button button--ghost" to="/openings">
              Volver
            </Link>
            <button
              type="button"
              className="button"
              onClick={handleStartOver}
            >
              Reintentar
            </button>
          </div>
        </div>
      </section>
    );
  }

  if (phase === "loading") {
    return (
      <section className="page">
        <div className="state-card">
          <p>Preparando entrenamiento...</p>
        </div>
      </section>
    );
  }

  if (phase === "resume" && resumeSession && opening) {
    return (
      <section className="page">
        <div className="page-heading">
          <p className="eyebrow">Entrenamiento</p>
          <h2>{opening.name}</h2>
          <p>Tenés una sesión sin terminar.</p>
        </div>
        <div className="state-card">
          <h3>Reanudar sesión</h3>
          <p>
            Podés continuar donde quedaste o empezar un entrenamiento nuevo.
          </p>
          <div className="form-actions">
            <Link className="button button--ghost" to="/openings">
              Volver
            </Link>
            <button
              type="button"
              className="button button--ghost"
              onClick={handleStartOver}
            >
              Empezar de nuevo
            </button>
            <button type="button" className="button" onClick={handleResume}>
              Reanudar
            </button>
          </div>
        </div>
      </section>
    );
  }

  if (phase === "finished" && step?.kind === "finished" && opening) {
    const summary = step.summary;
    return (
      <section className="page">
        <div className="page-heading">
          <p className="eyebrow">Entrenamiento completado</p>
          <h2>{opening.name}</h2>
          <p>Terminaste todas las posiciones pendientes.</p>
        </div>
        <div className="training-summary">
          <div className="summary-item">
            <span>Preguntas</span>
            <strong>{summary.questions_total}</strong>
          </div>
          <div className="summary-item">
            <span>Aciertos a la primera</span>
            <strong>{summary.first_try_correct}</strong>
          </div>
          <div className="summary-item">
            <span>Porcentaje</span>
            <strong>{summary.accuracy.toFixed(1)}%</strong>
          </div>
        </div>
        <div className="form-actions">
          <Link className="button button--ghost" to="/openings">
            Volver
          </Link>
          <button type="button" className="button" onClick={handleStartOver}>
            Entrenar de nuevo
          </button>
        </div>
      </section>
    );
  }

  if (!opening) {
    return (
      <section className="page">
        <div className="state-card">
          <p>Preparando entrenamiento...</p>
        </div>
      </section>
    );
  }

  return (
    <section className="page training-page">
      <div className="training-layout">
        <div className="training-board">
          <ChessBoardView
            fen={boardFen}
            orientation={orientation}
            disabled={phase !== "question"}
            lastMove={lastMove}
            boardWidth={boardWidth}
            onMove={handleMove}
          />
        </div>

        <aside className="training-sidebar">
          <section className="panel training-info">
            <p className="eyebrow">Entrenamiento</p>
            <h2>{opening.name}</h2>
            <p className="editor-info">{COLOR_LABELS[opening.color]}</p>
            <Link className="button button--ghost" to="/openings">
              Volver
            </Link>
          </section>

          {progress && (
            <section className="panel training-progress">
              <div className="progress-header">
                <span className="phase-pill">{phaseLabel}</span>
                <span>
                  {progress.answered} / {progress.total} respondidas
                </span>
                <span>{progress.pending} pendiente(s)</span>
              </div>
              <div className="progress-bar">
                <div style={{ width: `${progressPercent}%` }} />
              </div>
            </section>
          )}

          {error && (
            <div className="alert" role="alert">
              <p>{error}</p>
              <button type="button" onClick={() => setError(null)}>
                Cerrar
              </button>
            </div>
          )}

          {phase === "correct" && (
            <div className="alert alert--success" role="status">
              <p>¡Correcto!</p>
            </div>
          )}

          {phase === "incorrect" && feedback && (
            <div className="alert" role="alert">
              <p>
                <strong>Incorrecto.</strong> La jugada correcta es{" "}
                <code>{feedback.correctSan}</code>.
              </p>
              <button type="button" onClick={handleContinue}>
                Continuar
              </button>
            </div>
          )}

          <section className="panel">
            <p className="card-label">Estado</p>
            {phase === "animating" && (
              <p className="editor-info">Reproduciendo la línea...</p>
            )}
            {phase === "question" && (
              <p className="editor-info">Realiza tu jugada en el tablero.</p>
            )}
            {phase === "answering" && (
              <p className="editor-info">Comprobando respuesta...</p>
            )}
            {phase === "correct" && (
              <p className="editor-info">Respuesta correcta.</p>
            )}
            {phase === "incorrect" && (
              <p className="editor-info">
                Revisa la jugada correcta y pulsa Continuar.
              </p>
            )}
            {phaseLabel && (
              <p className="editor-info">
                Fase: <strong>{phaseLabel}</strong>
              </p>
            )}
          </section>
        </aside>
      </div>
    </section>
  );
}

export default TrainingPage;