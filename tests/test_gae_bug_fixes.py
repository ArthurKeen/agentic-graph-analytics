"""
Tests for GAE execution bug fixes.

These tests verify the fixes for three critical bugs:
1. Result field names use standard algorithm names (not template names)
2. Collection restriction is enforced (no excluded collections in results)
3. WCC computes actual components (not just vertex IDs)
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from graph_analytics_ai.gae_orchestrator import (
    AnalysisConfig,
    AnalysisResult,
    AnalysisStatus,
    GAEOrchestrator,
    ALGORITHM_RESULT_FIELDS,
)


class TestBugFix1_StandardFieldNames:
    """Test that result field names use standard algorithm names."""

    def test_wcc_uses_component_field(self):
        """WCC results should use 'component' field name."""
        config = AnalysisConfig(
            name="Test WCC Analysis",
            algorithm="wcc",
            vertex_collections=["users"],
            edge_collections=["friends"],
        )

        assert config.result_field == "component"
        assert config.result_field != "wcc_Test WCC Analysis"

    def test_pagerank_uses_rank_field(self):
        """PageRank results should use 'rank' field name."""
        config = AnalysisConfig(
            name="Product Demand",
            algorithm="pagerank",
            vertex_collections=["products"],
            edge_collections=["related"],
        )

        assert config.result_field == "rank"

    def test_scc_uses_component_field(self):
        """SCC results should use 'component' field name."""
        config = AnalysisConfig(
            name="Strongly Connected",
            algorithm="scc",
            vertex_collections=["nodes"],
            edge_collections=["edges"],
        )

        assert config.result_field == "component"

    def test_label_propagation_uses_community_field(self):
        """Label Propagation results should use 'community' field name."""
        config = AnalysisConfig(
            name="Community Detection",
            algorithm="label_propagation",
            vertex_collections=["users"],
            edge_collections=["follows"],
        )

        assert config.result_field == "community"

    def test_betweenness_uses_centrality_field(self):
        """Betweenness results should use 'centrality' field name."""
        config = AnalysisConfig(
            name="Influence Analysis",
            algorithm="betweenness",
            vertex_collections=["users"],
            edge_collections=["interactions"],
        )

        assert config.result_field == "centrality"

    def test_custom_result_field_is_preserved(self):
        """If user specifies result_field explicitly, it should be preserved."""
        config = AnalysisConfig(
            name="Custom Analysis",
            algorithm="wcc",
            result_field="my_custom_field",
            vertex_collections=["users"],
            edge_collections=["friends"],
        )

        assert config.result_field == "my_custom_field"

    def test_algorithm_result_fields_constant(self):
        """Verify ALGORITHM_RESULT_FIELDS constant is defined correctly."""
        assert ALGORITHM_RESULT_FIELDS["wcc"] == "component"
        assert ALGORITHM_RESULT_FIELDS["scc"] == "component"
        assert ALGORITHM_RESULT_FIELDS["pagerank"] == "rank"
        assert ALGORITHM_RESULT_FIELDS["label_propagation"] == "community"
        assert ALGORITHM_RESULT_FIELDS["betweenness"] == "centrality"


class TestBugFix2_CollectionRestriction:
    """Test that collection restriction is enforced in load_graph."""

    def test_load_graph_called_with_graph_name_none(self):
        """Verify load_graph is called with graph_name=None to force collection-based loading."""
        orchestrator = GAEOrchestrator(verbose=False)

        # Mock the connections
        orchestrator.gae = Mock()
        orchestrator.db = Mock()
        orchestrator.db.properties.return_value = {"sharding": "none"}

        # Mock load_graph to return success
        orchestrator.gae.load_graph.return_value = {
            "graph_id": "test_graph_123",
            "job_id": "job_123",
        }

        # Mock the orchestrator's _wait_for_job method
        orchestrator._wait_for_job = Mock(return_value={"status": "completed"})

        orchestrator.gae.get_graph.return_value = {
            "vertex_count": 1000,
            "edge_count": 5000,
        }

        # Create config with specific collections
        config = AnalysisConfig(
            name="Test Analysis",
            algorithm="wcc",
            vertex_collections=["Device", "IP"],
            edge_collections=["connects"],
        )

        result = AnalysisResult(
            config=config, status=AnalysisStatus.PENDING, start_time=datetime.now()
        )

        # Call _load_graph
        orchestrator._load_graph(result)

        # Verify load_graph was called with graph_name=None
        orchestrator.gae.load_graph.assert_called_once()
        call_kwargs = orchestrator.gae.load_graph.call_args.kwargs

        assert call_kwargs["graph_name"] is None, "graph_name should be explicitly None"
        assert call_kwargs["vertex_collections"] == ["Device", "IP"]
        assert call_kwargs["edge_collections"] == ["connects"]


class TestBugFix3_ValidationLogic:
    """Test the result validation logic."""

    def test_validation_detects_missing_standard_field(self):
        """Validation should fail if standard field is missing."""
        orchestrator = GAEOrchestrator(verbose=False)
        orchestrator.db = Mock()

        # Mock collection with wrong field name
        mock_collection = Mock()
        mock_cursor = [
            {"id": "Device/1", "wrong_field": "Device/1"},  # Should have 'component'
            {"id": "Device/2", "wrong_field": "Device/1"},
        ]
        mock_collection.all.return_value = iter(mock_cursor)
        orchestrator.db.collection.return_value = mock_collection

        config = AnalysisConfig(
            name="Test",
            algorithm="wcc",
            vertex_collections=["Device"],
            edge_collections=["connects"],
        )

        result = AnalysisResult(
            config=config,
            status=AnalysisStatus.COMPLETED,
            start_time=datetime.now(),
            results_stored=True,
            documents_updated=2,
        )

        # Should raise ValueError
        with pytest.raises(
            ValueError, match="Results missing expected field 'component'"
        ):
            orchestrator._validate_results(result)

    def test_validation_detects_invalid_components(self):
        """Validation should fail if every vertex is its own component."""
        orchestrator = GAEOrchestrator(verbose=False)
        orchestrator.db = Mock()

        # Mock collection where every vertex is its own component
        mock_collection = Mock()
        mock_cursor = [
            {"id": "Device/1", "component": "Device/1"},  # Same as ID - invalid!
            {"id": "Device/2", "component": "Device/2"},
            {"id": "Device/3", "component": "Device/3"},
        ]
        mock_collection.all.return_value = iter(mock_cursor)
        orchestrator.db.collection.return_value = mock_collection

        config = AnalysisConfig(
            name="Test",
            algorithm="wcc",
            vertex_collections=["Device"],
            edge_collections=["connects"],
        )

        result = AnalysisResult(
            config=config,
            status=AnalysisStatus.COMPLETED,
            start_time=datetime.now(),
            results_stored=True,
            documents_updated=3,
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="Every vertex is its own component"):
            orchestrator._validate_results(result)

    def test_validation_detects_excluded_collections(self):
        """Validation should fail if excluded collections appear in results."""
        orchestrator = GAEOrchestrator(verbose=False)
        orchestrator.db = Mock()

        # Mock collection with excluded collection (Publisher)
        mock_collection = Mock()
        mock_cursor = [
            {"id": "Device/1", "component": "Device/1"},
            {"id": "Publisher/999", "component": "Device/1"},  # EXCLUDED!
            {"id": "Device/2", "component": "Device/1"},
        ]
        mock_collection.all.return_value = iter(mock_cursor)
        orchestrator.db.collection.return_value = mock_collection

        config = AnalysisConfig(
            name="Test",
            algorithm="wcc",
            vertex_collections=["Device", "IP"],  # Publisher NOT in list
            edge_collections=["connects"],
        )

        result = AnalysisResult(
            config=config,
            status=AnalysisStatus.COMPLETED,
            start_time=datetime.now(),
            results_stored=True,
            documents_updated=3,
        )

        # Should raise ValueError
        with pytest.raises(
            ValueError, match="Results contain documents from excluded collections"
        ):
            orchestrator._validate_results(result)

    def test_validation_passes_with_valid_results(self):
        """Validation should pass with valid WCC results."""
        orchestrator = GAEOrchestrator(verbose=False)
        orchestrator.db = Mock()

        # Mock collection with valid WCC results
        mock_collection = Mock()
        mock_cursor = [
            {"id": "Device/1", "component": "Device/1"},
            {"id": "Device/2", "component": "Device/1"},  # Same component
            {"id": "Device/3", "component": "Device/1"},
            {"id": "Device/4", "component": "Device/4"},  # Different component
            {"id": "Device/5", "component": "Device/4"},
        ]
        mock_collection.all.return_value = iter(mock_cursor)
        orchestrator.db.collection.return_value = mock_collection

        config = AnalysisConfig(
            name="Test",
            algorithm="wcc",
            vertex_collections=["Device"],
            edge_collections=["connects"],
        )

        result = AnalysisResult(
            config=config,
            status=AnalysisStatus.COMPLETED,
            start_time=datetime.now(),
            results_stored=True,
            documents_updated=5,
        )

        # Should not raise
        orchestrator._validate_results(result)

    def test_validation_skipped_when_no_results(self):
        """Validation should be skipped if no results were stored."""
        orchestrator = GAEOrchestrator(verbose=False)

        config = AnalysisConfig(
            name="Test",
            algorithm="wcc",
            vertex_collections=["Device"],
            edge_collections=["connects"],
        )

        result = AnalysisResult(
            config=config,
            status=AnalysisStatus.COMPLETED,
            start_time=datetime.now(),
            results_stored=False,  # No results
            documents_updated=0,
        )

        # Should not raise (validation skipped)
        orchestrator._validate_results(result)


class TestIntegration_BugFixes:
    """Integration tests verifying all bug fixes work together."""

    def test_full_workflow_uses_standard_fields_and_validates(self):
        """Test that a full workflow uses standard fields and validates results."""
        # This would be a full integration test with real GAE
        # For now, just verify the components work together

        config = AnalysisConfig(
            name="Household Detection",
            algorithm="wcc",
            vertex_collections=["Device", "IP", "AppProduct"],
            edge_collections=["device_to_ip", "device_to_app"],
        )

        # Verify standard field name
        assert config.result_field == "component"

        # Verify validation would check for this field
        expected_field = ALGORITHM_RESULT_FIELDS.get(config.algorithm)
        assert expected_field == "component"

    def test_template_to_config_conversion_uses_standard_field(self):
        """Test that template → config conversion uses standard field names."""
        from graph_analytics_ai.ai.execution.executor import AnalysisExecutor
        from graph_analytics_ai.ai.templates.models import (
            AnalysisTemplate,
            AlgorithmParameters,
            AlgorithmType,
            TemplateConfig,
            EngineSize,
        )
        from graph_analytics_ai.gae_orchestrator import GAEOrchestrator
        from unittest.mock import Mock

        # Create a mock orchestrator
        mock_orchestrator = Mock(spec=GAEOrchestrator)
        executor = AnalysisExecutor(orchestrator=mock_orchestrator)

        # Create a template with a human-readable name
        template = AnalysisTemplate(
            name="UC-S01: Household and Identity Resolution",  # Template name
            description="Identify household clusters",
            algorithm=AlgorithmParameters(
                algorithm=AlgorithmType.WCC, parameters={}  # Correct field name
            ),
            config=TemplateConfig(
                graph_name="premion_graph",
                vertex_collections=["Device", "IP"],
                edge_collections=["device_to_ip"],
                engine_size=EngineSize.SMALL,
                store_results=True,
                result_collection="uc_s01_results",
            ),
        )

        # Convert template to config
        config = executor._template_to_config(template)

        # Verify the config uses standard field name, NOT template name
        assert (
            config.result_field == "component"
        ), f"Expected 'component' but got '{config.result_field}'"
        assert (
            config.result_field != template.name
        ), f"result_field should not be template name '{template.name}'"

        # Also verify other fields are correct
        assert config.name == template.name  # Name can be human-readable
        assert config.algorithm == "wcc"
        assert config.target_collection == "uc_s01_results"
