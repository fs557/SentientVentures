import type { CompanyEvaluation, EvaluationItem } from "@sv/contracts/generated";
import { ScoreBadge } from "@sv/ui";
import { moneyText } from "../lib/format";
import { EvaluationCard } from "./evaluation-card";

function readItem(items: EvaluationItem[], id: string) { return items.find((item) => item.id === id)?.assessment ?? "Not provided"; }
export function HomeOverview({ evaluation }: { evaluation: CompanyEvaluation }) {
  const home = evaluation.categories.home;
  if (!home) return <section className="missing-category" role="alert"><h2>Home evaluation unavailable</h2><p>The API returned no Home document for this ready company.</p></section>;
  const { investment } = evaluation;
  const allItems = Object.values(evaluation.categories).flatMap((document) => document?.items ?? []);
  const argumentsFor = allItems.flatMap((item) => item.positiveArguments.map((text) => ({ id: item.id, text }))).slice(0, 4);
  const risks = allItems.flatMap((item) => item.negativeArguments.map((text) => ({ id: item.id, text }))).slice(0, 4);
  const missing = allItems.flatMap((item) => item.missingInformation.map((text) => ({ id: item.id, text }))).slice(0, 4);
  return <>
    <section className="home-brief" aria-labelledby="overview-title"><div><p className="eyebrow">Company overview</p><h1 id="overview-title">{evaluation.company}</h1><p>{readItem(home.items, "home.company_idea")}</p></div><div className="home-score"><ScoreBadge label="Overall score" score={evaluation.overallScore} /></div></section>
    <section className="summary-grid" aria-label="Company summary"><article><h2>Investment terms</h2><dl><div><dt>Requested investment</dt><dd>{moneyText(investment.amount, investment.currency)}</dd></div><div><dt>Equity offered</dt><dd>{investment.equityPercentage === null ? "Not provided" : `${investment.equityPercentage}%`}</dd></div><div><dt>Pre-money valuation</dt><dd>{moneyText(investment.preMoneyValuation, investment.currency)}</dd></div><div><dt>Use of funds</dt><dd>{investment.useOfFunds.length ? investment.useOfFunds.join(", ") : "Not provided"}</dd></div></dl></article><article><h2>Score overview</h2><dl>{(["idea", "market", "financial", "management"] as const).map((category) => <div key={category}><dt>{category[0].toUpperCase() + category.slice(1)}</dt><dd>{evaluation.categoryScores[category] ?? "Unavailable"}</dd></div>)}</dl></article><article><h2>Founder overview</h2><p>{readItem(home.items, "home.founders")}</p></article></section>
    <section className="signals" aria-label="Investment signals"><article><h2>Investment arguments</h2><ul>{argumentsFor.length ? argumentsFor.map((entry, index) => <li key={`${entry.id}-${index}`}><span>{entry.id}</span>{entry.text}</li>) : <li>Not provided</li>}</ul></article><article><h2>Key risks</h2><ul>{risks.length ? risks.map((entry, index) => <li key={`${entry.id}-${index}`}><span>{entry.id}</span>{entry.text}</li>) : <li>Not provided</li>}</ul></article><article><h2>Missing information</h2><ul>{missing.length ? missing.map((entry, index) => <li key={`${entry.id}-${index}`}><span>{entry.id}</span>{entry.text}</li>) : <li>Not provided</li>}</ul></article></section>
    <section className="section-heading"><p className="eyebrow">Evidence-led review</p><h2>Company record</h2><p>All submitted Home criteria are shown below. Unavailable source values are identified in the evaluation.</p></section>
    <div className="cards">{home.items.map((item) => <EvaluationCard key={item.id} item={item} />)}</div>
  </>;
}
