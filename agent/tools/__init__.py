"""Tool registry: deterministic functions the orchestrator dispatches to
AFTER the security pipeline has approved a structured query.

The LLM does NOT call these directly. The orchestrator calls them based on
a deterministic translation from RouteQuery (Satriyo's schema) to tool args.
This is by design -- the LLM is sandboxed to JSON intent only.

Implementations are stubs in `stubs.py`; Ben fills in real Valhalla / OSM
calls in his lane.
"""

from agent.tools.stubs import find_pois, route, terrain_query

__all__ = ["find_pois", "route", "terrain_query"]
