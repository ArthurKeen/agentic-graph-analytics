"""
Models for GAE template generation.

Defines data structures for GAE analysis configurations and templates.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class AlgorithmType(Enum):
    """
    GAE algorithm types.

    Only includes algorithms that are actually supported by GAE
    and implemented in the library.

    IMPORTANT: This is the single source of truth for supported algorithms.
    Do not reference unsupported algorithms (LOUVAIN, SHORTEST_PATH, CLOSENESS_CENTRALITY)
    anywhere in the codebase.
    """

    PAGERANK = "pagerank"
    LABEL_PROPAGATION = "label_propagation"
    WCC = "wcc"  # Weakly Connected Components
    SCC = "scc"  # Strongly Connected Components
    BETWEENNESS_CENTRALITY = "betweenness"

    @classmethod
    def get_supported_names(cls) -> List[str]:
        """Get list of supported algorithm names."""
        return [alg.value for alg in cls]

    @classmethod
    def get_display_names(cls) -> Dict[str, str]:
        """Get mapping of algorithm values to display names."""
        return {
            cls.PAGERANK.value: "PageRank",
            cls.LABEL_PROPAGATION.value: "Label Propagation",
            cls.WCC.value: "Weakly Connected Components (WCC)",
            cls.SCC.value: "Strongly Connected Components (SCC)",
            cls.BETWEENNESS_CENTRALITY.value: "Betweenness Centrality",
        }


class EngineSize(Enum):
    """GAE engine sizes for AMP deployments."""

    XSMALL = "xsmall"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"


@dataclass
class AlgorithmParameters:
    """Parameters for a specific GAE algorithm."""

    algorithm: AlgorithmType
    """The algorithm to run."""

    parameters: Dict[str, Any] = field(default_factory=dict)
    """Algorithm-specific parameters."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {"algorithm": self.algorithm.value, "parameters": self.parameters}


@dataclass
class LpgProjection:
    """Typed projection plan for an LPG (Labelled Property Graph) source.

    PRD v0.6 / FR-71. GAE engines consume whole collections, so when
    the source schema is LPG (one generic collection mixing many
    logical types distinguished by a discriminator property such as
    ``type`` or ``relType``), the orchestrator MUST materialize a
    typed projection before launching GAE.

    The plan captures everything the executor needs to do that
    materialization deterministically:

    - ``logical_type`` — entity / relationship name from the
      conceptual schema (e.g. ``"Person"``).
    - ``source_collection`` — generic collection to project from
      (e.g. ``"nodes"`` or ``"entities"``).
    - ``discriminator_field`` — property to filter on (e.g. ``"type"``).
    - ``discriminator_value`` — value the field must equal
      (e.g. ``"Person"``).
    - ``kind`` — ``"node"`` or ``"edge"`` so the materializer knows
      whether to copy ``_from`` / ``_to``.
    - ``materialization_collection`` — name of the projection
      collection to create / refresh
      (e.g. ``"_proj_corpus_Person"``).
    - ``materialization_aql`` — AQL command the executor can run
      verbatim. Always ``UPSERT``-shaped so the projection is
      idempotent.
    """

    logical_type: str
    source_collection: str
    discriminator_field: str
    discriminator_value: str
    kind: str = "node"  # "node" | "edge"
    materialization_collection: str = ""
    materialization_aql: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "logical_type": self.logical_type,
            "source_collection": self.source_collection,
            "discriminator_field": self.discriminator_field,
            "discriminator_value": self.discriminator_value,
            "kind": self.kind,
            "materialization_collection": self.materialization_collection,
            "materialization_aql": self.materialization_aql,
        }


