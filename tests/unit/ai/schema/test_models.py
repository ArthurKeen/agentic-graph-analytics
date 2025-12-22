"""
Unit tests for schema models.

Tests the data models used to represent graph schema information.
"""

from graph_analytics_ai.ai.schema.models import (
    AttributeInfo,
    CollectionSchema,
    CollectionType,
    Relationship,
    SchemaAnalysis,
)


class TestAttributeInfo:
    """Test AttributeInfo model."""

    def test_presence_ratio(self):
        """Test calculation of presence ratio."""
        attr = AttributeInfo(name="email", present_count=80, null_count=20)

        assert attr.presence_ratio == 0.8

    def test_presence_ratio_zero_total(self):
        """Test presence ratio with zero total."""
        attr = AttributeInfo(name="test")
        assert attr.presence_ratio == 0.0

    def test_primary_type_single(self):
        """Test primary type with single type."""
        attr = AttributeInfo(name="age", data_types={"number"})

        assert attr.primary_type == "number"

    def test_primary_type_with_null(self):
        """Test primary type preferring non-null types."""
        attr = AttributeInfo(name="email", data_types={"string", "null"})

        assert attr.primary_type == "string"

    def test_primary_type_only_null(self):
        """Test primary type when only null."""
        attr = AttributeInfo(name="missing", data_types={"null"})

        assert attr.primary_type == "null"

    def test_primary_type_unknown(self):
        """Test primary type when no types."""
        attr = AttributeInfo(name="unknown")
        assert attr.primary_type == "unknown"


class TestCollectionSchema:
    """Test CollectionSchema model."""

    def test_get_key_attributes(self, sample_collection_schema):
        """Test getting key attributes."""
        key_attrs = sample_collection_schema.get_key_attributes(3)

        # Should include system field _key
        assert "_key" in key_attrs

        # Should include top attributes by presence
        assert "name" in key_attrs
        assert "age" in key_attrs

    def test_get_key_attributes_limited(self, sample_collection_schema):
        """Test limiting number of key attributes."""
        key_attrs = sample_collection_schema.get_key_attributes(2)

        # Should respect the limit (plus system fields)
        assert len(key_attrs) <= 3  # 2 + 1 system field

    def test_edge_collection_metadata(self):
        """Test edge collection specific metadata."""
        col = CollectionSchema(name="follows", type=CollectionType.EDGE)

        col.from_collections = {"users", "admins"}
        col.to_collections = {"users"}

        assert len(col.from_collections) == 2
        assert len(col.to_collections) == 1


class TestRelationship:
    """Test Relationship model."""

    def test_string_representation(self):
        """Test string representation of relationship."""
        rel = Relationship(
            edge_collection="follows",
            from_collection="users",
            to_collection="users",
            edge_count=100,
            relationship_type="FOLLOWS",
        )

        result = str(rel)

        assert "users" in result
        assert "follows" in result
        assert "FOLLOWS" in result
        assert "--[" in result and "]-->" in result

    def test_string_representation_no_type(self):
        """Test string representation without relationship type."""
        rel = Relationship(
            edge_collection="edges",
            from_collection="a",
            to_collection="b",
            edge_count=10,
        )

        result = str(rel)

        assert "a" in result
        assert "b" in result
        assert "edges" in result


class TestGraphSchema:
    """Test GraphSchema model."""

    def test_total_documents(self, sample_graph_schema):
        """Test calculation of total documents."""
        # users (100) + products (50) + follows (200) + purchased (500)
        assert sample_graph_schema.total_documents == 850

    def test_total_edges(self, sample_graph_schema):
        """Test calculation of total edges."""
        # follows (200) + purchased (500)
        assert sample_graph_schema.total_edges == 700

    def test_get_collection_vertex(self, sample_graph_schema):
        """Test getting vertex collection."""
        col = sample_graph_schema.get_collection("users")

        assert col is not None
        assert col.name == "users"
        assert col.type == CollectionType.VERTEX

    def test_get_collection_edge(self, sample_graph_schema):
        """Test getting edge collection."""
        col = sample_graph_schema.get_collection("follows")

        assert col is not None
        assert col.name == "follows"
        assert col.type == CollectionType.EDGE

    def test_get_collection_not_found(self, sample_graph_schema):
        """Test getting non-existent collection."""
        col = sample_graph_schema.get_collection("nonexistent")
        assert col is None

    def test_get_relationships_for_collection(self, sample_graph_schema):
        """Test getting relationships for a collection."""
        # Users are involved in both relationships
        rels = sample_graph_schema.get_relationships_for_collection("users")

        assert len(rels) == 2
        assert any(r.edge_collection == "follows" for r in rels)
        assert any(r.edge_collection == "purchased" for r in rels)

    def test_get_relationships_for_collection_products(self, sample_graph_schema):
        """Test getting relationships for products."""
        # Products only in purchased relationship
        rels = sample_graph_schema.get_relationships_for_collection("products")

        assert len(rels) == 1
        assert rels[0].edge_collection == "purchased"

    def test_to_summary_dict(self, sample_graph_schema):
        """Test conversion to summary dictionary."""
        summary = sample_graph_schema.to_summary_dict()

        assert summary["database"] == "test_db"
        assert summary["statistics"]["total_collections"] == 4
        assert summary["statistics"]["vertex_collections"] == 2
        assert summary["statistics"]["edge_collections"] == 2
        assert summary["statistics"]["total_documents"] == 850
        assert summary["statistics"]["total_edges"] == 700

        assert "users" in summary["vertex_collections"]
        assert "products" in summary["vertex_collections"]
        assert "follows" in summary["edge_collections"]
        assert "purchased" in summary["edge_collections"]

        assert len(summary["relationships"]) == 2


class TestSchemaAnalysis:
    """Test SchemaAnalysis model."""

    def test_is_simple_graph(self, sample_graph_schema):
        """Test simple graph detection."""
        analysis = SchemaAnalysis(schema=sample_graph_schema, complexity_score=2.5)

        assert analysis.is_simple_graph
        assert not analysis.is_complex_graph

    def test_is_complex_graph(self, sample_graph_schema):
        """Test complex graph detection."""
        analysis = SchemaAnalysis(schema=sample_graph_schema, complexity_score=8.5)

        assert not analysis.is_simple_graph
        assert analysis.is_complex_graph

    def test_moderate_complexity(self, sample_graph_schema):
        """Test moderate complexity graph."""
        analysis = SchemaAnalysis(schema=sample_graph_schema, complexity_score=5.0)

        assert not analysis.is_simple_graph
        assert not analysis.is_complex_graph

    def test_with_all_fields(self, sample_graph_schema):
        """Test analysis with all fields populated."""
        analysis = SchemaAnalysis(
            schema=sample_graph_schema,
            description="Test graph",
            domain="testing",
            key_entities=["users", "products"],
            key_relationships=["follows"],
            suggested_analyses=[
                {"type": "pagerank", "title": "PageRank", "reason": "Test"}
            ],
            complexity_score=5.0,
        )

        assert analysis.description == "Test graph"
        assert analysis.domain == "testing"
        assert len(analysis.key_entities) == 2
        assert len(analysis.key_relationships) == 1
        assert len(analysis.suggested_analyses) == 1
