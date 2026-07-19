# Operations

## Local startup

1. Create and activate the Conda environment.
2. Install the pnpm workspace.
3. Start the stack with `pnpm dev`.

The root dev script launches:

- API on `8000`
- founder portal on `8080`
- VC dashboard on `8081`

Open `http://localhost:8000/` for the API entry point, `http://localhost:8000/health` for a health check, or `http://localhost:8000/docs` for interactive API documentation.

## Local environment variables

The API reads the environment keys listed in `packages/config/src/index.ts`. The most relevant ones are:

- `SV_DATA_ROOT`
- `SV_ALLOWED_ORIGINS`
- `SV_MAX_FILE_BYTES`
- `SV_MAX_AGGREGATE_FILE_BYTES`
- `SV_OCR_ENABLED`
- `SV_OCR_TEXT_THRESHOLD`
- `SV_LLM_PROVIDER`
- `SV_LLM_MODEL`
- `SV_LLM_TIMEOUT_SECONDS`
- `SV_LLM_MAX_OUTPUT_TOKENS`
- `SV_ENABLE_DEV_RESET`
- `SV_DEMO_RESET_TOKEN`

## Data persistence

Submission data is stored on the local filesystem under the configured data root. Each company gets its own slugged directory with:

- `source/` for uploaded PDFs
- `extracted/` for derived extraction artifacts
- `evaluation/` for generated Markdown evaluations
- `logs/` for job logs
- `metadata.json` for the job and company record

The API writes files atomically and keeps file access scoped to the resolved company root.

## Safe recovery

If a worker run is interrupted, the repository marks the job as failed and retryable when it next loads the persisted metadata. A manual retry endpoint is available for failed jobs that still allow retry.

If a valid evaluation already exists, the dashboard continues to read the last successful company record from the read-only company APIs.

If the fixture index is damaged or a file hash changes, the read-only company endpoints return an index error instead of serving the corrupted artifact.

## Known gaps

- No authentication is implemented.
- No production database is used.
- No distributed queue is used.
- No reset or reindex endpoint is exposed in the API.
- The project is intended for local use and trusted operators.

## Validation commands

Use the smallest relevant command first, then the broader suite:

```bash
pnpm --filter @sv/contracts test
pnpm --filter @sv/founder-portal test
pnpm --filter @sv/vc-dashboard test
pnpm test:web
pnpm test:contracts
pnpm test
pnpm test:e2e
conda run -n codex-agents pytest
```