@dataclass
class TemplateConfig:
    """Configuration for template generation."""

    graph_name: str
    """Name of the graph to analyze."""

    vertex_collections: List[str] = field(default_factory=list)
    """Vertex collections to include (empty = all)."""

    edge_collections: List[str] = field(default_factory=list)
    """Edge collections to include (empty = all)."""

    engine_size: EngineSize = EngineSize.SMALL
    """Engine size for AMP deployments."""

    store_results: bool = True
    """Whether to store results in database."""

    result_collection: Optional[str] = None
    """Collection to store results (auto-generated if None)."""

    schema_kind: Optional[str] = None
    """Source schema kind ('pg' / 'lpg' / 'hybrid' / 'rpt' / 'unknown').

    PRD v0.6 / FR-71. Set when the template was generated against a
    :class:`SchemaAcquisitionBundle`. Lets the executor decide whether
    to materialize typed projections before running GAE.
    """

    lpg_projections: List[LpgProjection] = field(default_factory=list)
    """Typed projection plans (PRD v0.6 / FR-71).

    Empty for PG sources. For LPG / hybrid sources, lists the
    projections the executor must materialize before launching GAE.
    """

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        payload: Dict[str, Any] = {
            "graph_name": self.graph_name,
            "vertex_collections": self.vertex_collections,
            "edge_collections": self.edge_collections,
            "engine_size": self.engine_size.value,
            "store_results": self.store_results,
            "result_collection": self.result_collection,
        }
        if self.schema_kind is not None:
            payload["schema_kind"] = self.schema_kind
        if self.lpg_projections:
            payload["lpg_projections"] = [p.to_dict() for p in self.lpg_projections]
        return payload


@dataclass
class AnalysisTemplate:
    """
    Template for a GAE analysis configuration.

    Represents a complete, executable GAE analysis configuration
    that can be sent to the GAE API.
    """

    name: str
    """Human-readable name for this analysis."""

    description: str
    """Description of what this analysis does."""

    algorithm: AlgorithmParameters
    """Algorithm and its parameters."""

    config: TemplateConfig
    """Template configuration."""

    use_case_id: Optional[str] = None
    """ID of the use case this was generated from."""

    estimated_runtime_seconds: Optional[float] = None
    """Estimated runtime (if available)."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for GAE API."""
        return {
            "name": self.name,
            "description": self.description,
            "algorithm": self.algorithm.to_dict(),
            "config": self.config.to_dict(),
            "use_case_id": self.use_case_id,
            "estimated_runtime_seconds": self.estimated_runtime_seconds,
            "metadata": self.metadata,
        }

    def to_analysis_config(self) -> Dict[str, Any]:
        """
        Convert to AnalysisConfig format for GAE orchestrator.

        Returns dictionary that can be used with GAEOrchestrator.
        """
        payload: Dict[str, Any] = {
            "name": self.name,
            "graph": self.config.graph_name,
            "algorithm": self.algorithm.algorithm.value,
            "params": self.algorithm.parameters,
            "vertex_collections": self.config.vertex_collections,
            "edge_collections": self.config.edge_collections,
            "engine_size": self.config.engine_size.value,
            "store_results": self.config.store_results,
            "result_collection": self.config.result_collection,
        }
        if self.config.schema_kind is not None:
            payload["schema_kind"] = self.config.schema_kind
        if self.config.lpg_projections:
            payload["lpg_projections"] = [
                p.to_dict() for p in self.config.lpg_projections
            ]
        return payload


# Default algorithm parameters for supported GAE algorithms
DEFAULT_ALGORITHM_PARAMS = {
    AlgorithmType.PAGERANK: {"damping_factor": 0.85, "maximum_supersteps": 100},
    AlgorithmType.LABEL_PROPAGATION: {
        "start_label_attribute": "_key",
        "synchronous": False,
        "random_tiebreak": False,
        "maximum_supersteps": 100,
    },
    AlgorithmType.BETWEENNESS_CENTRALITY: {"maximum_supersteps": 100},
    AlgorithmType.WCC: {},
    AlgorithmType.SCC: {},
}


# Recommended engine sizes based on graph size
def recommend_engine_size(vertex_count: int, edge_count: int) -> EngineSize:
    """
    Recommend engine size based on graph dimensions.

    Args:
        vertex_count: Number of vertices in graph
        edge_count: Number of edges in graph

    Returns:
        Recommended EngineSize
    """
    total_elements = vertex_count + edge_count

    if total_elements < 1000:
        return EngineSize.XSMALL
    elif total_elements < 10000:
        return EngineSize.SMALL
    elif total_elements < 100000:
        return EngineSize.MEDIUM
    elif total_elements < 1000000:
        return EngineSize.LARGE
    else:
        return EngineSize.XLARGE
