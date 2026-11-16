import { useState } from "react";

interface AccuracyPoint {
  label: string;
  value: number;
}

interface AccuracyChartProps {
  title: string;
  description?: string;
  points: AccuracyPoint[];
}

const WIDTH = 640;
const HEIGHT = 240;
const MARGIN = { top: 16, right: 18, bottom: 34, left: 44 };
const GRID = [0, 25, 50, 75, 100];

function clamp(value: number): number {
  return Math.min(100, Math.max(0, value));
}

function AccuracyChart({
  title,
  description,
  points,
}: AccuracyChartProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const plotWidth = WIDTH - MARGIN.left - MARGIN.right;
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
  const x = (index: number) =>
    points.length <= 1
      ? MARGIN.left + plotWidth / 2
      : MARGIN.left + (index / (points.length - 1)) * plotWidth;
  const y = (value: number) =>
    MARGIN.top + (1 - clamp(value) / 100) * plotHeight;
  const path =
    points.length > 1
      ? points
          .map(
            (point, index) =>
              `${index === 0 ? "M" : "L"} ${x(index)} ${y(point.value)}`,
          )
          .join(" ")
      : "";
  const labelStep = Math.max(1, Math.ceil(points.length / 6));
  const activePoint =
    activeIndex !== null ? points[activeIndex] ?? null : null;
  const activeX = activeIndex !== null ? x(activeIndex) : 0;
  const activeY = activePoint ? y(activePoint.value) : 0;
  const tooltipLeft = Math.min(
    94,
    Math.max(6, (activeX / WIDTH) * 100),
  );
  const tooltipTop = (activeY / HEIGHT) * 100;
  const tooltipBelow = tooltipTop < 24;

  const bandBounds = (index: number) => {
    if (points.length <= 1) {
      return {
        left: MARGIN.left,
        right: WIDTH - MARGIN.right,
      };
    }
    const spacing = plotWidth / (points.length - 1);
    return {
      left: index === 0 ? MARGIN.left : x(index) - spacing / 2,
      right:
        index === points.length - 1
          ? WIDTH - MARGIN.right
          : x(index) + spacing / 2,
    };
  };

  return (
    <article className="stats-chart-card">
      <div className="stats-chart-heading">
        <h4>{title}</h4>
        {description && <p>{description}</p>}
      </div>

      {points.length === 0 ? (
        <p className="state-message">Sin entrenamientos completos.</p>
      ) : (
        <div className="accuracy-chart-wrapper">
          <svg
            className="accuracy-chart"
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            role="img"
            aria-label={title}
            onMouseLeave={() => setActiveIndex(null)}
          >
            {GRID.map((level) => (
              <g key={level}>
                <line
                  x1={MARGIN.left}
                  x2={WIDTH - MARGIN.right}
                  y1={y(level)}
                  y2={y(level)}
                  className="accuracy-chart__grid"
                />
                <text
                  x={MARGIN.left - 8}
                  y={y(level) + 4}
                  textAnchor="end"
                  className="accuracy-chart__axis-label"
                >
                  {level}%
                </text>
              </g>
            ))}

            {path && (
              <path d={path} className="accuracy-chart__line" />
            )}

            {activePoint && (
              <line
                x1={activeX}
                x2={activeX}
                y1={activeY}
                y2={HEIGHT - MARGIN.bottom}
                className="accuracy-chart__guide"
              />
            )}

            {points.map((point, index) => {
              const pointX = x(index);
              const pointY = y(point.value);
              const band = bandBounds(index);
              const isActive = activeIndex === index;
              return (
                <g
                  key={`${point.label}-${index}`}
                  className="accuracy-chart__point-group"
                  tabIndex={0}
                  role="img"
                  aria-label={`${point.label}: ${point.value.toFixed(1)}%`}
                  onMouseEnter={() => setActiveIndex(index)}
                  onFocus={() => setActiveIndex(index)}
                  onBlur={() =>
                    setActiveIndex((current) =>
                      current === index ? null : current,
                    )
                  }
                >
                  <rect
                    x={band.left}
                    y={MARGIN.top}
                    width={band.right - band.left}
                    height={plotHeight}
                    className="accuracy-chart__hover-band"
                  />
                  <circle
                    cx={pointX}
                    cy={pointY}
                    r={isActive ? 6 : 4.5}
                    className={`accuracy-chart__point${
                      isActive ? " accuracy-chart__point--active" : ""
                    }`}
                  />
                  {(index % labelStep === 0 ||
                    index === points.length - 1) && (
                    <text
                      x={pointX}
                      y={HEIGHT - 10}
                      textAnchor="middle"
                      className="accuracy-chart__x-label"
                    >
                      {point.label}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

          {activePoint && (
            <div
              className={`accuracy-chart__tooltip${
                tooltipBelow
                  ? " accuracy-chart__tooltip--below"
                  : ""
              }`}
              style={{ left: `${tooltipLeft}%`, top: `${tooltipTop}%` }}
              role="tooltip"
            >
              <span>{activePoint.label}</span>
              <strong>{activePoint.value.toFixed(1)}%</strong>
            </div>
          )}
        </div>
      )}
    </article>
  );
}

export default AccuracyChart;
