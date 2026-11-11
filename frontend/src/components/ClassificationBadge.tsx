import type { CSSProperties } from "react";

import {
  getClassification,
  type ClassificationKey,
} from "../types/classifications";

interface ClassificationBadgeProps {
  classification: ClassificationKey | string | null;
  size?: "sm" | "md" | "lg" | "fill";
}

function hexToRgb(hex: string): [number, number, number] | null {
  const normalized = hex.replace("#", "");
  if (!/^[0-9a-fA-F]{6}$/.test(normalized)) {
    return null;
  }
  return [
    Number.parseInt(normalized.slice(0, 2), 16),
    Number.parseInt(normalized.slice(2, 4), 16),
    Number.parseInt(normalized.slice(4, 6), 16),
  ];
}

function contrastColor(hex: string): string {
  const rgb = hexToRgb(hex);
  if (!rgb) {
    return "#ffffff";
  }
  const [red, green, blue] = rgb.map((channel) => {
    const value = channel / 255;
    return value <= 0.03928
      ? value / 12.92
      : ((value + 0.055) / 1.055) ** 2.4;
  });
  const luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue;
  return luminance > 0.55 ? "#16211b" : "#ffffff";
}

function ClassificationBadge({
  classification,
  size = "md",
}: ClassificationBadgeProps) {
  const definition = getClassification(classification);
  if (!definition) {
    return null;
  }

  const style: CSSProperties = {
    backgroundColor: definition.color,
    color: contrastColor(definition.color),
  };

  return (
    <span
      className={`classification-badge classification-badge--${size}`}
      style={style}
      title={definition.label}
      aria-label={definition.label}
      role="img"
    >
      {definition.symbol}
    </span>
  );
}

export default ClassificationBadge;