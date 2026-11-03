"""Schema-and-graph-driven use case planning (FR-75).

The deterministic bundle in :mod:`discovery_use_cases` picks use cases from
collection-name prefixes: one hardcoded branch for IC-design graphs, and two
fixed use cases (PageRank, WCC) for everything else. It never looks at how
large the graph is, how it is shaped, or what its entities mean, so every
unfamiliar domain gets the same two analyses.

This module asks the LLM to choose instead, grounded in the observed entity
and relationship types plus real collection counts, and keeps the
deterministic bundle as the fallback for when no provider is configured or
the model returns nothing usable.

The algorithm whitelist is enforced here rather than trusted from the model.
A plan naming an algorithm the engine does not implement fails late, inside
an execution, where it reads as a runtime error rather than a bad plan.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..documents.models import Priority
from ..schema.models import GraphSchema, SchemaAnalysis
from .discovery_use_cases import generate_discovery_use_cases
from .use_cases import UseCase, UseCaseType

logger = logging.getLogger(__name__)


# The five algorithms the Graph Analytics Engine actually exposes. A plan is
# only as good as the engine behind it, so anything outside this set is
# dropped rather than passed along.
SUPPORTED_ALGORITHMS = (
    "pagerank",
    "betweenness",
    "wcc",
    "scc",
    "label_propagation",
)

# What each algorithm is for, in the terms the use case model uses.
ALGORITHM_USE_CASE_TYPE = {
    "pagerank": UseCaseType.CENTRALITY,
    "betweenness": UseCaseType.CENTRALITY,
    "wcc": UseCaseType.COMMUNITY,
    "scc": UseCaseType.COMMUNITY,
    "label_propagation": UseCaseType.COMMUNITY,
}

PRIORITY_BY_NAME = {
    "high": Priority.HIGH,
    "medium": Priority.MEDIUM,
    "low": Priority.LOW,
}

PLAN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "domain": {"type": "string"},
        "use_cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "question": {"type": "string"},
                    "algorithm": {"type": "string", "enum": list(SUPPORTED_ALGORITHMS)},
                    "rationale": {"type": "string"},
                    "target_entities": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "report_focus": {"type": "string"},
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                },
                "required": [
                    "title",
                    "question",
                    "algorithm",
                    "rationale",
                    "report_focus",
                ],
            },
        },
    },
    "required": ["use_cases"],
}


def summarize_graph(
    schema: Optional[GraphSchema],
    schema_analysis: Optional[SchemaAnalysis],
) -> Dict[str, Any]:
    """Describe what is actually in the graph, not just what it declares.

    Counts come from the live collections, so the planner can tell a
    1,000-vertex graph from a 17-million-edge one. Betweenness on the latter
    is a very different proposition, and a planner that cannot see the
    difference will keep proposing it.
    """

    summary: Dict[str, Any] = {
        "vertex_collections": [],
        "edge_collections": [],
        "total_vertices": 0,
        "total_edges": 0,
    }
    if schema is None:
        return summary

    for name, collection in (schema.vertex_collections or {}).items():
        count = getattr(collection, "document_count", 0) or 0
        summary["vertex_collections"].append({"name": name, "count": count})
        summary["total_vertices"] += count

    for name, collection in (schema.edge_collections or {}).items():
        count = getattr(collection, "document_count", 0) or 0
        summary["edge_collections"].append({"name": name, "count": count})
        summary["total_edges"] += count

    vertices = summary["total_vertices"]
    if vertices:
        # Average degree separates a hub-and-spoke graph from a mesh, which is
        # the single most useful signal for choosing between centrality and
        # community algorithms.
        summary["average_degree"] = round(summary["total_edges"] / vertices, 2)

    relationships = getattr(schema, "relationships", None) or []
    summary["relationship_types"] = [
        {
            "type": getattr(rel, "name", None) or getattr(rel, "edge_collection", ""),
            "from": getattr(rel, "from_collection", ""),
            "to": getattr(rel, "to_collection", ""),
        }
        for rel in relationships
    ]

    if schema_analysis is not None:
        if schema_analysis.domain:
            summary["domain"] = schema_analysis.domain
        if schema_analysis.key_entities:
            summary["key_entities"] = list(schema_analysis.key_entities)
        if schema_analysis.key_relationships:
            summary["key_relationships"] = list(schema_analysis.key_relationships)
        if schema_analysis.description:
            summary["description"] = schema_analysis.description

    return summary


def build_planning_prompt(summary: Dict[str, Any], max_use_cases: int) -> str:
    """Render the graph summary into the planning prompt."""

    lines = [
        "You are planning a graph analytics study. Nobody has told you what "
        "to look for. Decide it from the graph itself.",
        "",
        "## The graph",
    ]

    if summary.get("domain"):
        lines.append(f"Domain (inferred): {summary['domain']}")
    if summary.get("description"):
        lines.append(f"Description: {summary['description']}")

    lines.append(
        f"Scale: {summary.get('total_vertices', 0):,} vertices, "
        f"{summary.get('total_edges', 0):,} edges"
    )
    if "average_degree" in summary:
        lines.append(f"Average degree: {summary['average_degree']}")

    vertex_collections = summary.get("vertex_collections") or []
    if vertex_collections:
        lines.append("")
        lines.append("Vertex collections:")
        for collection in vertex_collections:
            lines.append(f"- {collection['name']}: {collection['count']:,}")

    edge_collections = summary.get("edge_collections") or []
    if edge_collections:
        lines.append("")
        lines.append("Edge collections:")
        for collection in edge_collections:
            lines.append(f"- {collection['name']}: {collection['count']:,}")

    relationship_types = summary.get("relationship_types") or []
    if relationship_types:
        lines.append("")
        lines.append("Relationships:")
        for rel in relationship_types:
            if rel.get("type"):
                lines.append(
                    f"- {rel['type']}: {rel.get('from', '?')} to {rel.get('to', '?')}"
                )

    lines.extend(
        [
            "",
            "## Your task",
            f"Propose at most {max_use_cases} analyses that are worth running "
            "on THIS graph. Each one must name a question a person in this "
            "domain would actually ask, and say what the report should show.",
            "",
            "Choose only from these algorithms:",
            "- pagerank: which nodes are influential, by weighted incoming links",
            "- betweenness: which nodes are bridges on paths between others. "
            "Costly on large graphs, so justify it or leave it out",
            "- wcc: which parts of the graph are disconnected islands",
            "- scc: which parts are mutually reachable, following direction",
            "- label_propagation: which nodes cluster into communities",
            "",
            "Rules:",
            "- Name real entity and relationship types from the lists above. "
            "Do not invent collection names.",
            "- Skip an algorithm when the graph's shape does not suit it. "
            "Fewer, well-matched analyses beat a full set.",
            "- rationale must say what about THIS graph makes the analysis "
            "worth running, not what the algorithm does in general.",
            "- report_focus must say what the reader should take away.",
        ]
    )

    return "\n".join(lines)


def _coerce_use_case(index: int, raw: Any) -> Optional[UseCase]:
    """Turn one planned entry into a UseCase, or drop it.

    Returns None rather than raising: one malformed entry in a plan of six is
    not a reason to lose the other five.
    """

    if not isinstance(raw, dict):
        return None

    algorithm = str(raw.get("algorithm", "")).strip().lower()
    if algorithm not in SUPPORTED_ALGORITHMS:
        logger.warning(
            "Dropping planned use case %r: algorithm %r is not implemented",
            raw.get("title"),
            raw.get("algorithm"),
        )
        return None

    title = str(raw.get("title", "")).strip()
    if not title:
        return None

    question = str(raw.get("question", "")).strip()
    rationale = str(raw.get("rationale", "")).strip()
    report_focus = str(raw.get("report_focus", "")).strip()

    description_parts = [part for part in (question, rationale) if part]
    targets = [
        str(entity).strip()
        for entity in (raw.get("target_entities") or [])
        if str(entity).strip()
    ]

    return UseCase(
        id=f"UC-A{index:02d}",
        title=title,
        description=" ".join(description_parts) or title,
        use_case_type=ALGORITHM_USE_CASE_TYPE[algorithm],
        priority=PRIORITY_BY_NAME.get(
            str(raw.get("priority", "")).strip().lower(), Priority.MEDIUM
        ),
        graph_algorithms=[algorithm],
        data_needs=targets,
        expected_outputs=[report_focus] if report_focus else [],
        success_metrics=[],
    )


def plan_use_cases(
    schema: Optional[GraphSchema],
    schema_analysis: Optional[SchemaAnalysis],
    llm_provider: Optional[Any] = None,
    *,
    max_use_cases: int = 6,
) -> List[UseCase]:
    """Decide which analyses suit this graph.

    Falls back to the deterministic bundle when there is no provider, the
    call fails, or every proposed use case is rejected. The fallback is the
    reason this can be enabled by default: the worst case is the behaviour
    that shipped before.
    """

    if llm_provider is None:
        return generate_discovery_use_cases(
            schema, schema_analysis, max_use_cases=max_use_cases
        )

    summary = summarize_graph(schema, schema_analysis)

    try:
        plan = llm_provider.generate_structured(
            build_planning_prompt(summary, max_use_cases), PLAN_SCHEMA
        )
    except Exception as exc:  # noqa: BLE001 - any provider failure falls back
        logger.warning("Autonomous planning failed, using the fixed bundle: %s", exc)
        return generate_discovery_use_cases(
            schema, schema_analysis, max_use_cases=max_use_cases
        )

    raw_cases = (plan or {}).get("use_cases") or []
    use_cases: List[UseCase] = []
    for raw in raw_cases:
        use_case = _coerce_use_case(len(use_cases) + 1, raw)
        if use_case is not None:
            use_cases.append(use_case)
        if len(use_cases) >= max_use_cases:
            break

    if not use_cases:
        logger.warning("Autonomous plan had no usable use cases, using the bundle")
        return generate_discovery_use_cases(
            schema, schema_analysis, max_use_cases=max_use_cases
        )

    return use_cases
