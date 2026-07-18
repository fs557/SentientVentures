# SentientVentures — Implementation-Ready PoC Plan

## 1. Executive summary

SentientVentures will be a single repository with two desktop React applications and one local FastAPI service:

- Founder Submission Portal: `http://localhost:8080`
- VC Evaluation Dashboard: `http://localhost:8081`
- API and in-process worker: `http://localhost:8000`

The API owns uploads, filesystem-backed company records, document processing, a bounded three-role LLM Council, deterministic Markdown generation/validation, scoring, and dashboard data. The dashboard **never** reads Markdown from disk: it requests normalized, validated data from the API. Markdown remains the human-readable, versioned interchange artifact between processing and presentation.

The initial delivery is deliberately local and single-process. It must reliably demonstrate: submit PDFs/LinkedIn details, see asynchronous progress, process a company, produce five evaluation Markdown files, and switch safely between two complete fictional companies in the dashboard.

## 2. Confirmed assumptions

- This is a greenfield hackathon PoC. Repository inspection found no frontend, backend, parser, fixtures, API routes, database, or running services.
- Existing material is `AGENTS.md`, two specifications, `environment.yml`, `README.md`, and `assets/logo/sv_logo.png` (1254×1254) plus `sv_logo.ico` (32×32). The PNG is the shared navbar source asset.
- Python 3.11 remains the backend version because `environment.yml` declares it. TypeScript 5.x is used for all web packages.
- The client supplies `company_name`, `founder_name`, and `founder_email` at submission. They are required for stable tracking and are explicitly user-entered submission metadata, not inferred document facts.
- One pitch-deck PDF is required. One CV PDF **or** a valid LinkedIn HTTPS URL is required. Up to four optional supporting PDFs are supported in v1 (financial or other documents).
- The API runs as one local Uvicorn process. An in-process worker and polling are simpler and more demonstrable than SSE/WebSockets/queues, and are adequate for one presenter at a time.
- The configured default council model is the environment value `SV_LLM_MODEL` with intended value `gpt-5.4-nano`; availability must be verified with the selected provider before enabling live council processing. Model IDs are never hard-coded in prompts or components.
- No VC portfolio is supplied initially. The portfolio-fit and portfolio-synergy criteria are retained with `score: null`, a provisional/unavailable assessment, and explicit missing information. They are excluded from the Market average until `data/portfolio/portfolio.json` is intentionally added and validated.

## 3. Explicit non-goals

- Mobile/tablet layouts, native apps, multi-language UI, authentication, multi-tenant user accounts, billing, notifications, collaboration, or public sharing.
- A production database, distributed task queue, Kubernetes, object storage, antivirus service, SSO, or real-time events.
- Automatic web browsing, LinkedIn scraping, GitHub scraping, portfolio research, claims verification, financial advice, or autonomous investment decisions.
- Direct rendering of arbitrary uploaded Markdown/HTML, editable council results, model fine-tuning, or repeated multi-agent debate.
- A durable production retention/deletion workflow. The PoC instead has a documented local reset; production requirements are called out below.

## 4. Repository findings and current-state evidence

Read evidence:

| Command / file | Finding and architectural consequence |
|---|---|
| `rg --files` and `find . -maxdepth 3 -type f` | Only specifications, logo assets, environment metadata, README, and this plan exist. All target source paths below are new; no existing implementation convention can be reused. |
| `AGENTS.md` | Python 3.11 backend, TypeScript web code, `environment.yml` as dependency source of truth, restrained agents, and focused changes are required. |
| `docs/specs/sentientventures-poc.md` | Authoritative workflow, question inventory, ports, UI behavior, security expectations, and acceptance criteria. |
| `docs/specs/sentientventures_planner_start_optimized.md` | Planning-run guardrails and the required plan structure. |
| `environment.yml` | Already includes FastAPI, Uvicorn, Pydantic, pytest, httpx, aiofiles, OpenAI/Anthropic SDKs, and Python dotenv; it contains no usable web workspace yet. |
| `file assets/logo/*` | Reuse `assets/logo/sv_logo.png` in shared UI; do not create a new brand asset. |
| `git status --short` | `.codex/config.toml` was already modified before this plan; it is unrelated and must not be changed by implementation phases unless separately authorized. |

## 5. Chosen technology stack

| Concern | Decision | Reason / boundary |
|---|---|---|
| Repository / package manager | pnpm workspace monorepo; root `package.json`, `pnpm-workspace.yaml`; Python remains managed through `environment.yml` | One lockfile for web packages and one explicit Conda environment; shared browser code is natural while Python remains idiomatic. |
| Founder and dashboard apps | React 18 + TypeScript 5 + Vite 5 | Two independent dev servers map cleanly to 8080/8081 without a server-side framework. |
| UI | Tailwind CSS, Radix/shadcn-style primitives, shared `packages/ui` | Accessible desktop components and one visual language. Frontend agent must use `ui-ux-pro-max` for all UI work. |
| Client data | TanStack Query and `fetch`; React Router | Polling, error/retry states, URL-selected company/category, no global data duplication. |
| API | FastAPI + Pydantic v2 + Uvicorn | Present in the declared environment; typed OpenAPI and multipart handling. |
| Contract validation | JSON Schema Draft 2020-12 in `packages/contracts/schema/`; Python `jsonschema`, TypeScript `ajv`; generated TS declarations are checked into `packages/contracts/src/generated.ts` | One versioned interchange contract usable on both sides. Pydantic request models may additionally validate API envelopes, but JSON Schema is canonical. |
| Storage | Local filesystem under `data/companies/`, atomically written JSON/Markdown | Transparent, human-inspectable, resettable PoC; no database needed. |
| PDF extraction | PyMuPDF native text per page; PyMuPDF page rasterization + Tesseract via `pytesseract` only for pages below the configurable text threshold | Native text first, OCR fallback only where needed. Missing Tesseract yields a visible partial-extraction warning, never invented text. |
| Markdown | `PyYAML` front matter plus a deliberately narrow custom Python line parser; normalized JSON is sent to web clients | The contract is deterministic and testable; a general Markdown parser would accept ambiguous structure. Browser components render fields, not raw Markdown. |
| LLM | Provider interface with OpenAI and Anthropic adapters, selected by `SV_LLM_PROVIDER`; structured JSON output validated before deterministic Markdown serialization | Keeps provider/model IDs centralized and prevents prompt text from becoming an implicit API. |
| Jobs | Persisted metadata + single in-process `asyncio.Queue`, polling every 2 seconds | Lowest-complexity asynchronous demo. The worker resumes queued jobs after restart; interrupted running jobs become failed/retryable. |
| Tests | pytest/pytest-asyncio/httpx for API/core; Vitest/Testing Library for web; Playwright for desktop E2E | Matches the existing Python environment and gives targeted UI/E2E coverage. |
| Local command | `pnpm dev` runs Vite founder `8080`, Vite dashboard `8081`, and `conda run -n codex-agents uvicorn apps.api.src.main:app --port 8000 --reload` via `concurrently` | One command for demo while the API retains the specified Python environment. |

Required additions must be declared in `environment.yml` and the web workspace manifests together: PyMuPDF, pytesseract, jsonschema, PyYAML, python-multipart, filetype, `openai`/`anthropic` versions as needed; Vite/React/Tailwind/Radix/TanStack Query/React Router/Ajv/Vitest/Playwright/concurrently. Tesseract itself is a documented host/Conda dependency. No dependency is added until the owning phase.

## 6. Complete architecture

