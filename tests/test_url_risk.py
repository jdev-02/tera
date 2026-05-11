from __future__ import annotations

from integrations.security.url_risk import assess_url_risk, score_url_heuristics


def test_heuristic_flags_gov_impersonation() -> None:
    signals = score_url_heuristics("https://fema-aid-claim-example.com/login")

    codes = {signal.code for signal in signals}
    assert "GOV_IMPERSONATION" in codes
    assert "CRISIS_KEYWORDS" in codes


def test_heuristic_flags_url_shortener() -> None:
    signals = score_url_heuristics("https://bit.ly/fema-aid")

    assert any(signal.code == "URL_SHORTENER" for signal in signals)


def test_assess_url_risk_offline_mode_requires_approval() -> None:
    assessment = assess_url_risk(
        "https://fema-aid-claim-example.com/login",
        "wildfire relief donation link",
        use_live_providers=False,
    )

    assert assessment.risk_level in {"high", "critical"}
    assert assessment.requires_human_approval is True
    assert "safe_browsing_offline_mode" in assessment.skipped_sources
