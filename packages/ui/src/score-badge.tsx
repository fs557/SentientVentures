import type { ReactNode } from "react";

function scoreTone(score: number | null): string {
  if (score === null) return "unavailable";
  if (score < 40) return "critical";
  if (score < 60) return "caution";
  if (score < 75) return "mixed";
  if (score < 90) return "strong";
  return "exceptional";
}

export function ScoreBadge({ score, label = "Score" }: { score: number | null; label?: string }): ReactNode {
  const tone = scoreTone(score);
  const progress = score === null ? 0 : Math.min(100, Math.max(0, score));
  return (
    <span className={`sv-score-badge sv-score-badge--${tone}`} aria-label={`${label}: ${score ?? "unavailable"}`}>
      <span className="sv-score-badge__value">
        <span className="sv-score-badge__label">{label}</span>
        <strong>{score ?? "—"}</strong>
      </span>
      <span className="sv-score-badge__track" aria-hidden="true">
        <span className="sv-score-badge__fill" style={{ width: `${progress}%` }} />
      </span>
    </span>
  );
}
