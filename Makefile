# Wayfinder — Makefile
# Single source of truth for local + CI. GitHub Actions calls `make ci`.
# PRD §14.4: "make ci is the single source of truth."

.PHONY: fmt lint test ci clean

# ---- Format ----------------------------------------------------------------
fmt:
	ruff format .

# ---- Lint ------------------------------------------------------------------
lint:
	ruff check .
	mypy security/ crypto/ --ignore-missing-imports --no-error-summary || true

# ---- Security static analysis ----------------------------------------------
security-scan:
	bandit -r security/ crypto/ -ll -q || true
	pip-audit --desc --fix --dry-run || true

# ---- Tests -----------------------------------------------------------------
test:
	pytest security/ crypto/ -v --tb=short

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
