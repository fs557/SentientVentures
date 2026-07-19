import type { ReactNode } from "react";

export function ScoreBadge({ score, label = "Score" }: { score: number | null; label?: string }): ReactNode {
  return (
    <span className={`sv-score-badge${score === null ? " sv-score-badge--unavailable" : ""}`} aria-label={`${label}: ${score ?? "unavailable"}`}>
      <span className="sv-score-badge__label">{label}</span>
      <strong>{score ?? "—"}</strong>
    </span>
  );
}
