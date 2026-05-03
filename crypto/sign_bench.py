"""ML-DSA / Ed25519-fallback sign+verify benchmark. Closes issue #12.

Usage:
    python crypto/sign_bench.py           # 1 000 round-trips
    python crypto/sign_bench.py 5000      # custom count
    make sign-bench                       # standard run via Makefile

Target (PRD §11.2): < 5 ms per round-trip on Jetson Orin Nano.
On a dev laptop this is usually < 1 ms (Ed25519 fallback) or < 2 ms (ML-DSA-65).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Allow `python crypto/sign_bench.py` from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto.ml_dsa_signer import _PQC_AVAILABLE, create_signer

# ---------------------------------------------------------------------------
# Benchmark payload — representative of a real CoT route payload.
# ---------------------------------------------------------------------------

SAMPLE_PAYLOAD = {
    "uid": "TERA-bench-0001",
    "lat": 37.7955,
    "lon": -122.3937,
    "route_hash": "a" * 64,
    "rationale": "Routed to Lobos Creek, distance 2.4 km, ETA 28 minutes on foot covered.",
    "mission_type": "search_and_rescue",
}

TARGET_MS = 5.0  # PRD §11.2 budget per round-trip


def run_bench(n: int = 1_000) -> None:
    algorithm = "ML-DSA-65 (liboqs)" if _PQC_AVAILABLE else "Ed25519-fallback"
    print(f"[sign-bench] algorithm : {algorithm}")
    print(f"[sign-bench] iterations: {n}")
    print()

    signer = create_signer("bench-key-001")

    # ---- warm-up (5 iterations, not counted) --------------------------------
    for _ in range(5):
        signed = signer.sign(SAMPLE_PAYLOAD)
        signer.verify(signed)

    # ---- timed run ----------------------------------------------------------
    t0 = time.perf_counter()
    failures = 0
    for i in range(n):
        signed = signer.sign(SAMPLE_PAYLOAD)
        ok = signer.verify(signed)
        if not ok:
            failures += 1
            print(f"  [FAIL] iteration {i} verify returned False")

    elapsed_s = time.perf_counter() - t0
    elapsed_ms = elapsed_s * 1_000
    avg_ms = elapsed_ms / n

    print(f"[sign-bench] total time : {elapsed_ms:.1f} ms for {n} round-trips")
    print(f"[sign-bench] avg / trip : {avg_ms:.3f} ms")
    print(f"[sign-bench] target     : < {TARGET_MS:.1f} ms")

    if failures:
        print(f"[sign-bench] FAIL — {failures} verification failure(s)")
        sys.exit(1)

    if avg_ms < TARGET_MS:
        print(f"[sign-bench] PASS  {avg_ms:.3f} ms < {TARGET_MS:.1f} ms target (OK)")
    else:
        print(
            f"[sign-bench] WARN  {avg_ms:.3f} ms exceeds {TARGET_MS:.1f} ms target. "
            "Check Jetson thermal state or liboqs build flags."
        )
        sys.exit(1)


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1_000
    run_bench(count)
