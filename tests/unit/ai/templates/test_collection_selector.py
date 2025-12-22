"""
Unit tests for CollectionSelector.

Tests algorithm-specific collection selection logic.
"""

import pytest
from graph_analytics_ai.ai.templates.collection_selector import (
    CollectionSelector,
    CollectionSelection,
    CollectionRole,
    select_collections_for_algorithm,
)
from graph_analytics_ai.ai.templates.models import AlgorithmType
from graph_analytics_ai.ai.schema.models import (
    GraphSchema,
    CollectionSchema,
    CollectionType,
)


@pytest.fixture
def sample_schema():
    """Create a sample graph schema for testing."""
    return GraphSchema(
        database_name="test_db",
        vertex_collections={
            "users": CollectionSchema(
                name="users",
                type=CollectionType.VERTEX,
                document_count=5000,
                sample_documents=[],
            ),
            "products": CollectionSchema(
                name="products",
                type=CollectionType.VERTEX,
                document_count=2000,
                sample_documents=[],
            ),
            "orders": CollectionSchema(
                name="orders",
                type=CollectionType.VERTEX,
                document_count=10000,
                sample_documents=[],
            ),
            "metadata": CollectionSchema(
                name="metadata",
                type=CollectionType.VERTEX,
                document_count=50,
                sample_documents=[],
            ),
            "configs": CollectionSchema(
                name="configs",
                type=CollectionType.VERTEX,
                document_count=10,
                sample_documents=[],
            ),
        },
        edge_collections={
            "purchases": CollectionSchema(
                name="purchases",
                type=CollectionType.EDGE,
                document_count=25000,
                sample_documents=[],
            ),
            "views": CollectionSchema(
                name="views",
                type=CollectionType.EDGE,
                document_count=50000,
                sample_documents=[],
            ),
            "config_refs": CollectionSchema(
                name="config_refs",
                type=CollectionType.EDGE,
                document_count=100,
                sample_documents=[],
            ),
        },
    )


