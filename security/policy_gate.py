"""
Policy gate: enforces least-privilege agent permissions.
No single agent holds full authority over the pipeline.
"""

AGENT_PERMISSIONS: dict[str, set[str]] = {
    "IntentAgent": {
        "ParseIntent"
    },
    "PolicyAgent": {
        "ValidateQuery",
        "ApprovePolicy"
    },
    "GeoQueryAgent": {
        "ReadTerrain",
        "ReadTrails",
        "ReadHydrography",
        "BuildGeoQuery"
    },
    "RoutingAgent": {
        "ComputeRoute"
    },
    "SigningAgent": {
        "SignApprovedRoute"
    },
    "RenderingAgent": {
        "RenderVerifiedRoute",
        "RenderSuggestedRoute"
    }
}

# Operations that require explicit pre-conditions
GUARDED_OPERATIONS = {
    "SignApprovedRoute": ["operator_approved", "policy_valid"],
    "RenderVerifiedRoute": ["signature_valid"],
    "ComputeRoute": ["schema_valid"]
}


def allow(agent: str, operation: str, context: dict) -> dict:
    """
    Returns {"allowed": bool, "reason": str}.
    Checks both agent permission scope and operation pre-conditions.
    """
    allowed_ops = AGENT_PERMISSIONS.get(agent)

    if allowed_ops is None:
        return {
            "allowed": False,
            "reason": f"Unknown agent: {agent}"
        }

    if operation not in allowed_ops:
        return {
            "allowed": False,
            "reason": f"{agent} is not allowed to perform {operation}"
        }

    # Check pre-conditions for guarded operations
    required_context = GUARDED_OPERATIONS.get(operation, [])
    for key in required_context:
        if not context.get(key):
            label = key.replace("_", " ")
            return {
                "allowed": False,
                "reason": f"{label.capitalize()} required before {operation}"
            }

    return {
        "allowed": True,
        "reason": "Operation allowed"
    }


def describe_permissions(agent: str) -> dict:
    """Returns the full permission set for an agent."""
    ops = AGENT_PERMISSIONS.get(agent)
    if ops is None:
        return {"agent": agent, "known": False, "permissions": []}
    return {"agent": agent, "known": True, "permissions": sorted(ops)}


if __name__ == "__main__":
    import json

    print("--- IntentAgent tries to sign route (should be DENIED) ---")
    print(json.dumps(allow(
        agent="IntentAgent",
        operation="SignApprovedRoute",
        context={"operator_approved": True, "policy_valid": True}
    ), indent=2))

    print("\n--- SigningAgent signs with full approval (should be ALLOWED) ---")
    print(json.dumps(allow(
        agent="SigningAgent",
        operation="SignApprovedRoute",
        context={"operator_approved": True, "policy_valid": True}
    ), indent=2))

    print("\n--- SigningAgent signs WITHOUT operator approval (should be DENIED) ---")
    print(json.dumps(allow(
        agent="SigningAgent",
        operation="SignApprovedRoute",
        context={"operator_approved": False, "policy_valid": True}
    ), indent=2))

    print("\n--- RoutingAgent computes route without schema validation (should be DENIED) ---")
    print(json.dumps(allow(
        agent="RoutingAgent",
        operation="ComputeRoute",
        context={"schema_valid": False}
    ), indent=2))
