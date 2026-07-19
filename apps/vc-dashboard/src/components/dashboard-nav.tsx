import type { CategoryScores, EvaluationCategory } from "@sv/contracts/generated";
import { ScoreBadge } from "@sv/ui";
import { categoryLabel } from "../lib/format";
import { categories, companyPath } from "../lib/routes";

export function DashboardNav({ slug, active, scores, overallScore, onNavigate }: { slug: string; active: EvaluationCategory; scores: CategoryScores; overallScore: number | null; onNavigate?: (category: EvaluationCategory) => void }) {
  return <nav className="dashboard-nav" aria-label="Evaluation categories"><div className="dashboard-nav__links">{categories.map((category) => <a key={category} href={companyPath(slug, category)} onClick={(event) => { if (onNavigate) { event.preventDefault(); onNavigate(category); } }} aria-current={active === category ? "page" : undefined} className={active === category ? "is-active" : ""}>{categoryLabel(category)}{category !== "home" && <span className="nav-score">{scores[category] ?? "—"}</span>}</a>)}</div><div className="dashboard-nav__overall" aria-label={`Overall score: ${overallScore ?? "unavailable"}`}><ScoreBadge label="Score" score={overallScore} /></div></nav>;
}
