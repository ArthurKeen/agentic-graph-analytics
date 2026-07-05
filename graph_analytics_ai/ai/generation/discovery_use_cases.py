"""
Discovery (unknown-unknowns) use case generation.

This module creates an opt-in bundle of "graph health + risk" analyses that can be
run alongside (or before) requirement-driven analytics. The goal is to surface
problems the user did not explicitly ask for.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..documents.models import Priority
from ..schema.models import GraphSchema, SchemaAnalysis
from .use_cases import UseCase, UseCaseType


def _looks_like_eda_ic_design(schema: Optional[GraphSchema]) -> bool:
    if not schema or not getattr(schema, "vertex_collections", None):
        return False
    names = set(schema.vertex_collections.keys())
    if any(n.startswith("RTL_") for n in names):
        return True
    if any(n.startswith("FSM_") for n in names):
        return True
    if {"Chunk", "Golden_Entity"} & names:
        # GraphRAG-style docs + entities are common in the IC demo graphs.
        return True
    return False


def generate_discovery_use_cases(
    schema: Optional[GraphSchema],
    schema_analysis: Optional[SchemaAnalysis],
    *,
    max_use_cases: int = 10,
) -> List[UseCase]:
    """
    Generate a discovery bundle of use cases.

    This is intentionally deterministic and lightweight. It relies on existing
    GAE-supported algorithms and downstream derived detectors in reporting.
    """
    domain_hint = ""
    if schema_analysis and getattr(schema_analysis, "domain", None):
        domain_hint = str(schema_analysis.domain)

    if _looks_like_eda_ic_design(schema):
        return [
            UseCase(
                id="UC-D01",
                title="Discovery: Critical IP & Documentation Hotspots (PageRank)",
                description=(
                    "Identify high blast-radius RTL modules/ports/signals and spec entities/chunks. "
                    "This surfaces hidden single points of failure and high-impact change targets."
                ),
                use_case_type=UseCaseType.CENTRALITY,
                priority=Priority.HIGH,
                graph_algorithms=["pagerank"],
                data_needs=[
                    "RTL_Module, RTL_Port, RTL_Signal, RTL_LogicChunk, Chunk, Golden_Entity",
                    "Edges: CONTAINS, HAS_PORT, HAS_SIGNAL, RESOLVED_TO",
                ],
                expected_outputs=[
                    "Top-k influential RTL modules/ports/signals/spec entities",
                    "Influence concentration and outliers",
                ],
                success_metrics=["Top-1% nodes identified with supporting evidence"],
            ),
            UseCase(
                id="UC-D02",
                title="Discovery: Interface Chokepoints & Bridge Risks (Betweenness)",
                description=(
                    "Find ports/signals/modules that bridge many regions of the design graph. "
                    "Chokepoints increase coupling and debug cost; failures propagate widely."
                ),
                use_case_type=UseCaseType.ANOMALY,
                priority=Priority.HIGH,
                graph_algorithms=["betweenness"],
                data_needs=[
                    "RTL_Port, RTL_Signal, RTL_Module",
                    "Edges: HAS_PORT, HAS_SIGNAL, WIRED_TO, DEPENDS_ON",
                ],
                expected_outputs=[
                    "Top bridge nodes by betweenness centrality",
                    "Bridge concentration and chokepoint candidates",
                ],
                success_metrics=[
                    "Top bridge nodes with clear blast-radius explanation"
                ],
            ),
            UseCase(
                id="UC-D03",
                title="Discovery: Traceability Islands & Integration Fragmentation (WCC)",
                description=(
                    "Detect disconnected components that indicate missing semantic bridges (spec/doc islands) "
                    "or incomplete extraction/integration (isolated RTL blocks)."
                ),
                use_case_type=UseCaseType.COMMUNITY,
                priority=Priority.HIGH,
                graph_algorithms=["wcc"],
                data_needs=[
                    "Chunk, Golden_Entity, RTL_Module and supporting structure",
                    "Edges: RESOLVED_TO plus structural RTL edges",
                ],
                expected_outputs=[
                    "Largest components and singleton/island counts",
                    "Spec-only components vs RTL-connected components",
                ],
                success_metrics=["Orphan islands and fragmentation quantified"],
            ),
            UseCase(
                id="UC-D04",
                title="Discovery: Cyclic Dependency Core (SCC)",
                description=(
                    "Identify tightly-coupled strongly connected cores that are expensive to debug/verify. "
                    "Use SCC as a first-pass proxy for dependency cycles across RTL blocks."
                ),
                use_case_type=UseCaseType.PATTERN,
                priority=Priority.MEDIUM,
                graph_algorithms=["scc"],
                data_needs=[
                    "RTL_Module/RTL_Signal/RTL_LogicChunk",
                    "Edges: DEPENDS_ON, WIRED_TO, DRIVES, READS_FROM",
                ],
                expected_outputs=[
                    "Largest SCCs and cyclic dependency concentration",
                ],
                success_metrics=["Dominant SCCs flagged with risk rationale"],
            ),
            UseCase(
                id="UC-D05",
                title="Discovery: Unexpected Mixing Across Natural Communities (Label Propagation)",
                description=(
                    "Discover natural clusters of design components and documentation. "
                    "Unexpected community mixing or a dominant mega-community can indicate hidden coupling."
                ),
                use_case_type=UseCaseType.COMMUNITY,
                priority=Priority.MEDIUM,
                graph_algorithms=["label_propagation"],
                data_needs=[
                    "RTL_Module, RTL_LogicChunk, Chunk/Golden_Entity",
                    "Edges: structural + RESOLVED_TO",
                ],
                expected_outputs=[
                    "Community count, sizes, and dominant communities",
                ],
                success_metrics=[
                    "Community structure summarized and anomalies highlighted"
                ],
            ),
        ][:max_use_cases]

    # Generic discovery bundle for unknown domains
    return [
        UseCase(
            id="UC-D01",
            title="Discovery: Influence Hotspots (PageRank)",
            description=(
                f"Identify high influence/importance nodes to surface hidden hotspots. Domain: {domain_hint or 'unknown'}."
            ),
            use_case_type=UseCaseType.CENTRALITY,
            priority=Priority.HIGH,
            graph_algorithms=["pagerank"],
            data_needs=[],
            expected_outputs=[
                "Top-k influential nodes",
                "Influence concentration/outliers",
            ],
            success_metrics=[],
        ),
        UseCase(
            id="UC-D02",
            title="Discovery: Connectivity Islands (WCC)",
            description="Detect disconnected components and isolate islands that may indicate missing links or data quality issues.",
            use_case_type=UseCaseType.COMMUNITY,
            priority=Priority.MEDIUM,
            graph_algorithms=["wcc"],
            data_needs=[],
            expected_outputs=[
                "Component count/sizes",
                "Isolated nodes and fragmentation",
            ],
            success_metrics=[],
        ),
    ][:max_use_cases]