```text
Founder Portal :8080 ──multipart/poll──> FastAPI :8000 <──JSON── VC Dashboard :8081
                                         │
                                         ├─ in-process FIFO worker
                                         ├─ data/companies/<slug>/ (documents, facts, evaluation, metadata)
                                         ├─ deterministic parser/validator/scoring core
                                         └─ LLM Provider -> Pro -> Contra -> Judge -> one repair maximum
```

`packages/contracts` is the contract source of truth. `packages/ui` contains presentation primitives only; it cannot contain company data, scoring logic, or API calls. Backend core modules own parsing, registry, scoring, and storage. The dashboard receives one validated `CompanyEvaluation` aggregate or one validated category document, so no UI component may invent an answer or a score.

## 7. End-to-end data flow

1. Founder enters required company/founder data, adds pitch deck, CV or LinkedIn URL, and optional supporting PDFs. Browser validation is helpful only; API validation is authoritative.
2. `POST /api/v1/submissions` validates the multipart envelope and documents, creates a collision-safe slug, safely stores files and `metadata.json`, persists an idempotency record, and returns `202` plus a queued job.
3. The portal polls the job endpoint. It displays the current state/stage, percentage, retryability, and the returned company slug; it never claims the evaluation is complete until `ready`.
4. Worker validates stored files, extracts native PDF text per page, OCRs only low-text scanned pages, classifies documents, creates source-cited facts, and records missing information.
5. The Council receives only fact records, document provenance, registry items, and a rubric. Pro produces evidence-bound positives; Contra produces evidence-bound risks; Judge emits a structured evaluation object for every registry item.
6. Deterministic validation checks schema, IDs, completeness, score ranges/types, sections, provenance, and forbidden invented-value conditions. A single repair request is permitted only for output-contract failures.
7. The server deterministically serializes the five Markdown documents, re-parses them, calculates scores, atomically writes `evaluation/`, updates `metadata.json` to `ready`, and indexes the company.
8. Dashboard lists only `ready` valid companies. It loads the selected slug, renders semantic item cards, attaches each score to its item, and recomputes no competing score logic; all figures come from the API aggregate.

## 8. Complete target directory structure

```text
.
├── apps/
│   ├── api/
│   │   ├── src/{api,core,providers,workers}/
│   │   └── tests/
│   ├── founder-portal/
│   │   └── src/{app,components,features,lib}/
│   └── vc-dashboard/
│       └── src/{app,components,features,lib}/
├── packages/
│   ├── contracts/{schema,src}/
│   ├── ui/src/
│   └── config/{src,example.env}/
├── assets/logo/{sv_logo.png,sv_logo.ico}
├── data/
│   ├── companies/.gitkeep
│   └── portfolio/portfolio.json                 # optional, not populated by default
├── prompts/{pro-analyst.md,contra-analyst.md,investment-judge.md}
├── scripts/{dev.py,generate_example_companies.py,validate_evaluations.py,reindex_companies.py,reset_demo.py}
├── tests/{fixtures/{markdown,companies,pdf},integration,e2e,contracts}
├── docs/{architecture.md,markdown-contract.md,operations.md}
├── environment.yml
├── package.json
├── pnpm-workspace.yaml
├── playwright.config.ts
├── vitest.workspace.ts
├── .env.example
└── PLAN.md
```

Generated `data/companies/`, uploaded PDFs, extracted text, logs, `.env`, Playwright output, and local virtual environments are ignored. Fictitious test fixtures are versioned; real submissions never are.

## 9. Company storage and isolation model

### IDs, slugs, and directory layout

- `company_id`: server-generated UUIDv4 string in metadata; immutable internal audit key.
- `slug`: API-facing stable identifier: `slugify(company_name)` in lower-case ASCII, `[a-z0-9]+` words separated by one `-`. If occupied, append `-2`, `-3`, etc. The slug is never renamed after creation. APIs accept only `^[a-z0-9]+(?:-[a-z0-9]+)*$` and resolve it from the index—not a free filesystem path.
- Original names are display-only. Stored file names are `<document_id>-<safe_basename>.pdf`, where `document_id` is UUIDv4 and `safe_basename` has only `[a-z0-9._-]`, no leading dot, and maximum 80 characters.

```text
data/companies/<slug>/
├── source/                 # raw user PDFs; API never serves this directory
│   └── <document_id>-<safe_basename>.pdf
├── extracted/
│   ├── document-index.json
│   ├── document-text.json
│   ├── company-facts.json
│   └── founder-facts.json
├── evaluation/
│   ├── <slug>_home.md
│   ├── <slug>_idea.md
│   ├── <slug>_market.md
│   ├── <slug>_financial.md
│   └── <slug>_management.md
├── logs/job-<job_id>.jsonl # structured redacted events, excluded from git
└── metadata.json
```

`metadata.json` is schema-validated and contains `company_id`, `slug`, `display_name`, `stage` (optional), `created_at`, `submission` (founder name/email and URL fields), source-document metadata, job summary, current state, contract/registry versions, category/overall scores, validation error summaries, and output hashes. Every write goes first to a same-directory temporary file, is fsynced, then atomically renamed. Generated evaluations are written to a temporary evaluation directory and swapped only when all five parse and validate.

### Source-document metadata contract

```json
{
  "id": "doc_550e8400-e29b-41d4-a716-446655440000",
  "role": "pitch_deck",
  "original_name": "Aether Deck.pdf",
  "stored_name": "doc_...-aether-deck.pdf",
  "media_type": "application/pdf",
  "size_bytes": 1842300,
  "sha256": "<64 lowercase hex characters>",
  "uploaded_at": "2026-07-19T12:00:00Z",
  "page_count": 14,
  "extraction": {"native_pages": [1,2], "ocr_pages": [3], "warnings": []}
}
```

Isolation boundary: all storage functions take a validated `CompanyRef` resolved from the company index, derive paths internally, call `resolve()`, and require the resolved path to be within that company’s resolved root. No request parameter is interpolated into a path. Jobs carry only `company_id`/slug and must re-resolve metadata before every stage. API aggregate creation loads exactly one company root; cache keys include slug; dashboard selection is the URL slug and query cache key.

## 10. Canonical question registry

The registry is `packages/contracts/schema/question-registry.v1.json`. It is immutable once fixtures exist; a semantic change creates `v2`. Each entry contains `id`, `category`, exact `title`, `score_required`, `portfolio_required` (when applicable), `display_order`, and a short rubric. IDs, not titles, are the identity. Documents must contain every category entry once, in display order; unknown or duplicate IDs are errors.

