.PHONY: install data zoo train test serve lint web demo

install:
	pip install -e ".[dev]"

data:
	bash scripts/download_data.sh

zoo:
	python -m trinetra.pipelines.zoo_benchmark

train:
	python -m trinetra.pipelines.train_ltfs

test:
	pytest -q

serve:
	uvicorn trinetra.api.app:app --reload --port 8091

lint:
	ruff check src tests

# Build the cockpit and serve the production bundle on http://localhost:4173.
# It calls the API on :8091, so run `make serve` in another shell (or `make demo`).
web:
	cd frontend && npm install && npm run build && npm run preview -- --port 4173

# One command for a judge: start the API in the background, build and serve the
# cockpit in the foreground, and stop the API on exit. API on :8091, cockpit on
# http://localhost:4173.
demo:
	@echo "Starting TRINETRA API on :8091 and cockpit on :4173 ..."
	@uvicorn trinetra.api.app:app --port 8091 & echo $$! > .demo-api.pid; \
	trap 'kill `cat .demo-api.pid` 2>/dev/null; rm -f .demo-api.pid' EXIT INT TERM; \
	cd frontend && npm install && npm run build && npm run preview -- --port 4173
