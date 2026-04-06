PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
PIP := $(VENV_PYTHON) -m pip
MGP_ADAPTER ?= memory

.PHONY: check-python install serve test test-all test-sdk test-integrations lint security build-sdk build-gateway docs docs-build docker-build

check-python:
	$(PYTHON) -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 'MGP requires Python 3.11+ for the reference gateway and docs toolchain.')"

install: check-python
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r reference/requirements.lock.txt -r compliance/requirements.lock.txt -r docs/requirements.lock.txt
	$(PIP) install -e reference -e sdk/python
	$(PIP) install ruff mypy pip-audit build pytest-asyncio pytest-cov types-PyYAML

serve:
	MGP_ADAPTER=$(MGP_ADAPTER) $(VENV)/bin/mgp-gateway --host 127.0.0.1 --port 8080

test:
	MGP_ADAPTER=$(MGP_ADAPTER) $(VENV_PYTHON) -m pytest compliance

test-all:
	MGP_ADAPTER=memory $(VENV_PYTHON) -m pytest compliance
	MGP_ADAPTER=file $(VENV_PYTHON) -m pytest compliance
	MGP_ADAPTER=graph $(VENV_PYTHON) -m pytest compliance

test-integrations:
	$(VENV_PYTHON) -m pytest integrations/nanobot/tests integrations/langgraph/tests integrations/minimal_runtime/tests

test-sdk:
	cd sdk/python && ../../$(VENV_PYTHON) -m pytest tests

lint:
	$(VENV_PYTHON) scripts/validate_schemas.py
	$(VENV_PYTHON) scripts/validate_openapi.py
	$(VENV_PYTHON) scripts/check_contract_drift.py
	$(VENV_PYTHON) -m ruff check adapters reference sdk/python integrations scripts
	$(VENV_PYTHON) -m mypy adapters reference sdk/python/mgp_client integrations scripts

security:
	$(VENV_PYTHON) -m pip_audit -r reference/requirements.lock.txt -r compliance/requirements.lock.txt -r docs/requirements.lock.txt

build-sdk:
	$(VENV_PYTHON) -m build sdk/python

build-gateway:
	$(VENV_PYTHON) -m build reference

docs-build:
	$(VENV_PYTHON) -m mkdocs build --strict

docs:
	$(VENV_PYTHON) -m mkdocs serve

docker-build:
	docker build -t mgp-reference-gateway .