| Category | Stable ID → exact canonical title, in required order |
|---|---|
| `home` (facts; scores optional/not required) | `home.company_name` → What is the company name?; `home.current_valuation` → What is the current valuation?; `home.company_idea` → What is the company idea?; `home.sector` → In which sector does the company operate?; `home.what_company_does` → What exactly does the company do?; `home.use_of_investment` → What will the requested investment be used for?; `home.equity_offered` → How much equity is offered?; `home.investment_requested` → How much investment is requested?; `home.implied_valuation` → What implied valuation follows from the proposed terms?; `home.founders` → Who are the founders?; `home.founder_facts` → What are the most important founder facts?; `home.company_facts` → What are the most important company facts?; `home.missing_information` → What important information is missing? |
| `idea` (all scored) | `idea.uniqueness` → How unique is the company idea?; `idea.copyability` → How easily can the idea be copied?; `idea.defensibility` → How defensible is the idea?; `idea.protectability` → Is the idea patentable or otherwise protectable?; `idea.technical_execution_complexity` → How complex is the technical execution?; `idea.operational_execution_complexity` → How complex is the operational execution?; `idea.goal_effort` → How much effort is required to achieve the stated goal?; `idea.sustainability` → How sustainable or environmentally friendly is the idea?; `idea.fundamental_problems` → What fundamental problems exist with the idea?; `idea.problem_solution_clarity` → How clearly does the idea solve a real problem?; `idea.value_proposition` → How strong is the value proposition?; `idea.product_maturity` → How mature is the current product or prototype? |
| `market` (all scored) | `market.addressable_market` → How large is the addressable market?; `market.market_size_reliability` → How reliable is the stated market-size estimate?; `market.sector_trend` → Is the sector trending upward or downward?; `market.expected_growth` → What market growth can reasonably be expected?; `market.entry_timing` → How strong is the timing for market entry?; `market.competition` → How strong is the competition?; `market.entry_barriers` → What barriers to entry exist?; `market.customer_adoption` → How difficult will customer adoption be?; `market.market_problems` → What problems exist in the target market?; `market.portfolio_fit` → Does the company fit the VC portfolio?; `market.portfolio_synergies` → Are there synergies with the existing portfolio?; `market.target_customer_clarity` → Is the target customer clearly defined?; `market.gtm_plausibility` → Is the go-to-market strategy plausible?; `market.customer_concentration` → How concentrated is the customer base likely to be?; `market.regulatory_barriers` → Are regulatory barriers relevant? |
| `financial` (all scored) | `financial.current_revenue` → What is the current revenue?; `financial.current_profit_loss` → What is the current profit or loss?; `financial.projected_revenue` → What future revenue is projected?; `financial.projected_profit` → What future profit is projected?; `financial.projection_plausibility` → How plausible are the projections?; `financial.customer_acquisition_cost` → What is the customer acquisition cost?; `financial.recurring_customer_rate` → What is the recurring customer rate?; `financial.customer_retention_rate` → What is the customer retention rate?; `financial.revenue_per_employee` → What is the revenue per employee?; `financial.profit_per_employee` → What is the profit per employee?; `financial.burn_rate` → What is the current burn rate?; `financial.runway` → What is the current runway?; `financial.funding_requirement_plausibility` → How plausible is the funding requirement?; `financial.capital_allocation` → How will the requested capital be allocated?; `financial.exit_strategy` → What is the proposed exit strategy?; `financial.inconsistencies` → What financial inconsistencies exist?; `financial.risks` → What financial risks exist?; `financial.document_completeness_reliability` → How complete and reliable are the submitted financial documents?; `financial.forecast_drivers` → What assumptions have the largest influence on the forecast? |
| `management` (all scored; visible label `MANAGEMENT`) | `management.academic_background` → How strong is the academic background?; `management.professional_background` → How relevant is the professional background?; `management.domain_expertise` → How deep is the domain expertise?; `management.technical_expertise` → How strong is the technical expertise?; `management.commercial_expertise` → How strong is the commercial expertise?; `management.founder_market_fit` → How strong is the founder-market fit?; `management.professional_following` → How large is the founder's professional following or influence?; `management.controversies` → Are there relevant controversies?; `management.creativity` → How creative or innovative is the management team?; `management.strengths` → What are the management team's greatest strengths?; `management.weaknesses` → What are the management team's greatest weaknesses?; `management.missing_roles` → Are important roles missing?; `management.execution_ability` → How strong is the team's ability to execute?; `management.credibility` → How credible and trustworthy does the team appear?; `management.team_balance` → Is the team sufficiently balanced?; `management.prior_execution` → Is there evidence of previous successful execution? |

All `idea`, `market`, `financial`, and `management` entries require an integer score. `home` is factual and never contributes to overall scoring. If optional home scoring is introduced later, it must use new registry IDs and remain excluded by the `overall_categories` configuration by default.

## 11. Canonical Markdown contract

### Versioned grammar

Every generated document uses UTF-8, LF line endings, one final newline, the canonical registry order, and this exact narrow grammar. Markdown generation is a serializer from validated JSON; LLMs never write final Markdown directly.

```markdown
---
schema_version: 1
registry_version: 1
company: "Aether Robotics"
slug: "aether-robotics"
category: "idea"
generated_at: "2026-07-19T12:00:00Z"
source_documents: ["doc_...", "doc_..."]
---

# Idea Evaluation

## idea.uniqueness | How unique is the company idea?

**Score:** 88
**Confidence:** 82

### Assessment
The supplied material describes an industry-specific inspection workflow; uniqueness is an inference, not a verified market fact.

### Positive Arguments
- Specialized workflow is directly described in `doc_...`, p. 4.

### Negative Arguments and Risks
- Comparable alternatives were not independently researched.

### Evidence
- fact | doc_... | p. 4 | Product workflow is described for industrial inspection.
- inference | doc_... | p. 4 | Niche specialization may improve differentiation.

### Missing Information
- Independent competitor comparison was not provided.

### Source References
- doc_... | p. 4 | Product section
```

Rules:

- Front matter keys are exactly those above; no unknown keys. `schema_version` and `registry_version` must equal supported integers; category must match filename and registry; slug must match containing directory. `source_documents` contain document IDs, not unsafe filenames.
- Each `##` heading is exactly `<stable-id> | <registry title>` and appears once. The parser rejects missing, duplicate, out-of-category, reordered, or title-mismatched headings.
- Each item has the six headings in the exact order shown. Every section must have non-empty text/list content. When an argument or evidence does not exist, write a truthful list item such as `- No direct evidence was provided.`; do not leave it blank.
- `Score` is either an unquoted base-10 integer from `1` through `100` or `N/A`. `N/A` is permitted only for Home or configured unavailable criteria (initially the two portfolio criteria when no portfolio file exists). Any `0`, `101`, decimal, words, blank score, or score-required `N/A` is invalid.
- `Confidence` is an optional base-10 integer `1..100` or `N/A`; absent means `null`. It is never used in scoring.
- Evidence lines must begin `fact` or `inference`, include a known document ID or `submission`, and may include page/section. `fact` means directly supported; `inference` means a bounded conclusion from named facts. Missing facts are represented only in `### Missing Information` as explicit bullets.
- Text is plain Markdown text; raw HTML is forbidden. The backend parser does not render HTML. If a future view renders Markdown, it must use an HTML-disabled renderer plus DOMPurify.

### Parser and malformed-file behavior

`parse_evaluation_document(markdown, expected_slug, expected_category)` first validates front matter, then parses only the grammar above line-by-line, normalizes it to the contract JSON, and returns all errors without silently discarding content. Unknown `###` section or preamble text is an error; unknown non-structural content within a valid section is retained as text. A malformed document is not indexed as ready. Existing prior-good evaluation remains available until a whole replacement set validates. Duplicate question IDs invalidate that document and produce no category score. Invalid/missing scores preserve the parsed assessment, set `score: null`, add a validation error, exclude the item from averaging, and request the one allowed repair during pipeline generation.

## 12. Normalized internal data model

The following JSON Schema objects are the public/API-normalized shape (camelCase after API serialization). Python uses equivalent Pydantic adapters internally; no frontend object reads files or reimplements parsing.

