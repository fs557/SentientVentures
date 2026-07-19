# Architecture

## Runtime layout

SentientVentures currently runs as a local monorepo with three runtime targets:

- `apps/api`: FastAPI service on port `8000`
- `apps/founder-portal`: Vite React app on port `8080`
- `apps/vc-dashboard`: Vite React app on port `8081`

The two web apps both consume the shared contract package `@sv/contracts` and the shared UI package `@sv/ui`.

## Repository structure

- `apps/api`: upload handling, persistence, extraction, scoring, evaluation publication, and read-only company APIs
- `apps/founder-portal`: submission form and processing-status view
- `apps/vc-dashboard`: company selector and evaluation views
- `packages/contracts`: generated TypeScript contract types plus the JSON Schemas used by the API and tests
- `packages/ui`: shared presentation components
- `packages/config`: server-side environment key list and shared defaults
- `tests/fixtures/companies`: deterministic read-only fixture companies used by the API and dashboard

## API behavior

The FastAPI app exposes:

- `GET /health`
- `GET /api/v1/companies`
- `GET /api/v1/companies/{slug}`
- `GET /api/v1/companies/{slug}/categories/{category}`
- `POST /api/v1/submissions`
- `GET /api/v1/jobs/{slug}`
- `POST /api/v1/jobs/{slug}/retry`

Responses use a fixed error envelope with `requestId`. CORS is limited to the configured local origins by default.

## Submission flow

The founder portal submits a multipart form with:

- company name
- founder name
- founder email
- a required pitch-deck PDF
- either a CV PDF or a LinkedIn HTTPS URL
- optional GitHub and website URLs
- up to four optional supporting PDFs

The API stores uploads on disk under a slugged company directory, records a queued job, and returns a company slug plus job URL.

## Processing flow

The worker processes a submission in stages:

1. validating
2. extracting
3. classifying
4. fact extracting
5. council preparation
6. council
7. output validation
8. publishing

Current behavior is local and in-process:

- files are kept on the filesystem
- PDFs are extracted with native text first
- OCR is only used as a fallback where configured and available
- processing artifacts are written under the company directory
- completed evaluations are swapped into place atomically

If the worker starts without a provider, it stops at council preparation and leaves the job unfinished rather than fabricating an evaluation.

## Dashboard behavior

The dashboard loads the read-only company index from the API, then fetches one company evaluation at a time by slug. It checks that the response slug matches the selected slug before rendering the data.

The dashboard currently renders:

- the shared navbar
- the company selector
- the category navigation
- the home summary view
- the per-category criterion cards

## Shared contracts

`packages/contracts/schema` contains the versioned JSON Schemas for:

- common shapes
- API envelopes
- evaluation documents
- scoring vectors
- the question registry

`packages/contracts/src/generated.ts` is the TypeScript surface consumed by the apps.

## Current limitations

- There is no production database.
- There is no distributed queue.
- There is no authentication.
- The system is intended for local use.
- The live model/provider path is configured in code, but test fixtures and deterministic local behavior remain the primary supported path.
