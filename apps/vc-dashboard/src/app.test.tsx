import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { CompanyEvaluation, CompanySummary } from "@sv/contracts/generated";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardApp } from "./app";

const aether: CompanySummary = { slug: "aether", company: "Aether Robotics", stage: "Seed", submissionDate: "2026-07-19T12:00:00Z", overallScore: 82, categoryScores: { home: null, idea: 83, market: 80, financial: 82, management: 84 } };
const harbor: CompanySummary = { slug: "harbor", company: "Harborloop", stage: "Pre-seed", submissionDate: "2026-07-18T12:00:00Z", overallScore: 68, categoryScores: { home: null, idea: 71, market: null, financial: 65, management: 68 } };
function evaluation(summary: CompanySummary, portfolioScore: number | null = null): CompanyEvaluation {
  const item = (id: string, title: string, score: number | null) => ({ id, category: id.split(".")[0] as "home" | "idea" | "market" | "financial" | "management", title, score, confidence: 80, assessment: `${summary.company} assessment.`, positiveArguments: ["Supported positive."], negativeArguments: ["Known risk."], evidence: [{ kind: "fact" as const, documentId: "submission", text: "Submitted source." }], missingInformation: score === null ? ["Portfolio data was not provided."] : [], sourceReferences: [{ kind: "fact" as const, documentId: "submission", text: "Submitted source." }], validationErrors: [] });
  const doc = (category: "home" | "idea" | "market" | "financial" | "management", items: ReturnType<typeof item>[]) => ({ schemaVersion: 1 as const, registryVersion: 1 as const, company: summary.company, slug: summary.slug, category, generatedAt: summary.submissionDate, sourceDocuments: [], items, validationErrors: [] });
  const diligenceItem = { ...item("home.missing_information", "What important information is missing?", null), assessment: "Obtain signed contracts, deployment uptime data, and independent competitor comparisons." };
  return { companyId: `${summary.slug}-id`, company: summary.company, slug: summary.slug, stage: summary.stage, submissionDate: summary.submissionDate, investment: { amount: null, currency: null, equityPercentage: null, preMoneyValuation: null, postMoneyValuation: null, impliedValuation: null, useOfFunds: [] }, categories: { home: doc("home", [item("home.company_idea", "What is the company idea?", null), item("home.founders", "Who are the founders?", null), diligenceItem]), idea: doc("idea", [item("idea.uniqueness", "How unique is the company idea?", summary.categoryScores.idea)]), market: doc("market", [item("market.portfolio_fit", "Does the company fit the VC portfolio?", portfolioScore)]), financial: doc("financial", [item("financial.current_revenue", "What is the current revenue?", summary.categoryScores.financial)]), management: doc("management", [item("management.academic_background", "How strong is the academic background?", summary.categoryScores.management)]) }, categoryScores: summary.categoryScores, overallScore: summary.overallScore, validationErrors: [] } as CompanyEvaluation;
}
const api = vi.hoisted(() => ({ getCompanies: vi.fn(), getCompany: vi.fn() }));
vi.mock("./lib/api", async () => ({ ...(await vi.importActual<typeof import("./lib/api")>("./lib/api")), getCompanies: api.getCompanies, getCompany: api.getCompany }));
describe("DashboardApp", () => {
  beforeEach(() => { window.history.replaceState({}, "", "/companies/aether/home"); api.getCompanies.mockResolvedValue({ companies: [aether, harbor], registryVersion: 1 }); api.getCompany.mockImplementation((slug: string) => Promise.resolve(evaluation(slug === "harbor" ? harbor : aether))); });
  it("keeps criteria closed while preserving their title and score, then reveals content through the native summary", async () => { render(<DashboardApp />); expect(await screen.findByRole("heading", { name: "Aether Robotics" })).toBeInTheDocument(); const title = screen.getByRole("heading", { name: "What is the company idea?" }); const details = title.closest("details"); const summary = title.closest("summary"); expect(details).not.toHaveAttribute("open"); expect(within(details!).getByLabelText("Score: unavailable")).toBeInTheDocument(); expect(within(details!).getByLabelText("Criterion score: unavailable")).toBeInTheDocument(); expect(summary).not.toBeNull(); fireEvent.click(summary!); expect(details).toHaveAttribute("open"); expect(within(details!).getByText("Aether Robotics assessment.")).toBeInTheDocument(); fireEvent.click(screen.getByRole("link", { name: /market/i })); expect(await screen.findByRole("heading", { name: "Market evaluation" })).toBeInTheDocument(); const portfolioDetails = screen.getByText("Does the company fit the VC portfolio?").closest("details"); expect(portfolioDetails).not.toHaveAttribute("open"); expect(within(portfolioDetails!).getByLabelText("Criterion score: unavailable")).toBeInTheDocument(); });
  it("shows populated Aether investment terms in the dashboard metadata", async () => { api.getCompany.mockResolvedValue({ ...evaluation(aether), investment: { amount: 2500000, currency: "EUR", equityPercentage: 20, preMoneyValuation: 10000000, postMoneyValuation: 12500000, impliedValuation: 12500000, useOfFunds: [] } }); render(<DashboardApp />); expect(await screen.findByLabelText("Investment terms: €2.5M for 20%")).toBeInTheDocument(); });
  it("uses the answered Home assessment for diligence priorities", async () => { render(<DashboardApp />); const heading = await screen.findByRole("heading", { name: "Diligence priorities" }); const priorityBlock = heading.closest("article"); expect(within(priorityBlock!).getByText("Obtain signed contracts, deployment uptime data, and independent competitor comparisons.")).toBeInTheDocument(); expect(screen.queryByRole("heading", { name: "Missing information", level: 2 })).not.toBeInTheDocument(); });
  it("labels unavailable investment terms without inventing a currency", async () => { render(<DashboardApp />); expect(await screen.findByLabelText("Investment terms: Terms unavailable")).toBeInTheDocument(); });
  it("renders all five category views for the fixture-backed company data", async () => {
    render(<DashboardApp />);

    expect(await screen.findByRole("heading", { name: "Aether Robotics" })).toBeInTheDocument();
    expect(screen.getByText("Company overview")).toBeInTheDocument();

    for (const [label, heading] of [
      ["idea", "Idea evaluation"],
      ["market", "Market evaluation"],
      ["financial", "Financials evaluation"],
      ["management", "Management evaluation"],
    ] as const) {
      fireEvent.click(screen.getByRole("link", { name: new RegExp(`^${label}`, "i") }));
      expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
    }
  });
  it("clears the previous company before displaying a newly selected one", async () => { render(<DashboardApp />); expect((await screen.findAllByText("Aether Robotics assessment.")).length).toBeGreaterThan(0); fireEvent.change(screen.getByLabelText("Company under review"), { target: { value: "harbor" } }); await waitFor(() => expect(screen.queryAllByText("Aether Robotics assessment.")).toHaveLength(0)); expect((await screen.findAllByText("Harborloop assessment.")).length).toBeGreaterThan(0); });
  it("rejects a cross-company API response visibly", async () => { api.getCompany.mockResolvedValue(evaluation(harbor)); render(<DashboardApp />); expect(await screen.findByText(/identity check/i)).toBeInTheDocument(); });
});