```ts
type EvaluationCategory = "home" | "idea" | "market" | "financial" | "management";
type EvidenceKind = "fact" | "inference";

interface EvidenceReference {
  kind: EvidenceKind;
  documentId: string | "submission";
  page?: number;
  section?: string;
  text: string;
}
interface FactRecord {
  id: string;
  subject: "company" | "founder" | "investment" | "market" | "financial";
  field: string;
  value: string | number | boolean | string[] | null;
  status: "fact" | "inference" | "missing_information";
  evidence: EvidenceReference[];
  missingReason?: string;
  sourceDocumentIds: string[];
}
interface EvaluationItem {
  id: string; category: EvaluationCategory; title: string;
  score: number | null; confidence: number | null;
  assessment: string; positiveArguments: string[]; negativeArguments: string[];
  evidence: EvidenceReference[]; missingInformation: string[];
  sourceReferences: EvidenceReference[]; validationErrors: ValidationIssue[];
}
interface EvaluationDocument {
  schemaVersion: 1; registryVersion: 1; company: string; slug: string;
  category: EvaluationCategory; generatedAt: string; sourceDocuments: string[];
  items: EvaluationItem[]; validationErrors: ValidationIssue[];
}
interface InvestmentTerms {
  amount: number | null; currency: string | null; equityPercentage: number | null;
  preMoneyValuation: number | null; postMoneyValuation: number | null;
  impliedValuation: number | null; useOfFunds: string[];
}
interface ValidationIssue { code: string; path: string; message: string; severity: "warning" | "error"; }
interface CompanyEvaluation {
  companyId: string; company: string; slug: string; stage: string | null;
  submissionDate: string; investment: InvestmentTerms;
  categories: Partial<Record<EvaluationCategory, EvaluationDocument>>;
  categoryScores: Record<EvaluationCategory, number | null>;
  overallScore: number | null; validationErrors: ValidationIssue[];
}
```

`FactRecord` explicitly prevents fact/inference/missing-information collapse. A fact extractor may derive an `inference` only with supporting fact evidence; a missing record has `value: null`, a reason, and no made-up numeric surrogate. Numeric values retain parsed raw text and currency/unit in the internal extraction schema; conversion into `InvestmentTerms` occurs only when unit/currency is unambiguous.

## 13. API contracts

All routes live under `/api/v1`, return JSON, use UTC ISO-8601 timestamps, and return errors as `{ "error": { "code", "message", "details": [{"path","code","message"}], "requestId" } }`. `400` is malformed syntax, `404` unknown resource, `409` duplicate/conflict, `413` size limit, `415` media type, `422` semantic validation, `429` retryable capacity limit, and `500/502/504` server/provider failures. Responses never include raw PDF bytes, extracted full text, API keys, or unredacted prompt logs.

| Method and route | Request / validation | Success response | Failure and idempotency |
|---|---|---|---|
| `GET /health` | none | `200 {status:"ok", version, workerAvailable}` | `503` when storage/worker unavailable; naturally idempotent. |
| `POST /submissions` | `multipart/form-data`: required `company_name` 2–120 plain chars, `founder_name` 2–120, `founder_email` valid email, `pitch_deck` one PDF; exactly one-or-more of `cv` PDF / `linkedin_url` valid HTTPS URL; optional `github_url`, `website_url` valid HTTPS URLs; `supporting_documents` 0–4 PDFs. Individual max 25 MiB, aggregate max 75 MiB, max 100 pages/file. Required `Idempotency-Key` UUID. | `202 {company:{id,slug,name}, job:{id,state:"queued",statusUrl}, acceptedAt}` | Reject extension/content-type/magic-byte mismatch, invalid URLs, duplicate fields, or limits. Same key + same request hash returns the original `202`; same key + differing hash returns `409 IDEMPOTENCY_CONFLICT`. |
| `GET /jobs/{slug}` | validated slug; job belongs to resolved company | `200 {id,companySlug,state,stage,progress,attempt,repairCount,updatedAt,error,retryAllowed}` | `404`; idempotent. Never returns other-company job data. |
| `POST /jobs/{slug}/retry` | only `failed`, `attempt < 2`, same validated company root | `202 {id,state:"queued",attempt:2,statusUrl}` | `409` for ready/running/exhausted; required `Idempotency-Key`, duplicate retry replayed. One manual full-job retry maximum. |
| `GET /companies` | optional `limit` 1–100 (default 50); no filesystem paths | `200 {companies:[{slug,company,stage,submissionDate,overallScore,categoryScores}], registryVersion}` for valid `ready` companies only | `500 INDEX_INVALID` if global index cannot be read; idempotent. |
| `GET /companies/{slug}` | validated slug and `ready` state | `200 CompanyEvaluation` with all five normalized documents, summary, scores, and non-sensitive warnings | `404` unknown/not-ready, `409` invalid output retained only in internal logs; idempotent. |
| `GET /companies/{slug}/categories/{category}` | validated slug/category and ready document | `200 EvaluationDocument` | `404` document absent, `422` invalid category; idempotent. |
| `POST /dev/reset` | development only: `SV_ENABLE_DEV_RESET=true`, header `X-Demo-Reset-Token` matches secret; body `{confirm:"RESET_DEMO"}` | `204`; regenerates fixtures and clears only explicitly configured demo directories | Disabled and `404` otherwise; idempotency key required. Never enabled in deployment. |

API CORS admits only configured origins `http://localhost:8080` and `http://localhost:8081` in development; no wildcard credentials. The OpenAPI document is generated from FastAPI and contract-tested against checked-in schemas.

## 14. Processing-job state machine

`metadata.json` contains a job history and the current job. Progress is an informational fixed mapping, not a declaration of quality.

```text
queued -> validating -> extracting -> classifying -> fact_extracting
       -> council_preparing -> pro_analysis -> contra_analysis -> judging
       -> markdown_validating -> [repairing -> markdown_validating] -> scoring
       -> indexing -> ready
any non-terminal state -> failed
failed -> queued  (manual retry once only)
ready, failed     (terminal for current attempt)
```

Allowed transitions are only adjacent forward arrows, `failed`, and one retry from failed. `repairing` can be entered once (`repair_count == 0`) only from `markdown_validating`; it returns only to `markdown_validating`. A cancelled state is intentionally omitted because the v1 UI has no safe cancellation guarantee. Server startup changes a persisted non-terminal job to `failed` with `WORKER_INTERRUPTED`, preserving stage artifacts; it may then be manually retried.

| Stage | Input → output | Validation, errors, retry, logging |
|---|---|---|
| validating | multipart metadata/files → validated manifest | magic bytes, MIME, hash, limits, safe storage check; deterministic failure has no automatic retry; redacted `event=validation_failed`. |
| extracting | PDFs → page text/OCR metadata | native extract first; OCR only low-text pages; corrupt PDF fails; unavailable OCR warns/records missing text; transient I/O retries twice with capped exponential delays. |
| classifying | texts/roles → document index | recognized roles `pitch_deck`, `cv`, `supporting`; unknown supporting retained as `supporting`; deterministic no retry. |
| fact_extracting | text/submission fields → cited `FactRecord[]` | structured-schema validation and provenance checks; one provider network retry twice; schema failure fails job (not council repair). |
| council_preparing | facts/registry → redacted bounded council context | filters raw instruction-like text, size caps excerpts, validates registry version; no automatic retry. |
| pro_analysis / contra_analysis | context → structured analyst output | output schema/provenance required; per-call transient retry twice, 30s timeout; permanent failure fails job. |
| judging | facts + analyses + registry → structured documents | must enumerate every registry ID; transient retry twice; output violations continue to Markdown validation. |
| markdown_validating | Judge object → serializer → five parsed documents | deterministic schema/registry/score/section checks; exactly one `repairing` request for repairable Judge output; subsequent error fails. |
| scoring | valid docs → scores/aggregate | central scorer only; malformed/invalid score cannot be silently normalized; no retry. |
| indexing | aggregate + hashes → atomic metadata/index | read-back parse and atomic swap; transient I/O retry twice; sets `ready` only after all files succeed. |

