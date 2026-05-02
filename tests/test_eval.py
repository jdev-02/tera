"""Tests for the eval harness scaffolding (issue #21)."""

from __future__ import annotations

from eval.runner import (
    PASS_THRESHOLD,
    load_eval_entries,
    run_mock_mode,
    validate_against_schema,
)


def test_eval_loads_at_least_20_entries() -> None:
    entries = load_eval_entries()
    assert len(entries) >= 20, f"expected ≥20 prompts, got {len(entries)}"


def test_eval_entries_have_required_fields() -> None:
    entries = load_eval_entries()
    for e in entries:
        assert "id" in e, f"entry missing id: {e}"
        assert "utterance" in e, f"entry {e['id']} missing utterance"
        # expected_query may be None for adversarial entries; that's OK.


def test_eval_ids_are_unique() -> None:
    entries = load_eval_entries()
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids)), f"duplicate ids: {ids}"


def test_all_non_adversarial_entries_pass_schema() -> None:
    """Every entry with an expected_query must validate against the RouteQuery
    schema. If the schema changes, the eval set must be updated to match."""
    entries = load_eval_entries()
    for e in entries:
        if e.get("expected_query") is None:
            continue  # adversarial; pipeline blocks instead
        errors = validate_against_schema(e["expected_query"])
        assert not errors, f"entry {e['id']!r} fails schema: {errors}"


def test_run_mock_mode_at_threshold() -> None:
    """The mock-mode runner returns >= 90% pass rate. This is what CI checks."""
    passed, total, failures = run_mock_mode()
    assert total > 0
    pass_rate = passed / total
    assert pass_rate >= PASS_THRESHOLD, (
        f"eval pass rate {pass_rate:.0%} below threshold {PASS_THRESHOLD:.0%}; failures: {failures}"
    )


def test_prd_demo_scenarios_present() -> None:
    """The three hero prompts MUST be in the eval set with the right ids."""
    entries = load_eval_entries()
    ids = {e["id"] for e in entries}
    assert {"prd_a_freshwater_hero", "prd_b_covered_foot_grid", "prd_c_vehicle_mrap"} <= ids
