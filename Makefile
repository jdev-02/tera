# Wayfinder — Makefile
# Single source of truth for local + CI. GitHub Actions calls `make ci`.
# PRD §14.4: "make ci is the single source of truth."

.PHONY: fmt lint security-scan test ci clean

# ---- Format ----------------------------------------------------------------
fmt:
	python -m ruff format .

# ---- Lint ------------------------------------------------------------------
lint:
	python -m ruff check .
	python -m mypy security/ crypto/ --ignore-missing-imports --no-error-summary

# ---- Security static analysis ----------------------------------------------
security-scan:
	python -m bandit -r security/ crypto/ -ll -q
	python -m pip_audit -r requirements-ci.txt --desc --fix --dry-run

# ---- Tests -----------------------------------------------------------------
test:
	python -m pytest security/ crypto/ -v --tb=short

# ---- CI (mirrors GitHub Actions exactly) -----------------------------------
ci: fmt lint security-scan test
	@echo ""
	@echo "=============================="
	@echo "  make ci PASSED"
	@echo "=============================="

# ---- Clean -----------------------------------------------------------------
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