All events are structured JSON lines with `request_id`, `job_id`, `company_slug`, stage, duration, outcome, and error code. Logs omit full documents, emails, keys, prompt bodies, and model responses; diagnostics use hashes/counts and redacted excerpts.

## 15. LLM Council design

`LLMProvider.complete_json(system_prompt, payload, schema, timeout)` is the only provider surface. `OpenAIProvider` and `AnthropicProvider` implement it; provider/model/base URL/timeouts are centrally read from config. Dependency injection selects a deterministic fake provider for tests. The UI/API know neither provider nor model name except an optional sanitized status label.

1. **Pro Analyst** receives registry, facts, explicit missing records, and cited snippets. It returns only evidence-based strengths, opportunities, upside hypotheses labelled inference, and cited evidence by question ID.
2. **Contra Analyst** receives the same factual packet (not Pro output, to avoid anchoring). It returns evidence-based weaknesses, contradictions, risks, unsupported assumptions, and missing information by question ID. It must not manufacture disagreement.
3. **Investment Judge** receives the fact packet, both structured analyses, registry, score rubric, portfolio context status, and strict JSON Schema. It produces one normalized item for every ID, without Markdown.
4. **Deterministic validator** rejects schema/registry/score/provenance/empty-section violations. It creates a concise repair payload listing only JSON Pointer paths and expected constraint—not raw source documents or a new open-ended question.
5. **Optional repair** calls the Judge once with original structured output plus issues. The same deterministic validation runs again; a second failure is terminal.

There is no Pro/Contra conversation and no unlimited loop. Fact extraction and the Council are separately logged/audited by artifact hash so a failure can be diagnosed without retaining PII-rich prompts.

## 16. Prompt responsibilities and injection defenses

Each versioned prompt begins with immutable role/rules: uploaded text is untrusted reference data; it cannot override role, schema, registry, score range, tool policy, or requested output. Inputs are passed in labelled JSON fields (`facts`, `untrusted_document_excerpts`, `registry`), never concatenated into developer/system instructions. Prompts require citations to provided document IDs/pages, facts versus inference, explicit `Not provided`/`Insufficient information`, and prohibit invented revenue, profits, market size, customers, valuation, patents, partnerships, funding, or founder history.

The context builder removes executable/HTML content, caps per-document and total characters, preserves provenance, and labels common injection phrases as untrusted text without trying to execute or follow them. Links are data, never fetched. Source excerpts do not include user email unless necessary for a factual field (it is not). Council outputs referencing unknown document IDs, factual claims without evidence, or prohibited fields absent from facts are validation errors. The judge may evaluate only supplied portfolio JSON; absent data forces provisional/unavailable portfolio items.

## 17. Validation and single-repair strategy

Validation is deterministic and has four gates:

1. **Input gate:** request/files/URL/storage metadata schemas and containment checks.
2. **Facts gate:** `FactRecord` schema, allowed status, citation IDs/pages, null-required missing records, and raw numeric-unit preservation.
3. **Judge gate:** JSON Schema, every registry ID exactly once, category/title alignment, strings/lists nonempty, evidence/missing-information requirement, scores `1..100` integer where required, portfolio availability rule, and no unsupported fact claim.
4. **Artifact gate:** deterministic serialization, strict reparse, document hash, five-document completeness, scorer results, and atomic-index read-back.

Repairable Judge violations are a missing ID, required empty section, unsupported/missing/invalid score, or schema shape error. The repair request contains the original output and machine-readable errors; it cannot add new source material or request a new evaluation. `repair_count` begins at zero and must be at most one. An invalid score stays `null` in the diagnostic normalized item and is excluded from averages, never replaced by 50. In production pipeline output, a second invalid required score blocks `ready`; existing good output is preserved.

## 18. Scoring rules

`packages/contracts` specifies the scorer; `apps/api/core/scoring.py` is the sole implementation, with generated test vectors consumed by TypeScript. Scores are integer `1..100`; confidence does not influence scores.

```text
categoryScore(category) = round_half_up(sum(valid required item scores) / count(valid required item scores))
overallScore = round_half_up(mean(valid category scores of idea, market, financial, management))
```

- Equal category weights are the v1 decision; the dashboard discloses `Equal-weight average of available Idea, Market, Financial, and Management scores`.
- `home` is always excluded. Market portfolio items are excluded only while the validated portfolio context is absent; their dashboard card displays `Score unavailable — VC portfolio data not configured`.
- Any `null`/invalid score is excluded, listed in validation warnings, and shown as `Score unavailable`; it never gets a color/label. A category with no valid required scores is `null`; no valid category scores means overall `null`.
- `1..39 Critical`, `40..59 Weak`, `60..69 Mixed`, `70..79 Promising`, `80..89 Strong`, `90..100 Exceptional`. Text labels accompany color; threshold constants live in `packages/contracts/schema/scoring.v1.json`.
- `Math.round` equivalent half-up behavior is stipulated in shared vectors, including 72.5 → 73. No weighted scoring in v1.

## 19. Frontend component hierarchy

```text
AppShell
├── SharedNavbar(Logo, ProductName, optional controls)
├── FounderPortal
│   ├── SubmissionForm
│   │   ├── CompanyCard(PitchDeckDropzone, SupportingDocumentsDropzone)
│   │   ├── PersonalCard(FounderFields, CvDropzone, OrDivider, LinkedInField, ProfileLinks)
│   │   ├── FileRow(progress, success/error, replace/remove)
│   │   └── SubmissionStatus(job state, progress, retry, company slug)
│   └── ErrorSummary / accessible field errors
└── Dashboard
    ├── CompanySelector
    ├── DashboardNav(Home, CategoryLinksWithScores, non-clickable OverallScore)
    ├── HomeOverview(Company, Investment, Founders, ScoreOverview, TopSignals)
    └── CategoryPage
        └── EvaluationCriterionCard
            ├── CriterionNarrative(assessment, positives, risks, evidence, missing info)
            └── CriterionScore(score, label, bar, confidence)
```

`EvaluationCriterionCard` accepts only `EvaluationItem`; it owns no parsing/scoring. It renders score right-aligned in a 20–25% column and narrative in 75–80%, with label plus number so color is secondary. Core evidence/risks/missing information are visible without hover; only secondary reference detail may expand.

## 20. Founder Portal structure — port 8080

Route `/` has a max-width 1500px centered desktop canvas (minimum supported width 1400px), persistent shared navbar, and equal-width Company/Personal cards. Company card includes required PDF pitch drop/click area and multi-file optional supporting PDF area. Personal card has required founder name/email fields, a CV PDF drop/click option, a visual `OR`, LinkedIn HTTPS input, and optional GitHub/personal-site HTTPS inputs. The CV/LinkedIn cross-field error is clear and announced accessibly.

File rows show filename, byte size, individual upload/validation status, removal and replacement. The primary label is exactly **Submit Application**. Submit first validates all fields, then sends a multipart request with a generated UUID idempotency key held for the attempt. After `202`, it polls until ready/failed, displays meaningful stages (not fake completion), keeps the returned company identifier visible, and offers the one permitted job retry only when API says `retryAllowed`. Network retry repeats the same idempotency key. Browser data is discarded on successful completion; no PII is persisted in localStorage.

## 21. VC Dashboard structure — port 8081

