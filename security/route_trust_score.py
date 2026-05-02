"""
Computes the trust score for a route artifact before it reaches ATAK rendering.
A route that hasn't passed all checks must never appear as "Trusted Route" on the map.
"""


def compute_route_trust(route_artifact: dict) -> dict:
    """
    Returns:
      trust_score  : 0–100
      trust_status : "trusted" | "needs_review" | "untrusted"
      reasons      : list of failure reasons (empty when fully trusted)

    Expected keys in route_artifact:
      schema_valid             bool  — query passed schema validation
      policy_valid             bool  — policy gate approved
      operator_approved        bool  — human operator confirmed
      signature_valid          bool  — cryptographic route signature present
      untrusted_inputs_used    bool  — route used map labels / overlays as input
      superagent_guard_passed  bool  — SuperAgent Guard found no injection (optional)
    """
    score = 100
    reasons = []

    checks = [
        ("schema_valid", 30, "Structured query schema invalid"),
        ("policy_valid", 30, "Policy validation failed"),
        ("operator_approved", 20, "Operator approval missing"),
        ("signature_valid", 30, "Route signature missing or invalid"),
    ]

    for key, penalty, message in checks:
        if not route_artifact.get(key):
            score -= penalty
            reasons.append(message)

    # Low-trust input sources add a separate penalty
    if route_artifact.get("untrusted_inputs_used"):
        score -= 25
        reasons.append("Route used low-trust input sources")

    # SuperAgent Guard bonus/penalty — only applied when key is present
    if (
        "superagent_guard_passed" in route_artifact
        and not route_artifact["superagent_guard_passed"]
    ):
        score -= 40
        reasons.append("SuperAgent Guard detected prompt injection in input")

    score = max(0, score)

    if score >= 80:
        status = "trusted"
    elif score >= 50:
        status = "needs_review"
    else:
        status = "untrusted"

    return {"trust_score": score, "trust_status": status, "reasons": reasons}


ATAK_DISPLAY_MAP = {
    "trusted": "Trusted Route",
    "needs_review": "Suggested Route – Needs Review",
    "untrusted": "Untrusted – Do Not Execute",
}


def atak_label(trust_result: dict) -> str:
    return ATAK_DISPLAY_MAP.get(trust_result["trust_status"], "Unknown Trust State")


if __name__ == "__main__":
    import json
    from typing import Any

    scenarios: list[dict[str, Any]] = [
        {
            "name": "Fully trusted route (SuperAgent guard passed)",
            "artifact": {
                "schema_valid": True,
                "policy_valid": True,
                "operator_approved": True,
                "signature_valid": True,
                "untrusted_inputs_used": False,
                "superagent_guard_passed": True,
            },
        },
        {
            "name": "Missing approval and signature",
            "artifact": {
                "schema_valid": True,
                "policy_valid": True,
                "operator_approved": False,
                "signature_valid": False,
                "untrusted_inputs_used": False,
                "superagent_guard_passed": True,
            },
        },
        {
            "name": "Injection detected by SuperAgent Guard",
            "artifact": {
                "schema_valid": True,
                "policy_valid": True,
                "operator_approved": True,
                "signature_valid": True,
                "untrusted_inputs_used": False,
                "superagent_guard_passed": False,
            },
        },
        {
            "name": "Multiple failures (no guard key = legacy mode)",
            "artifact": {
                "schema_valid": False,
                "policy_valid": False,
                "operator_approved": False,
                "signature_valid": False,
                "untrusted_inputs_used": True,
            },
        },
    ]

    for s in scenarios:
        result = compute_route_trust(s["artifact"])
        print(f"\n=== {s['name']} ===")
        print(json.dumps(result, indent=2))
        print(f"ATAK display: {atak_label(result)}")
