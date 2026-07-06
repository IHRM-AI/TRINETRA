.PHONY: install data train test lint

install:
	pip install -e ".[dev]"

data:
	bash scripts/download_data.sh

train:
	python -m trinetra.pipelines.train_ltfs

test:
	pytest -q

serve:
	uvicorn trinetra.api.app:app --reload --port 8080

lint:
	ruff check src tests
