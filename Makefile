PY ?= python
export PYTHONPATH := src

.PHONY: all ingest run test
all: ingest run
ingest:
	$(PY) -m cgy.ingest
run:
	$(PY) -m cgy.pipeline
test:
	$(PY) -m pytest -q tests
