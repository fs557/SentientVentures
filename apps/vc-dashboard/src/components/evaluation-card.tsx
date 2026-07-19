import type { EvaluationItem } from "@sv/contracts/generated";
import { ScoreBadge } from "@sv/ui";

function EvidenceList({ title, entries }: { title: string; entries: EvaluationItem["evidence"] }) {
  return <section className="evidence"><h4>{title}</h4><ul>{entries.map((entry, index) => <li key={`${entry.documentId}-${index}`}><span className="evidence__source">{entry.kind} · {entry.documentId}{entry.page ? ` · p. ${entry.page}` : ""}{entry.section ? ` · ${entry.section}` : ""}</span>{entry.text}</li>)}</ul></section>;
}
export function EvaluationCard({ item }: { item: EvaluationItem }) {
  return <details className="evaluation-card" aria-labelledby={`${item.id}-title`}>
    <summary className="evaluation-card__summary">
      <header><p className="eyebrow">Criterion</p><h3 id={`${item.id}-title`}>{item.title}</h3></header>
      <div className="evaluation-card__score" role="group" aria-label={`Criterion score: ${item.score ?? "unavailable"}`}><ScoreBadge score={item.score} />{item.confidence !== null && <p className="confidence">Confidence <strong>{item.confidence}/100</strong></p>}<span className="evaluation-card__indicator" aria-hidden="true" /></div>
    </summary>
    <div className="evaluation-card__content">
      <section><h4>Assessment</h4><p>{item.assessment}</p></section>
      <div className="argument-grid"><section><h4>Positive arguments</h4><ul>{item.positiveArguments.map((text, index) => <li key={index}>{text}</li>)}</ul></section><section><h4>Negative arguments and risks</h4><ul>{item.negativeArguments.map((text, index) => <li key={index}>{text}</li>)}</ul></section></div>
      <EvidenceList title="Evidence" entries={item.evidence} />
      {item.missingInformation.length > 0 && <section><h4>Missing information</h4><ul>{item.missingInformation.map((text, index) => <li key={index}>{text}</li>)}</ul></section>}
      <EvidenceList title="Source references" entries={item.sourceReferences} />
      {item.validationErrors.length > 0 && <section className="validation-errors"><h4>Data notes</h4><ul>{item.validationErrors.map((error, index) => <li key={index}>{error.message}</li>)}</ul></section>}
    </div>
  </details>;
}
