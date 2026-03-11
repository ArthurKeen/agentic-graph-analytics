"""
Graph & connection tools.

Tools:
  - get_connection_info   – return current ArangoDB connection details
  - list_graphs           – list named graphs in the configured database
  - describe_graph        – vertex + edge collections for a named graph
  - analyze_schema        – full SchemaExtractor + SchemaAnalyzer run
"""

from typing import Optional

from graph_analytics_ai.db_connection import get_db_connection  # noqa: F401 – imported for patching
from ..server import mcp


# ---------------------------------------------------------------------------
# get_connection_info
# ---------------------------------------------------------------------------
@mcp.tool()
def get_connection_info() -> dict:
    """Return ArangoDB connection details (endpoint, database, user).

    Does NOT return the password. Useful for confirming which cluster the
    server is connected to.
    """
    from graph_analytics_ai.db_connection import get_connection_info as _get_info

    return _get_info()


# ---------------------------------------------------------------------------
# list_graphs
# ---------------------------------------------------------------------------
@mcp.tool()
def list_graphs() -> list:
    """List all named graphs in the configured ArangoDB database.

    Returns a list of graph names as strings.
    """
    db = get_db_connection()
    graphs = db.graphs()
    return [g["name"] for g in graphs]


# ---------------------------------------------------------------------------
# describe_graph
# ---------------------------------------------------------------------------
@mcp.tool()
def describe_graph(graph_name: str) -> dict:
    """Return the vertex and edge collection definitions for a named graph.

    Args:
        graph_name: Name of the ArangoDB named graph to describe.

    Returns a dict with keys:
      - name: graph name
      - vertex_collections: list of vertex collection names
      - edge_definitions: list of {collection, from, to} dicts
    """
    db = get_db_connection()
    graph = db.graph(graph_name)
    props = graph.properties()

    return {
        "name": props.get("name", graph_name),
        "vertex_collections": list(props.get("orphan_collections", [])) + [
            ed["from"][0] for ed in props.get("edge_definitions", [])
        ],
        "edge_definitions": [
            {
                "collection": ed["collection"],
                "from": ed["from"],
                "to": ed["to"],
            }
            for ed in props.get("edge_definitions", [])
        ],
    }


# ---------------------------------------------------------------------------
# analyze_schema
# ---------------------------------------------------------------------------
@mcp.tool()
def analyze_schema(
    graph_name: Optional[str] = None,
    max_sample_size: int = 100,
) -> dict:
    """Extract and LLM-analyse the graph schema.

    Runs SchemaExtractor to gather structural information from ArangoDB,
    then SchemaAnalyzer to produce LLM-generated insights.

    Args:
        graph_name: Optional graph to focus on. If omitted, analyses the
            whole database.
        max_sample_size: Max documents to sample per collection (default 100).

    Returns a dict with keys:
      - collections: list of collection summaries
      - relationships: list of edge relationships
      - analysis: LLM-generated schema analysis text
    """
    from graph_analytics_ai.db_connection import get_db_connection
    from graph_analytics_ai.ai.schema import SchemaExtractor, SchemaAnalyzer
    from graph_analytics_ai.ai.llm import create_llm_provider

    db = get_db_connection()
    extractor = SchemaExtractor(db, max_sample_size=max_sample_size)
    schema = extractor.extract()

    provider = create_llm_provider()
    analyzer = SchemaAnalyzer(provider)
    analysis = analyzer.analyze(schema)

    return {
        "collections": [
            {
                "name": c.name,
                "type": c.collection_type.value if hasattr(c.collection_type, "value") else str(c.collection_type),
                "document_count": c.document_count,
                "attributes": [a.name for a in (c.attributes or [])],
            }
            for c in schema.collections
        ],
        "relationships": [
            {
                "edge_collection": r.edge_collection,
                "from_collection": r.from_collection,
                "to_collection": r.to_collection,
            }
            for r in (schema.relationships or [])
        ],
        "analysis": analysis.summary if hasattr(analysis, "summary") else str(analysis),
    }
