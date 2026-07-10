.PHONY: install data zoo train test serve lint

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
