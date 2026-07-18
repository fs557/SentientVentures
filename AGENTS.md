# Project Guidelines

## Tech Stack & Environment
- **Environment:** Everything must run seamlessly within the `codex-agents` Conda environment.
- **Language:** Primary programming language is Python for both Backend and Frontend.
- **Dependencies:** Keep `environment.yml` and `requirements.txt` strictly synchronized.

## Design Language (Frontend)
- **Style:** "Frosted Touch" (Glassmorphism) with semi-transparent backgrounds and modern blur effects.
- **Vibe:** Ultra-modern, dark/monochromatic with high-contrast accents, minimalist—resembling the Tesla UI.
- **Consistency:** Always utilize the loaded skill `ui-ux-pro-max` for UI/UX implementation.

## Workflow & Collaboration
1. **Planning First:** No code shall be written before the `@planner` creates an architectural layout (e.g., in `PLAN.md`).
2. **Test-Driven Development:** The `@tester` must verify all code via `pytest` before a feature is marked as completed.
3. **Documentation:** The `@documentary` agent ensures clean docstrings, proper type hinting, and an up-to-date README.