"""Tool registry: deterministic functions the orchestrator dispatches to
AFTER the security pipeline has approved a structured query.

The LLM does NOT call these directly. The orchestrator calls them based on
a deterministic translation from RouteQuery (Satriyo's schema) to tool args.
This is by design -- the LLM is sandboxed to JSON intent only.

Routing and terrain are still stubs; find_pois now reads local OSM SQLite
feature packages when present and falls back to the demo stub otherwise.
"""

from agent.tools.find_pois import find_pois
from agent.tools.stubs import route, terrain_query

__all__ = ["find_pois", "route", "terrain_query"]