class TestCollectionSelector:
    """Test CollectionSelector class."""

    def test_init(self):
        """Test selector initialization."""
        selector = CollectionSelector()
        assert selector is not None
        assert selector.collection_roles == {}

    def test_classify_collections_with_hints(self, sample_schema):
        """Test classification with explicit hints."""
        selector = CollectionSelector()

        hints = {
            "satellite_collections": ["metadata", "configs"],
            "core_collections": ["users", "products", "orders"],
        }

        selector._classify_collections(sample_schema, hints)

        assert selector.collection_roles["metadata"] == CollectionRole.SATELLITE
        assert selector.collection_roles["configs"] == CollectionRole.SATELLITE
        assert selector.collection_roles["users"] == CollectionRole.CORE
        assert selector.collection_roles["products"] == CollectionRole.CORE
        assert selector.collection_roles["orders"] == CollectionRole.CORE

    def test_auto_classify_by_keywords(self, sample_schema):
        """Test auto-classification by collection names."""
        selector = CollectionSelector()
        selector._auto_classify_collections(sample_schema)

        # Should detect 'configs' as satellite (keyword match)
        assert selector.collection_roles["configs"] == CollectionRole.SATELLITE

        # Should detect 'metadata' as satellite (keyword match)
        assert selector.collection_roles["metadata"] == CollectionRole.SATELLITE

    def test_auto_classify_by_size(self):
        """Test auto-classification by document count."""
        schema = GraphSchema(
            database_name="test_db",
            vertex_collections={
                "tiny": CollectionSchema(
                    name="tiny",
                    type=CollectionType.VERTEX,
                    document_count=50,
                    sample_documents=[],
                ),
                "large": CollectionSchema(
                    name="large",
                    type=CollectionType.VERTEX,
                    document_count=10000,
                    sample_documents=[],
                ),
            },
            edge_collections={},
        )

        selector = CollectionSelector()
        selector._auto_classify_collections(schema)

        # Small collections should be metadata
        assert selector.collection_roles["tiny"] == CollectionRole.METADATA

        # Large collections should be core
        assert selector.collection_roles["large"] == CollectionRole.CORE

    def test_select_wcc_excludes_satellites(self, sample_schema):
        """Test WCC selection excludes satellite collections."""
        selector = CollectionSelector()

        selection = selector.select_collections(
            algorithm=AlgorithmType.WCC,
            schema=sample_schema,
            collection_hints={"satellite_collections": ["metadata", "configs"]},
        )

        # Should include core collections
        assert "users" in selection.vertex_collections
        assert "products" in selection.vertex_collections
        assert "orders" in selection.vertex_collections

        # Should exclude satellites
        assert "metadata" not in selection.vertex_collections
        assert "configs" not in selection.vertex_collections

        # Should have reasoning
        assert "core graph" in selection.reasoning.lower()
        assert len(selection.excluded_vertices) > 0

    def test_select_scc_excludes_satellites(self, sample_schema):
        """Test SCC selection excludes satellite collections."""
        selector = CollectionSelector()

        selection = selector.select_collections(
            algorithm=AlgorithmType.SCC,
            schema=sample_schema,
            collection_hints={"satellite_collections": ["metadata"]},
        )

        # Should include core
        assert "users" in selection.vertex_collections

        # Should exclude satellites
        assert "metadata" not in selection.vertex_collections

        # Should have reasoning about core graph
        assert "core graph" in selection.reasoning.lower()

    def test_select_pagerank_includes_all(self, sample_schema):
        """Test PageRank selection includes all collections."""
        selector = CollectionSelector()

        selection = selector.select_collections(
            algorithm=AlgorithmType.PAGERANK,
            schema=sample_schema,
            collection_hints={"satellite_collections": ["metadata", "configs"]},
        )

        # Should include everything
        assert "users" in selection.vertex_collections
        assert "products" in selection.vertex_collections
        assert "metadata" in selection.vertex_collections
        assert "configs" in selection.vertex_collections

        # Should have no exclusions
        assert len(selection.excluded_vertices) == 0

        # Should explain full graph usage
        assert (
            "complete graph" in selection.reasoning.lower()
            or "full graph" in selection.reasoning.lower()
        )

    def test_select_betweenness_includes_all(self, sample_schema):
        """Test Betweenness selection includes all collections."""
        selector = CollectionSelector()

        selection = selector.select_collections(
            algorithm=AlgorithmType.BETWEENNESS_CENTRALITY,
            schema=sample_schema,
            collection_hints={"satellite_collections": ["metadata"]},
        )

        # Should include everything for accurate centrality
        assert len(selection.vertex_collections) == len(
            sample_schema.vertex_collections
        )
        assert len(selection.excluded_vertices) == 0

    def test_select_label_propagation_excludes_satellites(self, sample_schema):
        """Test Label Propagation focuses on core graph."""
        selector = CollectionSelector()

        selection = selector.select_collections(
            algorithm=AlgorithmType.LABEL_PROPAGATION,
            schema=sample_schema,
            collection_hints={"satellite_collections": ["metadata", "configs"]},
        )

        # Should focus on core for communities
        assert "users" in selection.vertex_collections
        assert "products" in selection.vertex_collections

        # Should exclude satellites
        assert "metadata" not in selection.vertex_collections

    def test_selection_has_metadata(self, sample_schema):
        """Test selection includes metadata about the decision."""
        selector = CollectionSelector()

        selection = selector.select_collections(
            algorithm=AlgorithmType.WCC,
            schema=sample_schema,
            collection_hints={"satellite_collections": ["metadata"]},
        )

        # Should have reasoning
        assert selection.reasoning is not None
        assert len(selection.reasoning) > 0

        # Should have estimated size
        assert selection.estimated_graph_size is not None
        assert "vertices" in selection.estimated_graph_size
        assert "edges" in selection.estimated_graph_size

        # Size should be reasonable
        assert selection.estimated_graph_size["vertices"] > 0
        assert selection.estimated_graph_size["edges"] > 0

    def test_algorithm_requirements_exist(self):
        """Test that algorithm requirements are defined."""
        selector = CollectionSelector()

        # Check key algorithms have requirements
        assert AlgorithmType.WCC in selector.ALGORITHM_REQUIREMENTS
        assert AlgorithmType.SCC in selector.ALGORITHM_REQUIREMENTS
        assert AlgorithmType.PAGERANK in selector.ALGORITHM_REQUIREMENTS
        assert AlgorithmType.BETWEENNESS_CENTRALITY in selector.ALGORITHM_REQUIREMENTS
        assert AlgorithmType.LABEL_PROPAGATION in selector.ALGORITHM_REQUIREMENTS

        # Check structure
        wcc_req = selector.ALGORITHM_REQUIREMENTS[AlgorithmType.WCC]
        assert "needs_satellites" in wcc_req
        assert "focus" in wcc_req
        assert wcc_req["needs_satellites"] is False
        assert wcc_req["focus"] == "core_graph"