Routes are `/companies/:slug/home`, `/companies/:slug/idea`, `/market`, `/financial`, and `/management`; invalid/missing slug redirects to the first ready company or an empty-state screen. The shared navbar keeps the logo visible. A sticky desktop navigation shows `HOME`, category scores, and non-clickable `SCORE <overall>`; the initial labels match requested presentation (`FINANCIALS` visible for `financial`, `MANAGEMENT` visible for `management`). Active category is unmistakable and score labels/data are never hard-coded.

The company selector is loaded from `/companies`, presenting name, overall score (or unavailable), optional stage, and submission date. Changing it constructs a new URL slug, clears only the previous query view, and requests the selected aggregate; it cannot retain items from company A while showing company B. Home maps registry facts into Company Overview, Investment Terms, Founder Overview, Score Overview, Top Investment Arguments, key risks, and missing information. Values absent from source data render `Not provided`, never a fictitious placeholder.

Every category page renders all registry items independently, including `Score unavailable` cards and explicit portfolio unavailable cards. Long narrative scrolls in the page while navigation remains visible. The application uses a restrained, analytical desktop visual style, no decorative score charts, no huge empty areas, and no mobile-first compromise.

## 22. Company selection and data-isolation behavior

- The list endpoint publishes only valid ready company summaries; selected `slug` is the stable API/browser identity.
- Aggregate/category requests are keyed by `{slug, registryVersion}`. Selection cancellation uses `AbortController`; loading state replaces the previous detail pane before new data appears.
- API access resolves slug strictly, reads one company root, confirms all parsed front-matter slugs equal route slug, and rejects mismatches. It never scans a glob based on user input.
- A response has exactly one `slug`; the client asserts every document/item category matches it before display and shows a data-integrity error rather than mixing data.
- The LLM worker receives an immutable `CouncilContext` constructed from only its job's company root. No global company discovery, caches, or prior company facts enter context.

## 23. Configuration and secrets

