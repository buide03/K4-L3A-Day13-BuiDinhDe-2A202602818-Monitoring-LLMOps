# Repository Guidelines

## Purpose and Lab Workflow

This repository implements observability for a FastAPI and Langfuse-based mock LLM service. Work through the lab in checkpoint order: establish a baseline (CP0); implement correlation IDs, structured logs, and PII redaction (CP1); add traces, prompt versioning, dashboard, SLO, and alerts (CP2); investigate the private incident through **Metrics → Logs → Traces → Root Cause** (CP3); then finalize evidence and the report (CP4). Follow `docs/CHECKPOINTS.md` and `docs/RUBRIC.md`; do not replace real behavior with hardcoded validator output.

## Project Structure & Module Organization

- `app/`: API routes, middleware, agent, mock LLM/RAG, metrics, logging, PII, prompts, and tracing.
- `tests/`: pytest coverage for application behavior and configuration.
- `scripts/`: load generation, incident injection, and log/dashboard validators.
- `config/`: logging schema, dashboard, SLO, and alert definitions.
- `data/`: workload fixtures and generated local logs.
- `docs/`: setup, checkpoint, dashboard, prompt, and submission references.
- `submission/`: the report and its supporting evidence.

Keep route handlers small and place behavior in the matching module.

## Setup, Run, and Validation

Use Python 3.11+ from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env       # Windows: Copy-Item .env.example .env
uvicorn app.main:app --reload --env-file .env
```

With the API running, validate using:

```bash
python scripts/load_test.py
python scripts/validate_logs.py
python scripts/validate_dashboard.py
python -m pytest -q
```

The log validator target is at least 80/100; the dashboard must pass 6/6 panels.

## Coding and Testing Conventions

Use four-space indentation, type annotations, `snake_case` names for functions/variables, `PascalCase` classes, and uppercase constants. Group imports as standard library, third-party, then local. Use stable `snake_case` structlog events and scrub data before any sink or renderer. Name tests `test_<area>.py` and functions `test_<behavior>()`; cover every behavioral change, especially PII, request context, metrics, tracing, and prompt metadata.

## Security and Evidence Integrity

Never commit `.env`, API keys, raw PII, `.venv/`, generated `data/logs.jsonl`, or another student's evidence. `config/challenge.json` is private: never fabricate, share, or force-add it. Store evidence in `submission/evidence/` and reference it with relative links from `submission/REPORT.md`. Do not capture raw prompts or outputs containing PII in logs or traces.

## Commits and Pull Requests

Use short, imperative Conventional Commit subjects such as `fix: redact phone numbers` or `docs: update incident evidence`. Keep commits focused. Pull requests should summarize the affected checkpoint, list validation commands and results, link related issues, and include screenshots only for dashboard or Langfuse UI changes.
