.PHONY: help onboard catchup install install-crypto install-voice fmt lint test security shellcheck-syntax ci run run-https gen-cert tcpdump-demo audit-log demo-proofs inject-demo sign-bench demo eval clean protect-branch firewall firewall-remove firewall-status
.DEFAULT_GOAL := help

ifeq ($(OS),Windows_NT)
SHELL := C:/PROGRA~1/Git/bin/bash.exe
else
SHELL := /bin/bash
endif
.SHELLFLAGS := -eu -o pipefail -c

VENV := .venv
ifeq ($(OS),Windows_NT)
PY := py.exe -3.11
VENV_BIN := $(VENV)/Scripts
EXE := .exe
else
PY := python3.11
VENV_BIN := $(VENV)/bin
EXE :=
endif
PIP := $(VENV_BIN)/pip$(EXE)
PYTHON := $(VENV_BIN)/python$(EXE)
RUFF := $(VENV_BIN)/ruff$(EXE)
MYPY := $(VENV_BIN)/mypy$(EXE)
PYTEST := $(VENV_BIN)/pytest$(EXE)
BANDIT := $(VENV_BIN)/bandit$(EXE)
PIPAUDIT := $(VENV_BIN)/pip-audit$(EXE)

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

onboard: ## "I am Ben, get me ready to party." (interactive). Pass NAME=ben to skip prompt.
	@bash scripts/onboard.sh $(NAME)

catchup: ## Resume work after a sync break: pull main, refresh deps, summarize what changed
	@bash scripts/catchup.sh

$(VENV_BIN)/activate: pyproject.toml requirements-ci.txt ## Create venv if missing
	$(PY) -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-ci.txt
	$(PYTHON) -m pip install -e ".[dev]"

install: $(VENV_BIN)/activate ## Install core deps into venv (everyone runs this first)

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
	$(PYTHON) -m pip install -e ".[crypto]"
	@echo "[OK] crypto deps installed. You can now: make sign-bench"

install-voice: install ## Install Whisper + Piper deps. ONLY for Jon (P1).
	$(PYTHON) -m pip install -e ".[voice]"
	@echo "[OK] voice deps installed."

fmt: install ## Format code with ruff
	$(RUFF) format .
	$(RUFF) check --fix .

lint: install ## Lint with ruff + mypy (mypy only on populated lanes)
	$(RUFF) check .
	$(RUFF) format --check .
	@for d in agent routing crypto security; do \
		if [ -n "$$(find $$d -name '*.py' -type f 2>/dev/null)" ]; then \
			echo "$(MYPY) $$d --ignore-missing-imports --no-error-summary"; \
			$(MYPY) $$d --ignore-missing-imports --no-error-summary || exit 1; \
		else \
			echo "[mypy] skipping $$d (no .py files yet)"; \
		fi; \
	done

test: install ## Run pytest, including P2 security regressions
	$(PYTEST) -q -m "not slow" tests security crypto

security: install ## Bandit + pip-audit + optional gitleaks
	$(BANDIT) -r agent routing atak voice security crypto -ll -q
	$(PIPAUDIT) -r requirements-ci.txt --desc --fix --dry-run
	@if which gitleaks > /dev/null 2>&1; then \
		tmpdir="$$(mktemp -d)"; \
		git ls-files -z | tar --null -T - -cf - | tar -xf - -C "$$tmpdir"; \
		gitleaks detect --no-banner --redact --no-git --source "$$tmpdir"; \
		rm -rf "$$tmpdir"; \
	else \
		echo "[security] gitleaks not installed locally; GitHub Action still runs gitleaks"; \
	fi

ci: lint test security shellcheck-syntax ## Full CI gate (must pass before push)
	@echo "[OK] make ci passed"


shellcheck-syntax: ## bash -n parse-check on every committed shell script (catches typos like "diname")
	@echo "[shellcheck-syntax] parsing every *.sh under repo root..."
	@status=0; 	while IFS= read -r f; do 	  if bash -n "$$f" 2>&1; then 	    echo "  [ok] $$f"; 	  else 	    echo "  [FAIL] $$f"; status=1; 	  fi; 	done < <(find . -name '*.sh' -not -path './.venv/*' -not -path './node_modules/*' -not -path './.git/*'); 	if [ $$status -eq 0 ]; then echo "[OK] all shell scripts parse cleanly"; else exit $$status; fi

run: install ## Start the agent service on localhost only (HTTP, port 8000)
	PYTHONIOENCODING=utf-8 $(VENV_BIN)/uvicorn$(EXE) agent.app:app --host 127.0.0.1 --port 8000 --reload

gen-cert: ## Generate self-signed TLS cert for local HTTPS (run once, output to certs/)
	@bash infra/gen_dev_cert.sh

run-https: install gen-cert ## Start agent with HTTPS on localhost (port 8443)
	PYTHONIOENCODING=utf-8 $(VENV_BIN)/uvicorn$(EXE) agent.app:app \
		--host 127.0.0.1 --port 8443 \
		--ssl-keyfile certs/key.pem \
		--ssl-certfile certs/cert.pem \
		--reload

firewall: ## Block port 8000 from WiFi (Windows only). Run before `make run` on shared networks.
	@powershell -ExecutionPolicy Bypass -File infra/firewall_dev.ps1 add

firewall-remove: ## Remove the TERA port 8000 firewall block
	@powershell -ExecutionPolicy Bypass -File infra/firewall_dev.ps1 remove

firewall-status: ## Check if port 8000 firewall rule is active
	@powershell -ExecutionPolicy Bypass -File infra/firewall_dev.ps1 status

tcpdump-demo: ## Open tcpdump no-outbound monitor + audit log scroll for the security proof
	@bash infra/security_demo_monitors.sh

audit-log: ## Tail structured security audit events
	@bash infra/audit_log_scroll.sh

demo-proofs: ## Open 3-pane proof display: tcpdump + audit log + signed CoT (issue #15)
	@bash infra/security_demo_monitors.sh $(if $(INTERFACE),$(INTERFACE),)

inject-demo: install ## Demo pitch beat: unsigned CoT rejected, signed CoT accepted (issue, PRD §12 3:00-3:30)
	$(PYTHON) security/cot_inject_demo.py

sign-bench: install ## Sign + verify 1000 CoT round-trips, assert < 5 ms avg (issue #12)
	$(PYTHON) crypto/sign_bench.py

protect-branch: ## Lock main branch protection via GitHub API (GITHUB_TOKEN or gh auth)
	@bash infra/protect_branch.sh

demo: install ## Run the hero scenario end-to-end (lands by Sun 0500)
	@echo "make demo: not yet wired - will run hero scenario E2E by Sun 0500"
	@echo "stub: hitting /plan with sample prompt"
	@curl -s -X POST http://localhost:8000/plan \
	    -H 'Content-Type: application/json' \
	    -d '{"prompt": "route to nearest freshwater within 5km on foot covered terrain", "current": {"lat": 37.7955, "lon": -122.3937}}' | $(PYTHON) -m json.tool

eval: install ## Run the 20-prompt regression set
	$(PYTHON) -m eval.runner

clean: ## Remove venv and caches
	rm -rf $(VENV) .pytest_cache .ruff_cache .mypy_cache __pycache__
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
