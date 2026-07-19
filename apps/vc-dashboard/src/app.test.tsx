import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { CompanyEvaluation, CompanySummary } from "@sv/contracts/generated";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardApp } from "./app";

const aether: CompanySummary = { slug: "aether", company: "Aether Robotics", stage: "Seed", submissionDate: "2026-07-19T12:00:00Z", overallScore: 82, categoryScores: { home: null, idea: 83, market: 80, financial: 82, management: 84 } };
const harbor: CompanySummary = { slug: "harbor", company: "Harborloop", stage: "Pre-seed", submissionDate: "2026-07-18T12:00:00Z", overallScore: 68, categoryScores: { home: null, idea: 71, market: null, financial: 65, management: 68 } };
function evaluation(summary: CompanySummary, portfolioScore: number | null = null): CompanyEvaluation {
  const item = (id: string, title: string, score: number | null) => ({ id, category: id.split(".")[0] as "home" | "idea" | "market" | "financial" | "management", title, score, confidence: 80, assessment: `${summary.company} assessment.`, positiveArguments: ["Supported positive."], negativeArguments: ["Known risk."], evidence: [{ kind: "fact" as const, documentId: "submission", text: "Submitted source." }], missingInformation: score === null ? ["Portfolio data was not provided."] : [], sourceReferences: [{ kind: "fact" as const, documentId: "submission", text: "Submitted source." }], validationErrors: [] });
  const doc = (category: "home" | "idea" | "market" | "financial" | "management", items: ReturnType<typeof item>[]) => ({ schemaVersion: 1 as const, registryVersion: 1 as const, company: summary.company, slug: summary.slug, category, generatedAt: summary.submissionDate, sourceDocuments: [], items, validationErrors: [] });
  return { companyId: `${summary.slug}-id`, company: summary.company, slug: summary.slug, stage: summary.stage, submissionDate: summary.submissionDate, investment: { amount: null, currency: null, equityPercentage: null, preMoneyValuation: null, postMoneyValuation: null, impliedValuation: null, useOfFunds: [] }, categories: { home: doc("home", [item("home.company_idea", "What is the company idea?", null), item("home.founders", "Who are the founders?", null)]), idea: doc("idea", [item("idea.uniqueness", "How unique is the company idea?", summary.categoryScores.idea)]), market: doc("market", [item("market.portfolio_fit", "Does the company fit the VC portfolio?", portfolioScore)]), financial: doc("financial", [item("financial.current_revenue", "What is the current revenue?", summary.categoryScores.financial)]), management: doc("management", [item("management.academic_background", "How strong is the academic background?", summary.categoryScores.management)]) }, categoryScores: summary.categoryScores, overallScore: summary.overallScore, validationErrors: [] } as CompanyEvaluation;
}
const api = vi.hoisted(() => ({ getCompanies: vi.fn(), getCompany: vi.fn() }));
vi.mock("./lib/api", async () => ({ ...(await vi.importActual<typeof import("./lib/api")>("./lib/api")), getCompanies: api.getCompanies, getCompany: api.getCompany }));
describe("DashboardApp", () => {
  beforeEach(() => { window.history.replaceState({}, "", "/companies/aether/home"); api.getCompanies.mockResolvedValue({ companies: [aether, harbor], registryVersion: 1 }); api.getCompany.mockImplementation((slug: string) => Promise.resolve(evaluation(slug === "harbor" ? harbor : aether))); });
  it("renders API criterion content and the unavailable score state", async () => { render(<DashboardApp />); expect(await screen.findByRole("heading", { name: "Aether Robotics" })).toBeInTheDocument(); expect(screen.getByText("What is the company idea?")).toBeInTheDocument(); fireEvent.click(screen.getByRole("link", { name: /market/i })); expect(await screen.findByRole("heading", { name: "Market evaluation" })).toBeInTheDocument(); expect(screen.getByText("Does the company fit the VC portfolio?")).toBeInTheDocument(); expect(screen.getByLabelText("Score: unavailable")).toBeInTheDocument(); });
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
