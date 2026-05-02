# 00 — Team Standards (read by every agent, every task)

> Loaded after `AGENTS.md`. Codifies stack-level conventions.

## Stack (frozen at kickoff)

- **Python 3.11** (only). All Python files have `from __future__ import annotations` at the top.
- **FastAPI** for HTTP services. **uvicorn** as ASGI server.
- **structlog** for logging. **Never** use `print()` in committed code.
- **pytest** for tests. `pytest-asyncio` for async tests. **Never** use `unittest`.
- **pydantic v2** for data validation. All `/plan` request/response shapes are pydantic models.
- **ruff** for lint + format (one tool, fast). No `black` / `isort` / `flake8`.
- **mypy** for type checking; strict mode on `agent/`, `routing/`, `crypto/`.
- **httpx** for any *outbound* HTTP we do (Phase 1 only — frontier API). **Never** in Phase 3 paths.
- **`liboqs-python`** for ML-DSA / ML-KEM. Pinned to `0.10.0` in `pyproject.toml`.
- **`ollama`** Python client for local LLM in Phase 3. Frontier API client is `openai` for Phase 1.

## Style

- **Type hints required everywhere.** No `Any` without a comment explaining why.
- **No magic numbers.** Constants in `<lane>/constants.py` or in YAML config under `data/`.
- **Single responsibility.** A function does one thing. If you can't name it without "and", split it.
- **Guard clauses + early returns.** Avoid deep nesting.
- **Comments explain why, not what.** The code says what.
- **No TODOs in main.** Open an issue instead. `# TODO` in a PR diff fails CI.

## Logging

```python
import structlog
log = structlog.get_logger(__name__)

log.info("plan_request_received", request_id=req_id, prompt_len=len(prompt))
```

- Always include `request_id`.
- Never log secrets, full prompts that may contain location, or signing keys.

## Error handling

- Fail closed. On any exception in the `/plan` path, return a 503 with a generic error and log the full trace internally.
- Tool calls validate args before invocation. A schema-invalid tool call is a 400-class error from the agent's perspective (do not retry, do not loosen).

## Testing

- Every public function has at least one unit test.
- Every tool the agent can call has a happy-path and an error-path test.
- Mocks for external services (frontier API, Valhalla over network). **Never** hit real services in tests.
- `pytest -q` must complete in under 30 seconds locally. Slow tests get `@pytest.mark.slow` and run only in nightly.

## Files you must NOT touch without paired sign-off

- `/docs/contracts/agent_routing.schema.json` — change requires P1 + P4 sign-off.
- `/docs/contracts/cot_signed.md` — change requires P2 + P4 sign-off.
- `pyproject.toml` dependency additions — change requires P2 review (security/dep-audit).
- `Makefile`, `lefthook.yml`, `.github/workflows/ci.yml` — P2 owns.
- `AGENTS.md`, `/.agents/00-team.md`, `/.agents/10-architecture.md` — full-team review.

## Pre-push checklist (lefthook also enforces)

- [ ] `make fmt` (ruff format)
- [ ] `make lint` (ruff check + mypy)
- [ ] `make test` (pytest)
- [ ] `make security` (bandit + pip-audit + gitleaks)
- [ ] Commit message is conventional (`feat(scope): ...`)
- [ ] Branch name matches `<initials>/<short-desc>`
