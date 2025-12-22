"""
Collection Selection Agent for Algorithm-Specific Graph Filtering.

This agent determines which vertex and edge collections should be used
for each graph algorithm based on the algorithm's characteristics and
graph structure.
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from ..schema.models import GraphSchema
from .models import AlgorithmType


class CollectionRole(Enum):
    """Role of a collection in the graph."""

    CORE = "core"  # Central to the graph structure
    SATELLITE = "satellite"  # Peripheral, reference data
    BRIDGE = "bridge"  # Connects core to other parts
    METADATA = "metadata"  # Supplementary information


@dataclass
class CollectionSelection:
    """
    Selection of collections for a specific algorithm.
    """

    algorithm: AlgorithmType
    """Algorithm this selection is for."""

    vertex_collections: List[str]
    """Selected vertex collections."""

    edge_collections: List[str]
    """Selected edge collections."""

    excluded_vertices: List[str]
    """Excluded vertex collections with reasons."""

    excluded_edges: List[str]
    """Excluded edge collections with reasons."""

    reasoning: str
    """Explanation for the selection."""

    estimated_graph_size: Dict[str, int]
    """Estimated size of selected graph."""


class CollectionSelector:
    """
    Selects appropriate collections for each algorithm type.

    Different algorithms have different requirements:
    - WCC/SCC: Need strongly connected core graph, exclude satellites
    - PageRank: Works best with full graph including satellites
    - Betweenness: Needs full graph for accurate centrality
    - Label Propagation: Depends on community structure

    Example:
        >>> selector = CollectionSelector()
        >>> selection = selector.select_collections(
        ...     algorithm=AlgorithmType.WCC,
        ...     schema=graph_schema,
        ...     collection_hints={"satellite_collections": ["metadata", "configs"]}
        ... )
        >>> print(f"Using: {selection.vertex_collections}")
        >>> print(f"Reason: {selection.reasoning}")
    """

    # Algorithm-specific requirements
    ALGORITHM_REQUIREMENTS = {
        AlgorithmType.WCC: {
            "needs_satellites": False,
            "needs_full_connectivity": True,
            "min_edge_count": 1,
            "focus": "core_graph",
        },
        AlgorithmType.SCC: {
            "needs_satellites": False,
            "needs_full_connectivity": True,
            "needs_directed": True,
            "min_edge_count": 1,
            "focus": "core_graph",
        },
        AlgorithmType.PAGERANK: {
            "needs_satellites": True,  # Satellites can be important
            "needs_full_connectivity": False,
            "min_edge_count": 1,
            "focus": "full_graph",
        },
        AlgorithmType.BETWEENNESS_CENTRALITY: {
            "needs_satellites": True,  # Need full graph for accurate centrality
            "needs_full_connectivity": False,
            "min_edge_count": 1,
            "focus": "full_graph",
        },
        AlgorithmType.LABEL_PROPAGATION: {
            "needs_satellites": False,  # Focus on communities
            "needs_full_connectivity": False,
            "min_edge_count": 2,  # Need actual community structure
            "focus": "core_graph",
        },
    }

    def __init__(self):
        """Initialize collection selector."""
        self.collection_roles: Dict[str, CollectionRole] = {}

    def select_collections(
        self,
        algorithm: AlgorithmType,
        schema: GraphSchema,
        collection_hints: Optional[Dict[str, Any]] = None,
        use_case_context: Optional[str] = None,
    ) -> CollectionSelection:
        """
        Select appropriate collections for an algorithm.

        Args:
            algorithm: Algorithm to select collections for
            schema: Graph schema with collection information
            collection_hints: Optional hints about collection roles
            use_case_context: Optional use case description for context

        Returns:
            CollectionSelection with chosen collections and reasoning
        """
        # Get algorithm requirements
        requirements = self.ALGORITHM_REQUIREMENTS.get(
            algorithm, {"needs_satellites": True, "focus": "full_graph"}
        )

        # Classify collections if hints provided
        if collection_hints:
            self._classify_collections(schema, collection_hints)
        else:
            self._auto_classify_collections(schema)

        # Select based on algorithm needs
        if requirements["focus"] == "core_graph":
            return self._select_core_graph(algorithm, schema, requirements)
        elif requirements["focus"] == "full_graph":
            return self._select_full_graph(algorithm, schema, requirements)
        else:
            return self._select_custom(
                algorithm, schema, requirements, use_case_context
            )

    def _classify_collections(self, schema: GraphSchema, hints: Dict[str, Any]):
        """
        Classify collections based on provided hints.

        Args:
            schema: Graph schema
            hints: Dictionary with classification hints like:
                   {"satellite_collections": ["metadata", "configs"],
                    "core_collections": ["users", "products"],
                    "bridge_collections": ["categories"]}
        """
        # Mark satellites
        for coll_name in hints.get("satellite_collections", []):
            self.collection_roles[coll_name] = CollectionRole.SATELLITE

        # Mark core
        for coll_name in hints.get("core_collections", []):
            self.collection_roles[coll_name] = CollectionRole.CORE

        # Mark bridges
        for coll_name in hints.get("bridge_collections", []):
            self.collection_roles[coll_name] = CollectionRole.BRIDGE

        # Mark metadata
        for coll_name in hints.get("metadata_collections", []):
            self.collection_roles[coll_name] = CollectionRole.METADATA

    def _auto_classify_collections(self, schema: GraphSchema):
        """
        Auto-classify collections based on naming and structure.

        Uses heuristics:
        - Collections with few docs (<100) likely metadata
        - Collections with "config", "setting", "meta" in name likely satellites
        - Collections with most edges likely core
        - Collections with high document count likely core
        """
        # Heuristic keywords
        satellite_keywords = ["config", "setting", "metadata", "lookup", "reference"]

        # Get edge counts per collection
        edge_counts = self._count_edges_per_collection(schema)

        for coll_name, coll_info in schema.vertex_collections.items():
            doc_count = coll_info.document_count or 0
            edges = edge_counts.get(coll_name, 0)

            # Check for satellite keywords
            if any(kw in coll_name.lower() for kw in satellite_keywords):
                self.collection_roles[coll_name] = CollectionRole.SATELLITE
            # Very few documents = likely metadata
            elif doc_count < 100:
                self.collection_roles[coll_name] = CollectionRole.METADATA
            # Many edges = likely core
            elif edges > 1000 or (doc_count > 500 and edges > 100):
                self.collection_roles[coll_name] = CollectionRole.CORE
            # Default to core if substantial
            elif doc_count >= 100:
                self.collection_roles[coll_name] = CollectionRole.CORE
            else:
                self.collection_roles[coll_name] = CollectionRole.SATELLITE

    def _count_edges_per_collection(self, schema: GraphSchema) -> Dict[str, int]:
        """Count edges connected to each vertex collection."""
        counts = {}

        # Count from/to edges for each collection
        for edge_name, edge_info in schema.edge_collections.items():
            # This is simplified - in reality you'd need to parse edge definitions
            # For now, assume all vertex collections are involved
            pass

        return counts

    def _select_core_graph(
        self,
        algorithm: AlgorithmType,
        schema: GraphSchema,
        requirements: Dict[str, Any],
    ) -> CollectionSelection:
        """Select only core graph collections (exclude satellites)."""

        # Select core and bridge collections only
        selected_vertices = []
        excluded_vertices = []

        for coll_name, coll_info in schema.vertex_collections.items():
            role = self.collection_roles.get(coll_name, CollectionRole.CORE)

            if role in [CollectionRole.CORE, CollectionRole.BRIDGE]:
                selected_vertices.append(coll_name)
            else:
                excluded_vertices.append(f"{coll_name} ({role.value})")

        # Select edges that connect selected vertices
        selected_edges, excluded_edges = self._select_connecting_edges(
            schema, selected_vertices
        )

        reasoning = (
            f"{algorithm.value} analysis focuses on core graph connectivity. "
            f"Excluded {len(excluded_vertices)} satellite/metadata collections "
            f"and {len(excluded_edges)} peripheral edges. "
            f"This ensures the algorithm finds meaningful components "
            f"in the primary graph structure."
        )

        return CollectionSelection(
            algorithm=algorithm,
            vertex_collections=selected_vertices,
            edge_collections=selected_edges,
            excluded_vertices=excluded_vertices,
            excluded_edges=excluded_edges,
            reasoning=reasoning,
            estimated_graph_size=self._estimate_size(
                schema, selected_vertices, selected_edges
            ),
        )

    def _select_full_graph(
        self,
        algorithm: AlgorithmType,
        schema: GraphSchema,
        requirements: Dict[str, Any],
    ) -> CollectionSelection:
        """Select all collections (full graph)."""

        selected_vertices = list(schema.vertex_collections.keys())
        selected_edges = list(schema.edge_collections.keys())

        reasoning = (
            f"{algorithm.value} analysis uses the complete graph structure. "
            f"Including all {len(selected_vertices)} vertex collections and "
            f"{len(selected_edges)} edge collections ensures accurate "
            f"centrality/influence calculations across the entire network."
        )

        return CollectionSelection(
            algorithm=algorithm,
            vertex_collections=selected_vertices,
            edge_collections=selected_edges,
            excluded_vertices=[],
            excluded_edges=[],
            reasoning=reasoning,
            estimated_graph_size=self._estimate_size(
                schema, selected_vertices, selected_edges
            ),
        )

    def _select_custom(
        self,
        algorithm: AlgorithmType,
        schema: GraphSchema,
        requirements: Dict[str, Any],
        context: Optional[str],
    ) -> CollectionSelection:
        """Custom selection based on context."""
        # Default to full graph for unknown algorithms
        return self._select_full_graph(algorithm, schema, requirements)

    def _select_connecting_edges(
        self, schema: GraphSchema, selected_vertices: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Select edges that connect selected vertex collections.

        Args:
            schema: Graph schema
            selected_vertices: List of selected vertex collections

        Returns:
            Tuple of (selected_edges, excluded_edges)
        """
        selected_edges = []
        excluded_edges = []

        set(selected_vertices)

        for edge_name, edge_info in schema.edge_collections.items():
            # In a real implementation, you'd parse edge definitions
            # to determine from/to collections
            # For now, include all edges as we don't have that info
            selected_edges.append(edge_name)

        return selected_edges, excluded_edges

    def _estimate_size(
        self, schema: GraphSchema, vertices: List[str], edges: List[str]
    ) -> Dict[str, int]:
        """Estimate size of selected graph."""
        vertex_count = sum(
            schema.vertex_collections[v].document_count or 0
            for v in vertices
            if v in schema.vertex_collections
        )

        edge_count = sum(
            schema.edge_collections[e].document_count or 0
            for e in edges
            if e in schema.edge_collections
        )

        return {
            "vertices": vertex_count,
            "edges": edge_count,
            "collections": len(vertices) + len(edges),
        }


def select_collections_for_algorithm(
    algorithm: AlgorithmType,
    schema: GraphSchema,
    satellite_collections: Optional[List[str]] = None,
    core_collections: Optional[List[str]] = None,
) -> CollectionSelection:
    """
    Convenience function to select collections for an algorithm.

    Args:
        algorithm: Algorithm type
        schema: Graph schema
        satellite_collections: Optional list of satellite collection names
        core_collections: Optional list of core collection names

    Returns:
        CollectionSelection with chosen collections

    Example:
        >>> selection = select_collections_for_algorithm(
        ...     algorithm=AlgorithmType.WCC,
        ...     schema=my_schema,
        ...     satellite_collections=["metadata", "configs"]
        ... )
        >>> print(selection.vertex_collections)
        ['users', 'products', 'orders']  # Excludes metadata, configs
    """
    selector = CollectionSelector()

    hints = {}
    if satellite_collections:
        hints["satellite_collections"] = satellite_collections
    if core_collections:
        hints["core_collections"] = core_collections

    return selector.select_collections(
        algorithm=algorithm, schema=schema, collection_hints=hints if hints else None
    )
