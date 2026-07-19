import type { CategoryScores, EvaluationCategory, InvestmentTerms } from "@sv/contracts/generated";
import { ScoreBadge } from "@sv/ui";
import { categoryLabel, investmentTermsText } from "../lib/format";
import { categories, companyPath } from "../lib/routes";

export function DashboardNav({ slug, active, scores, overallScore, investment, onNavigate }: { slug: string; active: EvaluationCategory; scores: CategoryScores; overallScore: number | null; investment: Pick<InvestmentTerms, "amount" | "currency" | "equityPercentage">; onNavigate?: (category: EvaluationCategory) => void }) {
  const terms = investmentTermsText(investment);
  return <nav className="dashboard-nav" aria-label="Evaluation categories">
    <div className="dashboard-nav__links">{categories.map((category) => <a key={category} href={companyPath(slug, category)} onClick={(event) => { if (onNavigate) { event.preventDefault(); onNavigate(category); } }} aria-current={active === category ? "page" : undefined} className={`dashboard-nav__card${active === category ? " is-active" : ""}`}><span className="dashboard-nav__card-title">{categoryLabel(category)}</span><span className="dashboard-nav__card-meta">{category === "home" ? "Overview" : <>Score <strong className="nav-score">{scores[category] ?? "—"}</strong></>}</span></a>)}</div>
    <div className="dashboard-nav__metadata"><span className="dashboard-nav__terms" aria-label={`Investment terms: ${terms}`}><span className="dashboard-nav__terms-label">Terms</span><strong>{terms}</strong></span><div className="dashboard-nav__overall" aria-label={`Overall score: ${overallScore ?? "unavailable"}`}><ScoreBadge label="Overall" score={overallScore} /></div></div>
  </nav>;
}
