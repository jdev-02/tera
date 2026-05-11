from __future__ import annotations

from integrations.security import safe_browsing


def test_build_safe_browsing_request() -> None:
    req = safe_browsing.build_safe_browsing_request(["https://example.com"])

    assert req["threatInfo"]["platformTypes"] == ["ANY_PLATFORM"]
    assert "SOCIAL_ENGINEERING" in req["threatInfo"]["threatTypes"]
    assert req["threatInfo"]["threatEntries"] == [{"url": "https://example.com"}]


def test_normalize_safe_browsing_match_response() -> None:
    raw = {
        "matches": [
            {
                "threatType": "SOCIAL_ENGINEERING",
                "threat": {"url": "https://fake-fema.example/login"},
            }
        ]
    }

    results = safe_browsing.normalize_safe_browsing_response(
        raw,
        ["https://fake-fema.example/login"],
    )

    assert results[0].checked is True
    assert results[0].matched is True
    assert results[0].threat_types == ["SOCIAL_ENGINEERING"]


def test_normalize_safe_browsing_no_match_response() -> None:
    results = safe_browsing.normalize_safe_browsing_response({}, ["https://www.fema.gov/"])

    assert results[0].checked is True
    assert results[0].matched is False


def test_safe_browsing_missing_key_fallback(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_SAFE_BROWSING_API_KEY", raising=False)

    results = safe_browsing.check_url_threats(["https://example.com"])

    assert results[0].checked is False
    assert results[0].raw == {"skipped": "missing_api_key"}
