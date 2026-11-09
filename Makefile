# Short commands for the whole project.  Run `make help` to see them.
.PHONY: help setup sample lint test run all notebook clean hooks

help:
	@echo "make setup     install the Python packages"
	@echo "make sample    create fake data/events.csv (use your real file instead if you have it)"
	@echo "make lint      check the code with ruff"
	@echo "make test      run the automated tests"
	@echo "make run       run the whole pipeline"
	@echo "make all       lint + test + run"
	@echo "make hooks     turn on the git pre-commit checks"
	@echo "make clean     delete generated files"

setup:
	pip install -r requirements-dev.txt

sample:
	python scripts/generate_sample_data.py --sessions 6000 --out data/events.csv

lint:
	ruff check .

test:
	pytest

run:
	python -m src.run_pipeline --input data/events.csv --output outputs --reports reports

all: lint test run

hooks:
	pre-commit install

clean:
	rm -rf outputs spark-warehouse .pytest_cache .ruff_cache
