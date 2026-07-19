import type { CategoryScores, EvaluationCategory, InvestmentTerms } from "@sv/contracts/generated";
import { ScoreBadge } from "@sv/ui";
import { categoryLabel, investmentTermsText } from "../lib/format";
import { categories, companyPath } from "../lib/routes";

export function DashboardNav({ slug, active, scores, overallScore, investment, onNavigate }: { slug: string; active: EvaluationCategory; scores: CategoryScores; overallScore: number | null; investment: Pick<InvestmentTerms, "amount" | "currency" | "equityPercentage">; onNavigate?: (category: EvaluationCategory) => void }) {
  const terms = investmentTermsText(investment);
  return <nav className="dashboard-nav" aria-label="Evaluation categories"><div className="dashboard-nav__links">{categories.map((category) => <a key={category} href={companyPath(slug, category)} onClick={(event) => { if (onNavigate) { event.preventDefault(); onNavigate(category); } }} aria-current={active === category ? "page" : undefined} className={active === category ? "is-active" : ""}>{categoryLabel(category)}{category !== "home" && <span className="nav-score">{scores[category] ?? "—"}</span>}</a>)}</div><div className="dashboard-nav__metadata"><span className="dashboard-nav__terms" aria-label={`Investment terms: ${terms}`}><span className="dashboard-nav__terms-label">Terms</span>{terms}</span><div className="dashboard-nav__overall" aria-label={`Overall score: ${overallScore ?? "unavailable"}`}><ScoreBadge label="Score" score={overallScore} /></div></div></nav>;
}
