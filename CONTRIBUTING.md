# Contributing to TRINETRA

Thanks for your interest in improving TRINETRA. This guide covers local setup,
testing, linting, and the pull-request conventions used in this repository.

## Setup

Requires Python 3.10+ and Node 20+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # backend + dev tools (pytest, pytest-cov, ruff, mypy)
cp .env.example .env             # optional; fill in self-hosted endpoints when a GPU is running

cd frontend && npm install       # cockpit
```

Datasets are public but not redistributed. Run `bash scripts/download_data.sh`
(needs a Kaggle API token) to fetch them, then `make train` to produce the
segment artifact. The test suite does not require the datasets or a trained
artifact — it builds small in-memory models.

## Testing

```bash
make test        # pytest with coverage; fails below 85% line coverage
```

Coverage is measured over the served API and modelling library (the config in
`pyproject.toml` omits the offline-untestable data loaders, training pipelines,
and external GenAI clients). If you add code to a covered module, add tests so
the gate stays green; if you add a new offline-untestable integration, extend
the `[tool.coverage.run] omit` list with a short justification.

## Linting

```bash
make lint        # ruff check src tests
```

Backend code must pass `ruff check src tests` with no warnings. Frontend code
must pass `npx tsc -b --noEmit` from the `frontend/` directory. Both run in CI.

## Code conventions

- No filler comments and no emoji. Comments should explain non-obvious intent,
  not restate the code.
- Keep changes to the served API backward-compatible with the running demo:
  new hardening (auth, CORS, validation) must default to the current working
  behaviour and tighten only when an environment variable opts in.
- Do not commit secrets. Secrets live in `.env` (git-ignored); see `SECURITY.md`.
- Do not commit datasets or build output (`dist/`, coverage files) — these are
  git-ignored.

## Pull requests

- Branch from `main`; keep each PR focused on one change.
- Write clear, imperative commit messages that state what changed and why.
- Ensure `make test` and `make lint` pass locally before opening the PR; CI runs
  both plus the frontend type-check.
- Update the README, model card, or other docs when behaviour or metrics change.
- Reference any related issue in the PR description.

## Reporting security issues

Please report security vulnerabilities privately as described in `SECURITY.md`,
not via public issues or pull requests.
