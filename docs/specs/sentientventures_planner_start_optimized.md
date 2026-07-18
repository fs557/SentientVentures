# SentientVentures — Planner Run

You are the parent orchestration thread. This run is planning-only.

## Orchestration rules

1. Spawn exactly one project-scoped custom agent named `planner`.
2. The parent thread must not edit repository files.
3. The `planner` is the only writer and may modify only `PLAN.md`.
4. Do not spawn Explorer, Backend, Frontend, Tester, Reviewer, or Documentary during this run.
5. Wait for the planner to finish, then inspect `PLAN.md` against the acceptance checklist below.
6. If the plan is materially incomplete, send the same planner one bounded repair request listing only the missing items. Allow at most one repair pass.
7. Stop after the planning deliverable. Do not begin implementation.

## Task for the planner

Read, in this order:

1. `AGENTS.md`
2. `.codex/config.toml`
3. `.codex/agents/planner.toml`
4. `docs/specs/sentientventures-poc.md`
5. the current `PLAN.md`
6. the remaining repository tree and any relevant specifications or assets

Treat `docs/specs/sentientventures-poc.md` as the authoritative product specification. Treat the repository as greenfield unless working source code proves otherwise. Do not infer that a route, application, API, parser, model workflow, asset, or data store exists merely because the specification mentions it.

Create a decisive, implementation-ready `PLAN.md` for the complete SentientVentures proof of concept.

### Planning behavior

- Make reasonable technical decisions instead of leaving non-blocking choices open.
- Record only questions that genuinely prevent implementation.
- Prefer the simplest architecture that can reliably demonstrate the end-to-end workflow locally.
- Keep a clear upgrade path, but do not introduce production infrastructure that the hackathon demo does not need.
- Explicitly separate required product behavior from approved proof-of-concept shortcuts.
- Every shortcut must state its benefit, limitation, demo risk, and later production replacement.
- Do not use vague language such as “implement as needed,” “consider using,” or “choose a suitable library.” Select concrete defaults and explain major trade-offs.
- Do not implement production code, create large source files, generate the example-company fixtures, or alter configuration. Small schemas, interfaces, directory trees, state diagrams, and pseudocode are allowed only when they remove ambiguity.

### Required architectural decisions

The plan must explicitly choose and justify:

- monorepo and package-management strategy
- frontend framework and build tooling for ports 8080 and 8081
- backend framework and port
- shared UI, types, schema, scoring, and configuration packages
- local orchestration command
- filesystem storage and company isolation strategy
- upload and safe-filename behavior
- PDF text extraction with native extraction first and OCR only as a fallback for scanned pages
- normalized fact model
- canonical question registry
- deterministic Markdown contract and parser strategy
- schema-validation library
- job execution and status-polling strategy
- LLM provider abstraction and centrally configurable model IDs
- bounded Pro → Contra → Judge → deterministic validation → optional single repair workflow
- score calculation and missing/invalid-score behavior
- logging, error handling, retry, timeout, and idempotency behavior
- secrets and environment configuration
- unit, integration, contract, parser, security, and end-to-end test strategy
- fixture and example-company generation strategy
- demo reset and recovery strategy
- post-hackathon deployment path

### Contracts that must be unambiguous

Define concrete contracts for:

- company identifiers and slugs
- company directory layout
- source-document metadata
- extracted fact records, including `fact`, `inference`, and `missing_information`
- canonical question IDs and registry versioning
- Markdown front matter and criterion sections
- normalized evaluation items and documents
- category and overall score calculations
- upload request and response shapes
- processing job states and allowed transitions
- company index and dashboard-loading responses
- validation errors and one-pass repair requests
- cross-company isolation boundaries

For each API endpoint, include method, route, request, success response, failure response, validation rules, and idempotency expectations.

### Implementation plan requirements

Use ordered phases with dependency boundaries. For every phase include:

- objective
- owning agent
- dependencies
- affected files or directories
- expected outputs
- acceptance criteria
- tests and validation commands
- complexity: small, medium, or large

Assign one write-capable agent at a time unless file ownership is clearly disjoint and interfaces are already frozen. Include a file-ownership or change-boundary table so Backend and Frontend agents do not overwrite shared contracts independently.

The first phases must freeze contracts and fixtures before UI or processing implementation. The dashboard should render deterministic fixture data before the upload and LLM pipeline is connected. The final phases must cover integration, review, documentation, and demo hardening.

### Required `PLAN.md` structure

The completed plan must contain:

1. Executive summary
2. Confirmed assumptions
3. Explicit non-goals
4. Repository findings and current-state evidence
5. Chosen technology stack
6. Complete architecture
7. End-to-end data flow
8. Complete target directory structure
9. Company storage and isolation model
10. Canonical question registry
11. Canonical Markdown contract
12. Normalized internal data model
13. API contracts
14. Processing-job state machine
15. LLM Council design
16. Prompt responsibilities and injection defenses
17. Validation and single-repair strategy
18. Scoring rules
19. Frontend component hierarchy
20. Founder Portal structure on port 8080
21. VC Dashboard structure on port 8081
22. Company selection and data-isolation behavior
23. Configuration and secrets
24. Security and privacy considerations
25. Testing strategy and required fixtures
26. Example-company strategy
27. Implementation phases
28. Agent task decomposition and file ownership
29. Acceptance criteria and definition of done
30. Risks, mitigations, and fallbacks
31. Approved proof-of-concept shortcuts
32. Demo strategy and reset procedure
33. Deployment path after the hackathon
34. Genuine blocking questions

### Acceptance checklist for the parent thread

Before ending the run, verify that `PLAN.md`:

- selects concrete technologies rather than listing alternatives
- contains every required section above
- covers every required question category from the product specification
- defines stable question IDs and a deterministic Markdown grammar
- defines invalid-score, missing-data, duplicate-question, and malformed-file behavior
- defines exact job states and retry limits
- keeps Home out of the overall score by default
- forbids invented facts and distinguishes fact, inference, and missing information
- includes prompt-injection, PDF, path-traversal, sanitization, secret, PII, and company-isolation controls
- includes all required parser, scoring, submission, dashboard, isolation, and council tests
- assigns clear owners and change boundaries to agents
- includes no production implementation

## Final response

After `PLAN.md` is complete, return only a concise summary of:

- selected stack and architecture
- central contracts
- Markdown and scoring strategy
- council workflow
- implementation phases
- approved demo shortcuts
- largest risks
- genuine remaining product decisions