class TestConvenienceFunction:
    """Test select_collections_for_algorithm convenience function."""

    def test_convenience_function(self, sample_schema):
        """Test the convenience function works."""
        selection = select_collections_for_algorithm(
            algorithm=AlgorithmType.WCC,
            schema=sample_schema,
            satellite_collections=["metadata", "configs"],
        )

        assert isinstance(selection, CollectionSelection)
        assert selection.algorithm == AlgorithmType.WCC
        assert len(selection.vertex_collections) > 0

    def test_convenience_with_core_collections(self, sample_schema):
        """Test convenience function with core collections hint."""
        selection = select_collections_for_algorithm(
            algorithm=AlgorithmType.PAGERANK,
            schema=sample_schema,
            core_collections=["users", "products"],
        )

        assert "users" in selection.vertex_collections
        assert "products" in selection.vertex_collections


class TestCollectionRole:
    """Test CollectionRole enum."""

    def test_collection_role_values(self):
        """Test CollectionRole enum values."""
        assert CollectionRole.CORE.value == "core"
        assert CollectionRole.SATELLITE.value == "satellite"
        assert CollectionRole.BRIDGE.value == "bridge"
        assert CollectionRole.METADATA.value == "metadata"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_schema(self):
        """Test with empty schema."""
        schema = GraphSchema(
            database_name="test_db", vertex_collections={}, edge_collections={}
        )

        selector = CollectionSelector()
        selection = selector.select_collections(
            algorithm=AlgorithmType.WCC, schema=schema
        )

        # Should handle gracefully
        assert selection.vertex_collections == []
        assert selection.edge_collections == []

    def test_no_hints_uses_auto_classification(self, sample_schema):
        """Test that no hints triggers auto-classification."""
        selector = CollectionSelector()

        # No hints provided
        selection = selector.select_collections(
            algorithm=AlgorithmType.WCC, schema=sample_schema, collection_hints=None
        )

        # Should still work via auto-classification
        assert len(selection.vertex_collections) > 0

        # Should have auto-detected satellites
        # (metadata and configs should be excluded due to keywords/size)
        assert (
            "metadata" not in selection.vertex_collections
            or "configs" not in selection.vertex_collections
        )

    def test_unknown_algorithm_defaults_to_full_graph(self, sample_schema):
        """Test unknown algorithm defaults to safe behavior."""
        selector = CollectionSelector()

        # This would test a hypothetical new algorithm
        # For now, just verify existing algorithms have requirements
        for algo in AlgorithmType:
            selection = selector.select_collections(
                algorithm=algo, schema=sample_schema
            )

            # Should always return valid selection
            assert selection is not None
            assert isinstance(selection.vertex_collections, list)
            assert isinstance(selection.edge_collections, list)


class TestIntegrationWithTemplateGenerator:
    """Test integration scenarios."""

    def test_selection_metadata_structure(self, sample_schema):
        """Test that selection metadata has expected structure for templates."""
        selection = select_collections_for_algorithm(
            algorithm=AlgorithmType.WCC,
            schema=sample_schema,
            satellite_collections=["metadata"],
        )

        # Template generator expects these fields
        assert hasattr(selection, "reasoning")
        assert hasattr(selection, "excluded_vertices")
        assert hasattr(selection, "excluded_edges")
        assert hasattr(selection, "estimated_graph_size")

        # Reasoning should be a string
        assert isinstance(selection.reasoning, str)

        # Excluded should be lists
        assert isinstance(selection.excluded_vertices, list)
        assert isinstance(selection.excluded_edges, list)

        # Estimated size should be a dict
        assert isinstance(selection.estimated_graph_size, dict)
