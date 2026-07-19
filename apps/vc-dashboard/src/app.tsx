import { useEffect, useState } from "react";
import type { CompaniesList, CompanyEvaluation } from "@sv/contracts/generated";
import { StatusNotice } from "@sv/ui";
import logo from "../../../assets/logo/sv_logo_128.png";
import { CompanySelector } from "./components/company-selector";
import { DashboardNav } from "./components/dashboard-nav";
import { EvaluationCard } from "./components/evaluation-card";
import { HomeOverview } from "./components/home-overview";
import { FounderProjectsCard } from "./components/founder-projects-card";
import { FounderNetworkGraph } from "./components/founder-network-graph";
import { PersonProfileModal } from "./components/person-profile-modal";
import { ApiError, getCompanies, getCompany } from "./lib/api";
import { categoryLabel } from "./lib/format";
import { companyPath, routeFromPath, type Route } from "./lib/routes";

type LoadState<T> = { value: T | null; error: string | null; loading: boolean };
const idle = <T,>(): LoadState<T> => ({ value: null, error: null, loading: true });
const message = (error: unknown) => error instanceof Error ? error.message : "An unexpected error occurred.";

export function DashboardApp() {
  const [route, setRoute] = useState<Route>(() => routeFromPath(window.location.pathname));
  const [companies, setCompanies] = useState<LoadState<CompaniesList>>(idle);
  const [evaluation, setEvaluation] = useState<LoadState<CompanyEvaluation>>({ value: null, error: null, loading: false });
  const [activePersonId, setActivePersonId] = useState<string | null>(null);

  useEffect(() => { const listener = () => setRoute(routeFromPath(window.location.pathname)); window.addEventListener("popstate", listener); return () => window.removeEventListener("popstate", listener); }, []);
  useEffect(() => { const controller = new AbortController(); setCompanies((state) => ({ ...state, loading: true, error: null })); getCompanies(controller.signal).then((value) => setCompanies({ value, error: null, loading: false })).catch((error: unknown) => { if ((error as DOMException).name !== "AbortError") setCompanies({ value: null, error: message(error), loading: false }); }); return () => controller.abort(); }, []);
  const selectedSlug = route.slug ?? companies.value?.companies[0]?.slug ?? null;
  useEffect(() => { if (!selectedSlug) return; const controller = new AbortController(); setEvaluation({ value: null, error: null, loading: true }); getCompany(selectedSlug, controller.signal).then((value) => { if (value.slug !== selectedSlug || Object.values(value.categories).some((document) => document?.slug !== selectedSlug)) throw new ApiError("The API response failed its company identity check. No evaluation was displayed."); setEvaluation({ value, error: null, loading: false }); }).catch((error: unknown) => { if ((error as DOMException).name !== "AbortError") setEvaluation({ value: null, error: message(error), loading: false }); }); return () => controller.abort(); }, [selectedSlug, route.category]);
  useEffect(() => { if (!route.slug && selectedSlug) window.history.replaceState({}, "", companyPath(selectedSlug, route.category)); }, [route.slug, route.category, selectedSlug]);
  const navigate = (slug: string, category = route.category) => { window.history.pushState({}, "", companyPath(slug, category)); setRoute({ slug, category }); };

  return (
    <div className="app-shell sv-app-shell">
      <header className="navbar sv-navbar">
        <a href="/" className="brand sv-brand" aria-label="Sentient Ventures dashboard home">
          <img src={logo} alt="Sentient Ventures" />
          <span>Sentient<br />Ventures</span>
        </a>
        <p>Investment evaluation dashboard</p>
      </header>
      <main>
        {companies.loading && <StatusNotice tone="loading" title="Loading ready companies"><p>Retrieving the evaluation index.</p></StatusNotice>}
        {companies.error && <StatusNotice tone="error" title="The company index could not be loaded"><p>{companies.error}</p><button className="retry-button" onClick={() => window.location.reload()}>Try again</button></StatusNotice>}
        {companies.value?.companies.length === 0 && <StatusNotice tone="empty" title="No ready companies yet"><p>Completed and validated company evaluations will appear here.</p></StatusNotice>}
        {companies.value && companies.value.companies.length > 0 && (
          <>
            <CompanySelector companies={companies.value.companies} selectedSlug={selectedSlug} onSelect={navigate} disabled={evaluation.loading} />
            {selectedSlug && evaluation.value && (
              <DashboardNav 
                slug={selectedSlug} 
                active={route.category} 
                scores={evaluation.value.categoryScores} 
                overallScore={evaluation.value.overallScore} 
                investment={evaluation.value.investment} 
                onNavigate={(category) => navigate(selectedSlug, category)} 
              />
            )}
            {evaluation.loading && <StatusNotice tone="loading" title="Loading evaluation"><p>Retrieving the selected company without retaining the previous company’s data.</p></StatusNotice>}
            {evaluation.error && <StatusNotice tone={evaluation.error.includes("identity check") ? "warning" : "error"} title="Evaluation unavailable"><p>{evaluation.error}</p><button className="retry-button" onClick={() => window.location.reload()}>Try again</button></StatusNotice>}
            {evaluation.value && (
              route.category === "home" 
                ? <HomeOverview evaluation={evaluation.value} onSelectPerson={setActivePersonId} /> 
                : <CategoryPage evaluation={evaluation.value} category={route.category} onSelectPerson={setActivePersonId} />
            )}
          </>
        )}
      </main>
      {activePersonId && (
        <PersonProfileModal userId={activePersonId} onClose={() => setActivePersonId(null)} />
      )}
    </div>
  );
}

function CategoryPage({ 
  evaluation, 
  category, 
  onSelectPerson 
}: { 
  evaluation: CompanyEvaluation; 
  category: Exclude<Route["category"], "home">; 
  onSelectPerson: (id: string) => void; 
}) {
  const [tab, setTab] = useState<"criteria" | "network">("criteria");
  const document = evaluation.categories[category];
  if (!document) return <StatusNotice tone="warning" title={`${categoryLabel(category)} evaluation unavailable`}><p>The API did not supply this category document.</p></StatusNotice>;

  return (
    <>
      <section className="category-heading">
        <p className="eyebrow">{evaluation.company}</p>
        <h1>{categoryLabel(category)} evaluation</h1>
        <p>{document.items.length} criteria · scores are supplied by the API.</p>
      </section>
      {category === "management" && (
        <div className="person-tabs" role="tablist" style={{ marginBottom: "1.5rem" }}>
          <button type="button" className={tab === "criteria" ? "is-active" : ""} onClick={() => setTab("criteria")}>
            Evaluation Criteria
          </button>
          <button type="button" className={tab === "network" ? "is-active" : ""} onClick={() => setTab("network")}>
            Founder Network Graph
          </button>
        </div>
      )}
      {category === "management" && tab === "criteria" && (
        <FounderProjectsCard evaluation={evaluation} onSelectPerson={onSelectPerson} />
      )}
      {category === "management" && tab === "network" && (
        <FounderNetworkGraph evaluation={evaluation} onSelectPerson={onSelectPerson} />
      )}
      {(category !== "management" || tab === "criteria") && (
        <div className="cards">
          {document.items.map((item) => <EvaluationCard key={item.id} item={item} />)}
        </div>
      )}
    </>
  );
}
