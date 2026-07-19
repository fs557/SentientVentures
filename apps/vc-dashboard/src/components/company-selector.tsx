import type { CompanySummary } from "@sv/contracts/generated";
import { dateText, scoreText } from "../lib/format";

export function CompanySelector({ companies, selectedSlug, onSelect, disabled }: { companies: CompanySummary[]; selectedSlug: string | null; onSelect: (slug: string) => void; disabled?: boolean }) {
  return <label className="company-selector"><span>Company under review</span><select value={selectedSlug ?? ""} onChange={(event) => onSelect(event.target.value)} disabled={disabled} aria-label="Company under review">
    {companies.map((company) => <option key={company.slug} value={company.slug}>{company.company} · Score {scoreText(company.overallScore)}{company.stage ? ` · ${company.stage}` : ""} · {dateText(company.submissionDate)}</option>)}
  </select></label>;
}
