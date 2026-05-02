"""Route ontology: natural-language operator intent → RouteQuery JSON.

See ontology/route_ontology.yml for the WHERE / WHAT / HOW frame.
See ontology/system_prompt.md for the LLM template.
"""

from ontology.loader import build_system_prompt, load_ontology, load_route_query_schema

__all__ = ["build_system_prompt", "load_ontology", "load_route_query_schema"]
