import type { EvaluationItem } from "@sv/contracts/generated";
import { ScoreBadge } from "@sv/ui";
import { displayText } from "../lib/format";

function EvidenceNotes({ entries }: { entries: EvaluationItem["evidence"] }) {
  return <section className="evidence"><h4>Evidence notes</h4><ul>{entries.map((entry, index) => <li key={`${entry.documentId}-${index}`}>{displayText(entry.text)}</li>)}</ul></section>;
}
export function EvaluationCard({ item, variant = "criterion" }: { item: EvaluationItem; variant?: "criterion" | "fact" }) {
  const isFact = variant === "fact";
  return <details className={`evaluation-card evaluation-card--${variant}`} aria-labelledby={`${item.id}-title`}>
    <summary className="evaluation-card__summary">
      <header>{!isFact && <p className="eyebrow">Criterion</p>}<h3 id={`${item.id}-title`}>{item.title}</h3></header>
      {isFact
        ? <span className="evaluation-card__indicator" aria-hidden="true" />
        : <div className="evaluation-card__score" role="group" aria-label={`Criterion score: ${item.score ?? "unavailable"}`}><ScoreBadge score={item.score} />{item.confidence !== null && <p className="confidence">Confidence <strong>{item.confidence}/100</strong></p>}<span className="evaluation-card__indicator" aria-hidden="true" /></div>}
    </summary>
    <div className="evaluation-card__content">
      <section>{!isFact && <h4>Assessment</h4>}<p>{displayText(item.assessment)}</p></section>
      {!isFact && <div className="argument-grid"><section><h4>Positive arguments</h4><ul>{item.positiveArguments.map((text, index) => <li key={index}>{displayText(text)}</li>)}</ul></section><section><h4>Negative arguments and risks</h4><ul>{item.negativeArguments.map((text, index) => <li key={index}>{displayText(text)}</li>)}</ul></section></div>}
      {!isFact && <EvidenceNotes entries={item.evidence} />}
      {item.missingInformation.length > 0 && <section><h4>Missing information</h4><ul>{item.missingInformation.map((text, index) => <li key={index}>{displayText(text)}</li>)}</ul></section>}
      {item.validationErrors.length > 0 && <section className="validation-errors"><h4>Data notes</h4><ul>{item.validationErrors.map((error, index) => <li key={index}>{displayText(error.message)}</li>)}</ul></section>}
    </div>
  </details>;
}
