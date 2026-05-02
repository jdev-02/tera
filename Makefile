.PHONY: help onboard install install-crypto install-voice fmt lint test security ci run demo eval clean
.DEFAULT_GOAL := help

PY := python3.11
VENV := .venv
PIP := $(VENV)/bin/pip
PYTHON := $(VENV)/bin/python
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
PYTEST := $(VENV)/bin/pytest
BANDIT := $(VENV)/bin/bandit
PIPAUDIT := $(VENV)/bin/pip-audit

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

onboard: ## "I am Ben, get me ready to party." (interactive). Pass NAME=ben to skip prompt.
	@bash scripts/onboard.sh $(NAME)

$(VENV)/bin/activate: pyproject.toml ## Create venv if missing
	$(PY) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

install: $(VENV)/bin/activate ## Install core deps into venv (everyone runs this first)

install-crypto: install ## Install ML-DSA / liboqs deps. ONLY for Satriyo (P2). Requires `liboqs` system lib first.
	@if ! pkg-config --exists liboqs 2>/dev/null && [ ! -f /usr/local/lib/liboqs.dylib ] && [ ! -f /usr/local/lib/liboqs.so ] && [ ! -f /opt/homebrew/lib/liboqs.dylib ]; then \
		echo ""; \
		echo "ERROR: liboqs system library is not installed."; \
		echo ""; \
		echo "  macOS:           brew install liboqs"; \
		echo "  Ubuntu/Jetson:   bash infra/install_liboqs.sh"; \
		echo ""; \
		echo "After installing liboqs, run 'make install-crypto' again."; \
		exit 1; \
	fi
	$(PIP) install -e ".[crypto]"
	@echo "[OK] crypto deps installed. You can now: make sign-bench"

install-voice: install ## Install Whisper + Piper deps. ONLY for Jon (P1).
	$(PIP) install -e ".[voice]"
	@echo "[OK] voice deps installed."

fmt: install ## Format code with ruff
	$(RUFF) format .
	$(RUFF) check --fix .

lint: install ## Lint with ruff + mypy
	$(RUFF) check .
	$(RUFF) format --check .
	$(MYPY) agent routing crypto

test: install ## Run pytest (fast tests only)
	$(PYTEST) -q -m "not slow"

security: install ## Bandit + pip-audit + gitleaks
	@if [ ! -f $(BANDIT) ]; then echo "bandit missing; run 'make install' first"; exit 1; fi
	$(BANDIT) -r agent routing atak voice security -ll || true
	$(PIPAUDIT) --strict --skip-editable || true
	@if which gitleaks > /dev/null 2>&1; then \
		gitleaks detect --no-banner --redact --no-git || true; \
	else \
		echo "[security] gitleaks not installed (brew install gitleaks); skipping secret scan"; \
	fi

ci: lint test security ## Full CI gate (must pass before push)
	@echo "[OK] make ci passed"

run: install ## Start the agent service locally (stub)
	$(VENV)/bin/uvicorn agent.app:app --host 0.0.0.0 --port 8000 --reload

demo: install ## Run the hero scenario end-to-end (lands by Sun 0500)
	@echo "make demo: not yet wired \u2014 will run hero scenario E2E by Sun 0500"
	@echo "stub: hitting /plan with sample prompt"
	@curl -s -X POST http://localhost:8000/plan \
	    -H 'Content-Type: application/json' \
	    -d '{"prompt": "route to nearest freshwater within 5km on foot covered terrain", "current": {"lat": 37.7955, "lon": -122.3937}}' | $(PYTHON) -m json.tool

eval: install ## Run the 20-prompt regression set
	$(PYTHON) -m eval.runner

clean: ## Remove venv and caches
	rm -rf $(VENV) .pytest_cache .ruff_cache .mypy_cache __pycache__
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
