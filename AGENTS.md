
---

# 12. `AGENTS.md`

Codex liest `AGENTS.md` zu Beginn eines Laufs und verwendet es als dauerhafte Projektanweisung. Dateien in tieferen Projektordnern können die Regeln für einzelne Teilbereiche überschreiben. :contentReference[oaicite:12]{index=12} Project Guidance

## Objective

Build maintainable software with clear contracts, focused changes,
verifiable behavior, and restrained use of Codex subagents.

## Project conventions

- Backend language: Python 3.11 or the version selected in PLAN.md.
- Frontend and shared web packages: TypeScript using the version selected in PLAN.md.
- Do not force frontend functionality into Python merely because the backend uses Python.
- Follow the existing architecture and naming conventions before
  introducing new ones.
- Keep secrets out of source code, logs, tests, and documentation.
- Prefer small, reviewable changes over broad rewrites.
- Do not add a production dependency unless it is necessary and justified.
- Treat `environment.yml` as the environment source of truth.
- If the repository also contains `requirements.txt` or another lock file,
  keep the declared dependencies consistent.
- Do not modify unrelated files merely to improve formatting or style.

## Validation

- Run the smallest relevant checks first.
- For Python changes, use the project's existing formatter, linter,
  type checker, and pytest configuration.
- Never claim that a command passed unless it was actually executed.
- Report commands that were run.
- Report validation that could not be completed.
- Do not suppress failing tests merely to complete the task.

## Subagent policy

Use subagents only when delegation materially improves quality or keeps
noisy work out of the main thread.

### Small isolated change

Use the main agent only.

Examples:

- correcting a label
- changing one validation condition
- fixing a small CSS issue
- updating one configuration value

### Unknown code path

Delegate read-only mapping to `explorer`.

### Non-trivial cross-component feature

Ask `planner` for a bounded implementation plan.

### Backend implementation

Delegate a clearly scoped task to `backend`.

### Frontend implementation

Delegate a clearly scoped task to `frontend`.

The frontend agent must use the `ui-ux-pro-max` skill for design or UI
implementation work.

### Testing

Use `tester` after implementation.

Testing may run in parallel only when the tester and implementation agent
will not edit the same files.

### Documentation

Use `documentary` only when one of the following changed:

- public behavior
- setup instructions
- public API
- configuration
- migration process
- externally relevant limitations

### Review

Use `reviewer` only for:

- authentication or authorization changes
- file uploads
- database migrations
- user or confidential data
- concurrency
- networking or external integrations
- larger refactorings
- substantial pull requests
- changes with difficult rollback behavior

## Parallelism

Do not start all agents automatically.

Prefer at most one write-capable implementation agent at a time.

Parallelize:

- read-only exploration
- review
- log analysis
- independent test execution
- documentation research

Parallel write-heavy work is allowed only when:

- file ownership is clearly disjoint
- interfaces are already fixed
- neither agent needs to rewrite the other's output

## Definition of done

A task is complete when:

1. The requested behavior is implemented.
2. Relevant tests or checks have passed.
3. Important edge cases and failure paths were considered.
4. Unrelated files were not changed.
5. Documentation was updated when required.
6. Remaining risks or unverified assumptions are stated clearly.