#!/usr/bin/env python3
"""Generate deterministic, fictional v1 evaluation fixture companies from source facts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from src.core.markdown import EvidenceReference, EvaluationDocument, EvaluationItem
from src.core.registry import CATEGORIES, entries_for_category
from src.core.scoring import PORTFOLIO_UNAVAILABLE_IDS, category_scores, overall_score
from src.core.storage import CompanyRef, atomic_write_json, write_evaluation_set


# Each frozen registry ID has its own deterministic analytical lens and caveat.
# The company facts below provide the concrete subject; this table keeps the
# evaluation source maintainable without hand-editing derived Markdown files.
CRITERION_CONTEXT: dict[str, tuple[str, str]] = {
    "home.company_name": ("The submitted identity is {company}.", "The fixture does not model incorporation records."),
    "home.current_valuation": ("The proposed {currency} {postMoneyValuation:,.0f} post-money valuation is explicit.", "The valuation has not been independently benchmarked."),
    "home.company_idea": ("The core idea is {theme}.", "The thesis still depends on execution outside the pitch."),
    "home.sector": ("The company operates in {sector}.", "Sector labels alone do not prove buyer urgency."),
    "home.what_company_does": ("It sells {product} to {customer}.", "The exact implementation scope can expand during delivery."),
    "home.use_of_investment": ("The round funds {useOfFundsText}.", "Allocation discipline must be demonstrated after financing."),
    "home.equity_offered": ("The proposed dilution is {equityPercentage:g}%.", "The cap-table context is not independently verified."),
    "home.investment_requested": ("The requested amount is {currency} {amount:,.0f}.", "The amount should be tested against milestone costs."),
    "home.implied_valuation": ("The terms imply {currency} {impliedValuation:,.0f}, matching the stated post-money value.", "The implied value is arithmetic, not market validation."),
    "home.founders": ("The founding team is {founders}.", "Key-person concentration remains relevant."),
    "home.founder_facts": ("Relevant founder facts include {founderFacts}.", "References and employment history are not independently verified."),
    "home.company_facts": ("Material company facts are {companyFacts}.", "These are fictional pitch claims rather than audited disclosures."),
    "home.missing_information": ("The review should next obtain {nextEvidence}.", "Those gaps limit diligence depth but do not replace the assessment."),
    "idea.uniqueness": ("The differentiated element is {differentiator}.", "Adjacent teams can pursue similar workflows."),
    "idea.copyability": ("Copying requires {copyBarrier}.", "A well-funded competitor could replicate visible product features."),
    "idea.defensibility": ("Defensibility can compound through {defensibility}.", "The moat is still being earned rather than proven."),
    "idea.protectability": ("Protectable value is concentrated in {protectability}.", "No granted IP is represented in this fixture."),
    "idea.technical_execution_complexity": ("Technical delivery requires {technicalComplexity}.", "Integration failures could delay commercial readiness."),
    "idea.operational_execution_complexity": ("Operations require {operationalComplexity}.", "Field execution can become a bottleneck."),
    "idea.goal_effort": ("The stated milestone is {goal}, requiring a focused build-and-sell cycle.", "The schedule must absorb customer feedback."),
    "idea.sustainability": ("The sustainability case is {sustainability}.", "Impact should be measured rather than assumed."),
    "idea.fundamental_problems": ("The central structural challenge is {fundamentalProblem}.", "Failure to solve it would weaken the model."),
    "idea.problem_solution_clarity": ("The problem-solution link is {problemSolution}.", "Buyer validation still matters more than narrative clarity."),
    "idea.value_proposition": ("The value proposition is {valueProposition}.", "Customers must confirm that the benefit justifies switching."),
    "idea.product_maturity": ("Product maturity is {productMaturity}.", "The product has remaining proof points before scale."),
    "market.addressable_market": ("The addressable market is framed as {marketSize}.", "The bottom-up opportunity is not independently modelled."),
    "market.market_size_reliability": ("The market estimate is {marketReliability}.", "Market-size claims should be reconciled to customer counts."),
    "market.sector_trend": ("The sector trend is {sectorTrend}.", "Trend momentum can reverse with budgets or regulation."),
    "market.expected_growth": ("Expected growth rests on {growthDriver}.", "The forecast is sensitive to adoption pace."),
    "market.entry_timing": ("Entry timing is {entryTiming}.", "Timing advantages shrink if incumbents respond quickly."),
    "market.competition": ("Competitive pressure comes from {competition}.", "Competitors may bundle comparable capabilities."),
    "market.entry_barriers": ("Entry barriers include {entryBarriers}.", "Barriers are lower before customer-specific learning accumulates."),
    "market.customer_adoption": ("Customer adoption requires {adoptionPath}.", "Procurement and behavior change can slow conversion."),
    "market.market_problems": ("The market friction is {marketProblem}.", "That friction can constrain growth even when demand exists."),
    "market.portfolio_fit": ("Portfolio fit is intentionally unscored because the frozen contract provides no VC portfolio holdings or mandate context.", "A fit conclusion would require the investor's current portfolio and strategy."),
    "market.portfolio_synergies": ("Portfolio synergies are intentionally unscored because no portfolio-company capabilities, customer overlaps, or ownership constraints are supplied.", "Any synergy claim would be speculative without that portfolio context."),
    "market.target_customer_clarity": ("The initial customer is {customer}.", "The buying committee may be broader than the user profile."),
    "market.gtm_plausibility": ("The go-to-market plan is {gtm}.", "Repeatability is not yet established."),
    "market.customer_concentration": ("Likely concentration is {concentration}.", "Early dependence on a few accounts can affect pricing power."),
    "market.regulatory_barriers": ("Regulatory exposure is {regulation}.", "Requirements can vary by customer and geography."),
    "financial.current_revenue": ("Current revenue is {currentRevenue}.", "Revenue recognition has not been audited."),
    "financial.current_profit_loss": ("Current profitability is {currentProfitLoss}.", "The loss profile may change with hiring and deployment."),
    "financial.projected_revenue": ("The revenue projection is {projectedRevenue}.", "Projection conversion assumptions remain unverified."),
    "financial.projected_profit": ("The profit outlook is {projectedProfit}.", "Margin improvement depends on operating leverage."),
    "financial.projection_plausibility": ("Projection plausibility is {projectionPlausibility}.", "The model needs evidence from actual cohorts."),
    "financial.customer_acquisition_cost": ("Customer acquisition cost is {cac}.", "Sales-cycle length can materially change CAC."),
    "financial.recurring_customer_rate": ("Recurring customer rate is {recurringRate}.", "The measure needs a stable definition and cohort period."),
    "financial.customer_retention_rate": ("Customer retention is {retentionRate}.", "Renewals cannot yet be assumed from limited history."),
    "financial.revenue_per_employee": ("Revenue per employee is {revenuePerEmployee}.", "Product and field staffing may change productivity."),
    "financial.profit_per_employee": ("Profit per employee is {profitPerEmployee}.", "This measure is immature while the company invests ahead of revenue."),
    "financial.burn_rate": ("Current burn is {burnRate}.", "Burn may rise before the financed milestone is reached."),
    "financial.runway": ("Available runway is {runway}.", "A delayed raise or sales cycle would compress that runway."),
    "financial.funding_requirement_plausibility": ("The funding request is {fundingPlausibility}.", "Milestone budgeting should be validated line by line."),
    "financial.capital_allocation": ("Capital allocation prioritizes {useOfFundsText}.", "Spend sequencing must preserve the highest-risk validation work."),
    "financial.exit_strategy": ("The exit path is {exitStrategy}.", "Exit timing and buyer appetite are not controllable."),
    "financial.inconsistencies": ("Known financial consistency issue: {inconsistency}.", "Diligence should reconcile the underlying operating assumptions."),
    "financial.risks": ("The principal financial risk is {financialRisk}.", "The downside case needs explicit cash and pricing sensitivity."),
    "financial.document_completeness_reliability": ("Financial document quality is {documentQuality}.", "The fixture is intentionally not a substitute for audited records."),
    "financial.forecast_drivers": ("The main forecast drivers are {forecastDrivers}.", "Small changes in those drivers can materially affect outcomes."),
    "management.academic_background": ("Academic background is {academicBackground}.", "Credentials do not by themselves prove operating execution."),
    "management.professional_background": ("Professional background is {professionalBackground}.", "Prior roles should be reference-checked."),
    "management.domain_expertise": ("Domain expertise is {domainExpertise}.", "The team still needs ongoing customer learning."),
    "management.technical_expertise": ("Technical expertise is {technicalExpertise}.", "Technical depth must translate into reliable delivery."),
    "management.commercial_expertise": ("Commercial expertise is {commercialExpertise}.", "Enterprise sales capability may need reinforcement."),
    "management.founder_market_fit": ("Founder-market fit is {founderMarketFit}.", "The fit should be tested through sustained customer access."),
    "management.professional_following": ("Professional influence is {professionalFollowing}.", "Audience reach is not a proxy for purchase intent."),
    "management.controversies": ("The fixture reports {controversies}.", "Background checks remain part of real diligence."),
    "management.creativity": ("Team creativity appears in {creativity}.", "Novel approaches need disciplined prioritization."),
    "management.strengths": ("Core team strengths are {teamStrengths}.", "Strengths must be maintained as the organization grows."),
    "management.weaknesses": ("Current weaknesses are {teamWeaknesses}.", "Unaddressed gaps can slow execution."),
    "management.missing_roles": ("The key role gap is {missingRoles}.", "Hiring timing and quality are material risks."),
    "management.execution_ability": ("Execution evidence is {executionAbility}.", "Future execution includes challenges not yet encountered."),
    "management.credibility": ("Credibility rests on {credibility}.", "Claims should be verified with customers and references."),
    "management.team_balance": ("Team balance is {teamBalance}.", "The balance can change as commercial demands grow."),
    "management.prior_execution": ("Prior execution evidence is {priorExecution}.", "Past success reduces but does not remove venture risk."),
}

# Directly stated identities, terms, and operating values cite the fictional
# source as facts. The remaining criterion-specific judgments are inferences.
FACT_EVIDENCE_IDS = frozenset({
    "home.company_name", "home.current_valuation", "home.company_idea", "home.sector",
    "home.what_company_does", "home.use_of_investment", "home.equity_offered",
    "home.investment_requested", "home.implied_valuation", "home.founders",
    "home.founder_facts", "home.company_facts", "market.target_customer_clarity",
    "financial.current_revenue", "financial.current_profit_loss", "financial.projected_revenue",
    "financial.projected_profit", "financial.burn_rate", "financial.runway",
    "management.academic_background", "management.professional_background",
    "management.domain_expertise", "management.technical_expertise",
    "management.commercial_expertise", "management.professional_following",
    "management.controversies",
})


def _load_facts(path: Path) -> list[dict[str, Any]]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    companies = parsed.get("companies")
    if not isinstance(companies, list) or len(companies) != 2:
        raise ValueError("Fixture facts must define exactly two companies")
    return companies


def _score(facts: dict[str, Any], category: str, order: int, item_id: str) -> int | None:
    if item_id in PORTFOLIO_UNAVAILABLE_IDS:
        return None
    # The calculation is deterministic and deliberately produces imperfect variation.
    category_offset = {"idea": 1, "market": -2, "financial": 0, "management": 2}.get(category, 0)
    return max(1, min(100, int(facts["scoreBase"]) + category_offset + ((order * 7) % 9) - 4))


def _document(facts: dict[str, Any], category: str) -> EvaluationDocument:
    source = str(facts["documentId"])
    investment = facts["investment"]
    if not isinstance(investment, dict):
        raise ValueError("Fixture facts investment terms must be an object")
    formatting_facts = {
        **facts,
        **investment,
        "useOfFundsText": ", ".join(str(item) for item in investment["useOfFunds"]),
    }
    items: list[EvaluationItem] = []
    for entry in entries_for_category(category):
        unavailable = entry.id in PORTFOLIO_UNAVAILABLE_IDS
        score = None if category == "home" else _score(facts, category, entry.display_order, entry.id)
        context, caveat = CRITERION_CONTEXT[entry.id]
        assessment = context.format(**formatting_facts)
        evidence_kind = "fact" if entry.id in FACT_EVIDENCE_IDS else "inference"
        if unavailable:
            score = None
        items.append(EvaluationItem(
            id=entry.id, category=category, title=entry.title, score=score,
            confidence=None if unavailable else max(1, min(100, int(facts["scoreBase"]) + 5)),
            assessment=assessment,
            positive_arguments=[f"{entry.title} is supported by the fictional fact pattern: {assessment}"],
            negative_arguments=[caveat],
            evidence=[EvidenceReference(evidence_kind, source, f"{entry.id}: {assessment}", page=1, section=entry.id)],
            missing_information=[],
            source_references=[EvidenceReference(evidence_kind, source, f"Structured {evidence_kind} for {entry.id}", page=1, section=entry.id)],
        ))
    return EvaluationDocument(1, 1, str(facts["company"]), str(facts["slug"]), category, str(facts["generatedAt"]), [source], items)


def _metadata(facts: dict[str, Any], documents: dict[str, EvaluationDocument]) -> dict[str, object]:
    scores = category_scores({category: document.items for category, document in documents.items()})
    return {
        "company_id": facts["companyId"], "slug": facts["slug"], "display_name": facts["company"], "stage": facts["stage"],
        "created_at": facts["generatedAt"], "state": "ready", "schema_version": 1, "registry_version": 1,
        "submission": {"founder_name": "Fictional Founder", "founder_email": "fictional@example.invalid"},
        "source_documents": [{"id": facts["documentId"], "role": "pitch_deck", "original_name": "fictional-pitch.pdf", "stored_name": "fixture-facts.json", "media_type": "application/pdf", "size_bytes": 0, "sha256": "0" * 64, "uploaded_at": facts["generatedAt"]}],
        "category_scores": scores, "overall_score": overall_score(scores), "validation_errors": [],
        "investment": facts["investment"],
    }


def generate(destination: Path, facts_path: Path) -> dict[str, str]:
    destination.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for facts in _load_facts(facts_path):
        slug = str(facts["slug"])
        company_root = destination / slug
        if company_root.exists():
            shutil.rmtree(company_root)
        reference = CompanyRef.from_root(destination, slug)
        documents = {category: _document(facts, category) for category in CATEGORIES}
        write_evaluation_set(reference, documents)
        atomic_write_json(reference, "extracted/company-facts.json", facts)
        atomic_write_json(reference, "extracted/document-index.json", {"documents": [{"id": facts["documentId"], "kind": "pitch_deck"}]})
        atomic_write_json(reference, "metadata.json", _metadata(facts, documents))
        for path in sorted(company_root.rglob("*")):
            if path.is_file(): hashes[str(path.relative_to(destination))] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"generator": "v1", "files": dict(sorted(hashes.items()))}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return hashes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "tests/fixtures/companies")
    parser.add_argument("--facts", type=Path, default=ROOT / "tests/fixtures/example-company-facts.json")
    args = parser.parse_args()
    generate(args.output, args.facts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