`.env.example` documents names only; `.env` is ignored. `packages/config` has a typed, fail-fast configuration loader. Required for live council: `SV_LLM_PROVIDER`, `SV_LLM_MODEL`, provider API key (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`), `SV_DATA_ROOT`, `SV_ALLOWED_ORIGINS`, and `SV_MAX_FILE_BYTES`; optional: `SV_OCR_ENABLED`, `SV_OCR_TEXT_THRESHOLD`, `SV_LLM_TIMEOUT_SECONDS`, `SV_LOG_LEVEL`, `SV_ENABLE_DEV_RESET`, `SV_DEMO_RESET_TOKEN`.

Defaults are local-safe: data root `./data/companies`, origins ports 8080/8081, max individual 25 MiB, aggregate 75 MiB, OCR enabled only when Tesseract is detected, 30-second council-call timeout, and dev reset disabled. Startup validates real-path containment, allowed provider, model nonempty, and secret presence when provider is live. Secrets never appear in plans, fixtures, frontend bundle, errors, logs, telemetry, or commits. Browser config may contain only `VITE_API_BASE_URL`.

## 24. Security and privacy considerations

| Risk | Required control |
|---|---|
| Wrong/malicious upload | Require PDF extension, content type, and `%PDF-` magic bytes; size/page limits; stream to temp file; do not execute/embed; PyMuPDF extraction in constrained worker process is the post-hackathon upgrade. |
| Filename/path traversal/symlink | Ignore client path, sanitized UUID stored names, no user-derived paths, resolved containment checks, restrictive data-root permissions, no source-file download endpoint. |
| Malformed/encrypted/PDF bomb | page and byte caps, parser timeouts, catch/record parser exception, mark job failed/retryable; no unsafe rendering. |
| Markdown/XSS | deterministic parser only; raw HTML prohibited; semantic field rendering with React escaping; future raw Markdown needs HTML disabled plus DOMPurify. |
| Prompt injection | untrusted labelled excerpts, fixed system instructions/schemas, no tools/web fetching, text caps, citations required, output validation. |
| Invented facts | facts/inferences/missing records, provenance enforcement, forbidden-claim checks, unavailable states rather than synthetic values. |
| PII | minimize founder details, do not expose email in dashboard, redact logs/prompts, ignore real data in git, local reset. |
| Cross-company leakage | validated slug resolver, per-company roots, atomic artifacts, slug-inclusive caches/logs/jobs, isolation tests. |
| Secrets / browser exposure | server-only keys, typed env loading, `.env` ignored, no secret in Vite env, redacted errors. |
| Availability / duplicate work | idempotency keys and hashes, persisted state, bounded retries/timeouts, atomic write/index, prior-good output retention. |

The PoC has no authentication and must only be demonstrated on a trusted local machine. It is not suitable for real founder submissions without authentication, malware scanning/sandboxing, encryption, retention policy, consent, access controls, and audit controls.

## 25. Testing strategy and required fixtures

Fixtures are deterministic and versioned under `tests/fixtures`; fake-provider tests never call real models. `scripts/generate_example_companies.py` serializes two complete fictional company fixture sets from checked-in structured inputs and validates them. The script must be deterministic (fixed timestamps/IDs) and its output hash verified in CI.

| Layer | Required coverage |
|---|---|
| Contract / registry | JSON Schema validation, all 75 required IDs, exact title/order/category, registry-version compatibility, generated TS declaration check. |
| Markdown parser | valid complete file; missing front matter; missing question; duplicate question; missing/invalid score; score boundaries 1/100; `N/A` rules; unknown section; empty assessment; multiple evidence entries; malformed Markdown; unsupported category; heading/title mismatch; raw HTML; slug/filename mismatch. |
| Scoring | normal category average, rounding, one invalid score, all invalid, missing category, Home exclusion, equal-weight overall, unavailable portfolio items, all-null overall. |
| Storage/security | safe-name transformation, magic/type mismatch, size/page caps, traversal `../`, symlink containment, atomic failed write, corrupt/encrypted PDF, OCR unavailable/low-text fallback. |
| Submission/API | valid pitch; invalid type; oversized file; CV path; LinkedIn path; neither CV nor LinkedIn; invalid links; duplicate idempotency replay/conflict; processing failure; CORS; error envelope/OpenAPI contract. |
| Council | context only selected-company facts, Pro/Contra provenance, every ID emitted, evidence-or-explicit-missing data, invalid output invokes exactly one repair, second invalid fails, no model call in deterministic validation tests. |
| Integration | upload → fake worker → five Markdown files → parse → index → aggregate; stale prior evaluation preservation; job recovery/retry limits; company A/B data isolation. |
| Web unit | criterion binds correct score/title, unavailable score, missing-information state, company switch clears stale data, category nav/overall non-link, status/retry state. |
| E2E (Playwright) | both fixture companies on 1920×1080 and 2560×1440; all required questions/cards visible; long content; company change; portal CV submission; LinkedIn submission; validation/error/retry; no mixed company text. |

Commands, once implemented: `conda run -n codex-agents pytest`; `pnpm lint`; `pnpm typecheck`; `pnpm test`; `pnpm exec playwright test`; `python scripts/validate_evaluations.py tests/fixtures/companies`. Run the smallest owning suite in every phase before the full suite. Do not claim any command passed until it has run.

## 26. Example-company strategy

Create two complete, clearly fictional, non-overlapping fixture companies from structured source facts—not hand-authored UI state:

- **Aether Robotics:** strong but imperfect industrial inspection workflow; relevant founders, attractive market trend, credible financial plan, documented risks, and generally high non-perfect scores.
- **HarborLoop:** interesting circular-logistics concept with weak defensibility, uncertain demand, missing financial metrics, management gaps, and medium/low scores.

Each has a fixture `metadata.json`, document-index/facts, and all five v1 Markdown files with all 75 registry questions (13 Home factual and 62 scored non-Home), nonempty assessment/argument/risk/evidence-or-missing sections, valid integer scored items except explicitly unavailable portfolio items, and distinct evidence/narrative. They power parser/scoring/isolation/dashboard/council-output tests and demo. Fixture PDFs may be small synthetic PDFs created by an approved fixture-generation step; no real personal/company data, network fetch, or copied real deck.

## 27. Implementation phases

Only one write-capable implementation agent works at a time until contracts are frozen. Testing can run in parallel only after its targets are not being edited. Exact commands below are planned validations, not commands already executed.

### Phase 0 — Scaffold and contract freeze

| Field | Plan |
|---|---|
| Objective / owner / complexity | Establish the monorepo, environment manifests, versioned contracts, registry, score vectors, and frozen interfaces. **Planner**, then Backend for mechanical scaffold; **large**. |
| Dependencies | This approved `PLAN.md`. |
| Affected paths | `package.json`, `pnpm-workspace.yaml`, `environment.yml`, `apps/*` skeletons, `packages/contracts/**`, `packages/config/**`, `.env.example`, ignore files. |
| Outputs | Valid workspace, JSON schemas, all registry IDs, API/error/job schemas, score test vectors, generated TS types, documented config. |
| Acceptance | No UI/LLM behavior yet; contracts validate; all agents agree contract is frozen before fixtures. |
| Tests | `pnpm install --frozen-lockfile` (after lock exists), `pnpm typecheck --filter @sv/contracts`, `conda run -n codex-agents pytest tests/contracts`. |

### Phase 1 — Fixtures, deterministic Markdown, parser, and scorer

| Field | Plan |
|---|---|
| Objective / owner / complexity | Make artifacts independently correct before UI/pipeline. **Backend** owns parser/scorer/generator; **Tester** adds tests after Backend stops writing those files; **large**. |
| Dependencies | Phase 0 frozen schemas/registry. |
| Affected paths | `apps/api/src/core/{registry,markdown,scoring,storage}.py`, `scripts/{generate_example_companies,validate_evaluations}.py`, `tests/fixtures/**`, `tests/{contracts,integration}/**`. |
| Outputs | Strict parser/serializer, scoring implementation, two complete generated fixture companies, validation CLI and parser/scoring tests. |
| Acceptance | Five validated files/company, all required IDs exactly once, generated aggregate has no hard-coded score, invalid artifacts are rejected without substitution. |
| Tests | `conda run -n codex-agents pytest apps/api/tests -k 'markdown or scoring'`; `python scripts/validate_evaluations.py tests/fixtures/companies`. |

### Phase 2 — Dashboard against deterministic fixture API

| Field | Plan |
|---|---|
| Objective / owner / complexity | Deliver dashboard usefulness before live uploads/council. **Backend** first adds read-only fixture/index routes; then **Frontend** owns dashboard and shared UI using `ui-ux-pro-max`; **large**. |
| Dependencies | Phase 1 fixture aggregate and API response schemas. |
| Affected paths | `apps/api/src/api/{companies,health}.py`, `apps/vc-dashboard/**`, `packages/ui/**`, dashboard tests. |
| Outputs | 8081 selector, sticky nav, Home, all category cards, score/unavailable states, restrained desktop styling. |
| Acceptance | Both fixtures selectable; every required question is rendered from API data; score remains attached; Home is excluded; no company mixing. |
| Tests | `pnpm --filter @sv/vc-dashboard test`; `pnpm --filter @sv/vc-dashboard typecheck`; Playwright dashboard fixture flow at both target resolutions. |

### Phase 3 — Secure submission and processing status

| Field | Plan |
|---|---|
| Objective / owner / complexity | Accept a valid founder submission safely and show honest asynchronous status. **Backend** owns request/storage/jobs, then **Frontend** owns portal using `ui-ux-pro-max`; **large**. |
| Dependencies | Phases 0–2 endpoint/error schemas and storage model. |
| Affected paths | `apps/api/src/{api/submissions.py,api/jobs.py,core/{uploads,storage,jobs}.py,workers/queue.py}`, `apps/founder-portal/**`, tests. |
| Outputs | 8080 two-card portal, multipart endpoint, idempotency/limits, persisted state machine, poll/retry UI. |
| Acceptance | Required pitch and CV-or-LinkedIn rule enforced client/server; files safely stored; failure/retry/identifier visible; no false-complete UI. |
| Tests | targeted pytest upload/job tests; portal Testing Library tests; Playwright CV/LinkedIn/error/retry flows. |

### Phase 4 — Document extraction and fact pipeline

| Field | Plan |
|---|---|
| Objective / owner / complexity | Convert stored submissions into cited facts/missing records. **Backend**; **large**. |
| Dependencies | Phase 3 storage/job artifacts and Phase 1 fact schema. |
| Affected paths | `apps/api/src/core/{pdf_extract,classify,facts}.py`, worker stages, provider fake, PDF fixtures/tests; `environment.yml`. |
| Outputs | native-first extraction/OCR fallback, document index, fact objects, provenance, partial extraction warnings. |
| Acceptance | No extracted claim lacks provenance; OCR only low-text pages; corrupt/scanned/OCR-unavailable cases remain observable and safe. |
| Tests | PDF/extraction/security pytest suites, fake-provider integration job up through council preparation. |

### Phase 5 — Bounded LLM Council and artifact publication

| Field | Plan |
|---|---|
| Objective / owner / complexity | Produce validated Markdown/aggregate from live submission facts. **Backend**; **large**. |
| Dependencies | Phases 1, 3, and 4. |
| Affected paths | `apps/api/src/{providers,core/{council,validation,publish}.py,workers}`, `prompts/*.md`, config, integration tests. |
| Outputs | provider adapters, Pro/Contra/Judge flow, one repair limit, deterministic serialization/reparse, atomic publication/indexing. |
| Acceptance | all five files/all IDs, cited fact/inference/missing distinctions, exact score handling/retries, final company appears on dashboard only at ready. |
| Tests | fake-provider Council contract tests, one-repair enforcement, full API upload-to-dashboard integration test; optional manually authorized live-provider smoke test. |

### Phase 6 — Integration, quality, documentation, and demo hardening

| Field | Plan |
|---|---|
| Objective / owner / complexity | Make the end-to-end local demo reproducible and assess high-risk behavior. **Tester** first test hardening; **Reviewer** then security/data-isolation review; **Documentary** updates external docs after behavior is stable; **medium**. |
| Dependencies | Phases 0–5 complete. |
| Affected paths | tests, `README.md`, `docs/{architecture,markdown-contract,operations}.md`, `scripts/{dev,reset_demo,reindex_companies}.py`; reviewers do not edit production code. |
| Outputs | full validation reports, reset/recovery runbook, setup/known-limits docs, review findings resolved by the owning Backend/Frontend agent if any. |
| Acceptance | local one-command demo, reset works only in explicit demo mode, two fixtures remain selectable, no unresolved high-severity reviewer finding. |
| Tests | all commands in section 25 plus a manual fresh-environment demo/restart/retry test. |

## 28. Agent task decomposition and file ownership

| Agent | Ownership / boundary | Must not change |
|---|---|---|
| Planner | `PLAN.md`, architecture, contract decisions, phase gates | Production code, fixtures, manifests after plan approval. |
| Explorer | Read-only repository/asset/code-path mapping when an unknown path exists | Any files. |
| Backend | `apps/api/**`, `prompts/**`, server-side scripts, Python tests, contract implementation after frozen schemas | `apps/founder-portal/**`, `apps/vc-dashboard/**`, visual UI package; cannot unilaterally change frozen contract schemas. |
| Frontend | `apps/founder-portal/**`, `apps/vc-dashboard/**`, `packages/ui/**`, web tests; use `ui-ux-pro-max` | Python API/core, fixture source facts, frozen contracts. |
| Tester | `tests/**`, test configs and test-only helpers after owners stop editing targets | Production behavior/contracts without an owner-approved defect report. |
| Reviewer | Read-only review of upload/PDF, data isolation, parser, scoring, Council, concurrency | All files unless explicitly assigned a review remediation. |
| Documentary | `README.md`, `docs/**` after stable external behavior | Application code/contracts. |

`packages/contracts/**`, root manifests, and `environment.yml` are a protected shared boundary: Planner freezes them in Phase 0; a single designated Backend owner changes them thereafter only with both consuming side test updates. No concurrent write-capable agent touches a shared boundary. The suggested execution sequence is Backend → Tester → Backend/Frontend (non-overlapping) → Tester → Reviewer → Documentary, with no more than one writer when ambiguity remains.

## 29. Acceptance criteria and definition of done

- [ ] `pnpm dev` starts portal 8080, dashboard 8081, API 8000; both desktop target resolutions are usable and logo remains visible.
- [ ] Portal supports required pitch, optional multi-PDF supporting docs, CV-or-LinkedIn, client/server validation, upload/status/failure/retry/identifier states.
- [ ] Pipeline performs every named stage, native extraction before OCR fallback, documents errors/retries/logs, and never treats it as one unstructured prompt.
- [ ] Exactly five versioned Markdown documents are generated per ready company; every registry question appears exactly once; all required evaluative scores are integer 1–100.
- [ ] Facts, inferences, and missing information are distinct and evidence-cited; no unavailable financial/founder/market claim is fabricated.
- [ ] Dashboard discovers/selects companies by slug; all five documents, every question, text/evidence/risk, and attached score render from selected API data only.
- [ ] Category averages and equal-weight overall derive centrally from valid scores; Home is excluded; unavailable/invalid scores are explicit and never normalized to 50.
- [ ] Invalid/malformed/duplicate/unknown Markdown behavior, one-repair limit, retry limits, and stale-good-output retention meet sections 11, 14, and 17.
- [ ] Path traversal, unsafe PDFs, injection, raw HTML, secret, PII, CORS, and cross-company controls have passed targeted tests.
- [ ] Two distinctive fictional fixture companies validate, demonstrate switching, and power parser/scoring/council/dashboard/isolation tests.
- [ ] Required test suites pass, documentation/setup/reset/recovery paths are current, and reviewer has no unresolved high-severity finding.

## 30. Risks, mitigations, and fallbacks

| Risk | Mitigation / fallback |
|---|---|
| `gpt-5.4-nano` unavailable or poor structured output | Verify at setup; model/provider is environment-configurable; use fake provider for all tests; switch one configuration value to approved available model and record it. |
| LLM latency/cost/failure during a demo | Async status, 30s call timeout, two transient retries, one manual job retry; demonstrate fixture companies if a live provider fails. |
| OCR host dependency absent | Detect at startup/stage; retain native pages, mark scanned pages missing with warning; do not pretend extraction succeeded. |
| PDF parsing exploit/resource exhaustion | strict size/page/type caps, no serving/execution, fail safely; use isolated process/AV scanning in production. |
| Single-process worker restart | persisted metadata/state conversion to retryable failure; reset/retry; production migration to durable queue/worker. |
| Markdown drift or model noncompliance | structured Judge output, deterministic serializer/reparser, registry/schema gates, one bounded repair, fixtures. |
| No portfolio inputs | score unavailable/provisional and excluded, never guessed; add validated local portfolio file later. |
| No authentication | local trusted-machine demo only; do not expose network port publicly. |
| Shared contract conflict | phase-0 freeze and one owner boundary; contract-version bump required for semantic changes. |

## 31. Approved proof-of-concept shortcuts

| Shortcut | Benefit | Limitation / demo risk | Production replacement |
|---|---|---|---|
| Local filesystem rather than database/object store | Transparent files and instant inspection/reset | One host, no concurrent/distributed durability | Postgres metadata + object storage with tenant access controls. |
| In-process queue + polling | Minimal operations and clear progress | Worker dies with API; no scale | Durable queue (Redis/Celery/Arq or managed queue) and worker deployment; optionally SSE. |
| No auth | Fast local walkthrough | Cannot accept real untrusted users | OIDC/SSO, RBAC, per-company authorization and audit. |
| Fixed max four supporting PDFs | Predictable demo cost/time | Not full document-management product | Configurable pagination/batch upload. |
| No automatic external research | Avoids web claims/cost/legal ambiguity | Market/competition analysis limited to supplied files | Licensed research connectors with provenance/consent. |
| Portfolio is absent by default | Avoids invented portfolio claims | Two Market criteria unavailable | Validated portfolio data and permissioned retrieval. |
| Tesseract fallback is optional | Smallest native-first PDF path | Scanned quality varies / host dependency | Isolated OCR service with language packs/quality monitoring. |
| Local reset token | Reliable repeatable demo | Destructive if misconfigured | Admin-only tenant-scoped retention/deletion tools. |

## 32. Demo strategy and reset procedure

Before a demo, create the Conda environment from `environment.yml`, install locked pnpm packages, copy `.env.example` to `.env`, configure a provider only if live processing is desired, run deterministic fixture generation/validation, then run `pnpm dev`. Start on the dashboard: select Aether Robotics and HarborLoop, show category cards, unavailable portfolio state, score derivation, and no mixed data. Then use the portal with a tiny synthetic pitch/CV (or LinkedIn route), observe queued stages and a fake/local-provider completion; a live provider is optional, not the sole demo path.

Recovery: use the dashboard fixtures if a provider/OCR fails; use the portal retry only after a failed job and only once. For a clean rehearsal, stop services and run the reset script with `SV_ENABLE_DEV_RESET=true` plus the reset token; it deletes only canonicalized configured demo-company roots, recreates the two fixture companies, validates them, reindexes, and prints affected slugs. The API reset endpoint is disabled by default and absent outside demo mode. Never run reset against a path not resolved under `data/companies`.

## 33. Deployment path after the hackathon

Keep the contracts, registry, Markdown serializer/parser, scorer, and UI API shapes. Replace local components incrementally: static frontend hosting/reverse proxy; FastAPI containers; Postgres for metadata/job/idempotency/index; encrypted object storage for source/evaluation artifacts; a durable worker queue; isolated malware/OCR workers; managed secrets; OIDC/RBAC/tenant authorization; encrypted retention/deletion/audit procedures; telemetry with PII redaction; rate limits and backups. Add a migration tool that imports each local company directory only after revalidating Markdown/schema/hash and maps `company_id`/slug without changing public URLs. Deploy read-only dashboard first, then authenticated submissions, and retain an export of filesystem data for rollback. Roll back API/UI independently while retaining versioned artifact readers; reject unsupported future schema versions rather than misreading them.

## 34. Genuine blocking questions

None block implementation of the local PoC. The following are deliberately resolved defaults that require product approval before a public/real-data deployment: the legal/privacy retention policy and founder consent text; approved LLM provider/model and spend limit; whether a real VC portfolio may be supplied and who owns it; authentication/authorized investor roles; and whether external research is permitted. Until resolved, local fixtures, trusted-machine usage, submitted-material-only analysis, and unavailable portfolio scoring are mandatory.
