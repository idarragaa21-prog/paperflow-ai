.PHONY: install dev run test lint docker clean

VENV ?= .venv
PY = $(VENV)/bin/python

install:
	python3 -m venv $(VENV)
	$(PY) -m pip install -U pip
	$(PY) -m pip install -r requirements.txt

run:
	$(PY) -m uvicorn metaforge.api:app --host 127.0.0.1 --port 8000

dev:
	$(PY) -m uvicorn metaforge.api:app --reload --host 127.0.0.1 --port 8000

test:
	$(PY) -m pytest -q

example:
	$(PY) -m metaforge examples/doac_or.csv --out out

docker:
	docker compose up --build

clean:
	rm -rf $(VENV) .pytest_cache out **/__pycache__ *.egg-info
