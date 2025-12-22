"""
Data models for representing graph schema information.

These models capture the structure of an ArangoDB graph, including
collections, relationships, and attributes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from enum import Enum


class CollectionType(Enum):
    """Type of collection in ArangoDB."""

    VERTEX = "vertex"
    EDGE = "edge"
    DOCUMENT = "document"


@dataclass
class AttributeInfo:
    """Information about a single attribute in a collection."""

    name: str
    """Attribute name."""

    data_types: Set[str] = field(default_factory=set)
    """Set of observed data types (e.g., 'string', 'number', 'object')."""

    sample_values: List[Any] = field(default_factory=list)
    """Sample values for this attribute (max 5)."""

    null_count: int = 0
    """Number of documents where this attribute is null or missing."""

    present_count: int = 0
    """Number of documents where this attribute is present."""

    @property
    def presence_ratio(self) -> float:
        """Ratio of documents that have this attribute."""
        total = self.null_count + self.present_count
        if total == 0:
            return 0.0
        return self.present_count / total

    @property
    def primary_type(self) -> str:
        """Most common data type for this attribute."""
        if not self.data_types:
            return "unknown"
        # Simple heuristic: prefer non-null types
        types = self.data_types - {"null"}
        if types:
            return sorted(types)[0]
        return "null"


@dataclass
class CollectionSchema:
    """Schema information for a single collection."""

    name: str
    """Collection name."""

    type: CollectionType
    """Collection type (vertex, edge, or document)."""

    document_count: int = 0
    """Total number of documents in collection."""

    attributes: Dict[str, AttributeInfo] = field(default_factory=dict)
    """Attributes found in this collection."""

    sample_documents: List[Dict[str, Any]] = field(default_factory=list)
    """Sample documents from collection (max 3)."""

    # For edge collections
    from_collections: Set[str] = field(default_factory=set)
    """Collections that edges originate from (for edge collections)."""

    to_collections: Set[str] = field(default_factory=set)
    """Collections that edges point to (for edge collections)."""

    def get_key_attributes(self, top_n: int = 5) -> List[str]:
        """
        Get the most important attributes based on presence ratio.

        Args:
            top_n: Number of top attributes to return.

        Returns:
            List of attribute names sorted by importance.
        """
        # Sort by presence ratio (descending)
        sorted_attrs = sorted(
            self.attributes.items(), key=lambda x: x[1].presence_ratio, reverse=True
        )

        # Always include system fields if present
        system_fields = {"_key", "_from", "_to", "_id", "_rev"}
        key_attrs = [name for name, _ in sorted_attrs if name in system_fields]

        # Add top user-defined fields
        user_attrs = [name for name, _ in sorted_attrs if name not in system_fields]
        key_attrs.extend(user_attrs[:top_n])

        return key_attrs[: top_n + len(system_fields)]


@dataclass
class Relationship:
    """A relationship between two vertex collections via an edge collection."""

    edge_collection: str
    """Edge collection name."""

    from_collection: str
    """Source vertex collection."""

    to_collection: str
    """Target vertex collection."""

    edge_count: int = 0
    """Number of edges in this relationship."""

    relationship_type: Optional[str] = None
    """Semantic type of relationship (e.g., 'KNOWS', 'PURCHASED')."""

    def __str__(self) -> str:
        """String representation of relationship."""
        rel_type = f" ({self.relationship_type})" if self.relationship_type else ""
        return f"{self.from_collection} --[{self.edge_collection}{rel_type}]--> {self.to_collection}"


@dataclass
class GraphSchema:
    """Complete schema information for a graph database."""

    database_name: str
    """Database name."""

    vertex_collections: Dict[str, CollectionSchema] = field(default_factory=dict)
    """Vertex collections in the graph."""

    edge_collections: Dict[str, CollectionSchema] = field(default_factory=dict)
    """Edge collections in the graph."""

    document_collections: Dict[str, CollectionSchema] = field(default_factory=dict)
    """Document collections (neither vertex nor edge)."""

    relationships: List[Relationship] = field(default_factory=list)
    """Identified relationships between collections."""

    graph_names: List[str] = field(default_factory=list)
    """Named graphs defined in the database."""

    @property
    def total_documents(self) -> int:
        """Total number of documents across all collections."""
        return sum(
            col.document_count
            for collections in [
                self.vertex_collections,
                self.edge_collections,
                self.document_collections,
            ]
            for col in collections.values()
        )

    @property
    def total_edges(self) -> int:
        """Total number of edges across all edge collections."""
        return sum(col.document_count for col in self.edge_collections.values())

    def get_collection(self, name: str) -> Optional[CollectionSchema]:
        """Get collection schema by name."""
        for collections in [
            self.vertex_collections,
            self.edge_collections,
            self.document_collections,
        ]:
            if name in collections:
                return collections[name]
        return None

    def get_relationships_for_collection(
        self, collection_name: str
    ) -> List[Relationship]:
        """Get all relationships involving a specific collection."""
        return [
            rel
            for rel in self.relationships
            if (
                rel.from_collection == collection_name
                or rel.to_collection == collection_name
            )
        ]

    def to_summary_dict(self) -> Dict[str, Any]:
        """
        Convert schema to a summary dictionary for LLM consumption.

        Returns a simplified representation suitable for LLM prompts.
        """
        return {
            "database": self.database_name,
            "statistics": {
                "total_collections": (
                    len(self.vertex_collections)
                    + len(self.edge_collections)
                    + len(self.document_collections)
                ),
                "vertex_collections": len(self.vertex_collections),
                "edge_collections": len(self.edge_collections),
                "total_documents": self.total_documents,
                "total_edges": self.total_edges,
                "relationships": len(self.relationships),
            },
            "vertex_collections": {
                name: {
                    "document_count": col.document_count,
                    "key_attributes": col.get_key_attributes(),
                    "sample_document": (
                        col.sample_documents[0] if col.sample_documents else None
                    ),
                }
                for name, col in self.vertex_collections.items()
            },
            "edge_collections": {
                name: {
                    "document_count": col.document_count,
                    "key_attributes": col.get_key_attributes(),
                    "from_collections": list(col.from_collections),
                    "to_collections": list(col.to_collections),
                }
                for name, col in self.edge_collections.items()
            },
            "relationships": [
                {
                    "from": rel.from_collection,
                    "edge": rel.edge_collection,
                    "to": rel.to_collection,
                    "count": rel.edge_count,
                    "type": rel.relationship_type,
                }
                for rel in self.relationships
            ],
            "graphs": self.graph_names,
        }


@dataclass
class SchemaAnalysis:
    """
    Analysis and insights about a graph schema.

    This is generated by combining schema extraction with LLM analysis.
    """

    schema: GraphSchema
    """The underlying graph schema."""

    description: str = ""
    """Human-readable description of the graph."""

    domain: Optional[str] = None
    """Identified domain (e.g., 'social network', 'supply chain', 'knowledge graph')."""

    key_entities: List[str] = field(default_factory=list)
    """Most important vertex collections."""

    key_relationships: List[str] = field(default_factory=list)
    """Most important edge collections."""

    suggested_analyses: List[Dict[str, str]] = field(default_factory=list)
    """Suggested graph analytics based on schema structure."""

    complexity_score: float = 0.0
    """Complexity score (0-10) based on number of collections and relationships."""

    @property
    def is_simple_graph(self) -> bool:
        """Whether this is a simple graph (few collections, clear structure)."""
        return self.complexity_score < 3.0

    @property
    def is_complex_graph(self) -> bool:
        """Whether this is a complex graph (many collections, intricate relationships)."""
        return self.complexity_score > 7.0
