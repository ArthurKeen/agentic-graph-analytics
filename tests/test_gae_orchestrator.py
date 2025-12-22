"""Tests for GAE orchestrator module."""

from unittest.mock import patch, MagicMock
from datetime import datetime

from graph_analytics_ai.gae_orchestrator import (
    GAEOrchestrator,
    AnalysisConfig,
    AnalysisResult,
    AnalysisStatus,
)


class TestAnalysisConfig:
    """Tests for AnalysisConfig dataclass."""

    def test_init_minimal(self, mock_env_amp):
        """Test initialization with minimal parameters."""
        config = AnalysisConfig(
            name="test_analysis",
            algorithm="pagerank",  # Now required (no default after Fix #1)
            vertex_collections=["v1"],
            edge_collections=["e1"],
        )

        assert config.name == "test_analysis"
        assert config.algorithm == "pagerank"
        assert config.engine_size == "e16"  # Default
        assert config.database is not None  # Set in __post_init__

    def test_init_with_params(self, mock_env_amp):
        """Test initialization with all parameters."""
        config = AnalysisConfig(
            name="test_analysis",
            description="Test description",
            vertex_collections=["v1", "v2"],
            edge_collections=["e1"],
            algorithm="wcc",
            engine_size="e32",
            algorithm_params={"custom": "param"},
            target_collection="results",
        )

        assert config.name == "test_analysis"
        assert config.description == "Test description"
        assert config.algorithm == "wcc"
        assert config.engine_size == "e32"
        assert config.algorithm_params == {"custom": "param"}

    def test_default_algorithm_params(self, mock_env_amp):
        """Test that default algorithm parameters are set."""
        config = AnalysisConfig(
            name="test",
            vertex_collections=["v1"],
            edge_collections=["e1"],
            algorithm="pagerank",
        )

        assert "damping_factor" in config.algorithm_params
        assert config.algorithm_params["damping_factor"] == 0.85


class TestGAEOrchestrator:
    """Tests for GAEOrchestrator class."""

    @patch("graph_analytics_ai.gae_orchestrator.get_gae_connection")
    @patch("graph_analytics_ai.gae_orchestrator.get_db_connection")
    def test_init(self, mock_db, mock_gae, mock_env_amp):
        """Test orchestrator initialization."""
        mock_gae_conn = MagicMock()
        mock_gae.return_value = mock_gae_conn
        mock_db_conn = MagicMock()
        mock_db.return_value = mock_db_conn

        orchestrator = GAEOrchestrator()

        # Connections should be lazy loaded
        assert orchestrator.gae is None
        assert orchestrator.db is None
        assert orchestrator.verbose is True

        # Initialize
        orchestrator._initialize_connections()
        assert orchestrator.gae is not None
        assert orchestrator.db is not None

    @patch("graph_analytics_ai.gae_orchestrator.get_gae_connection")
    @patch("graph_analytics_ai.gae_orchestrator.get_db_connection")
    def test_is_retryable_error(self, mock_db, mock_gae, mock_env_amp):
        """Test retryable error detection."""
        orchestrator = GAEOrchestrator()

        # Non-retryable errors
        assert orchestrator._is_retryable_error("ARANGO_GRAPH_TOKEN not set") is False
        assert orchestrator._is_retryable_error("Configuration error") is False

        # Retryable errors
        assert orchestrator._is_retryable_error("Connection timeout") is True
        assert orchestrator._is_retryable_error("Network error") is True

    @patch("graph_analytics_ai.gae_orchestrator.get_gae_connection")
    @patch("graph_analytics_ai.gae_orchestrator.get_db_connection")
    def test_estimate_cost(self, mock_db, mock_gae, mock_env_amp):
        """Test cost estimation."""
        orchestrator = GAEOrchestrator()

        config = AnalysisConfig(
            name="test",
            algorithm="pagerank",  # Now required (no default after Fix #1)
            vertex_collections=["v1"],
            edge_collections=["e1"],
            engine_size="e16",
        )

        cost = orchestrator.estimate_cost(config, estimated_runtime_minutes=30)

        # e16 costs $0.40/hour, 30 minutes = 0.5 hours = $0.20
        assert cost == 0.20

    @patch("graph_analytics_ai.gae_orchestrator.get_gae_connection")
    @patch("graph_analytics_ai.gae_orchestrator.get_db_connection")
    def test_get_summary(self, mock_db, mock_gae, mock_env_amp):
        """Test getting analysis summary."""
        orchestrator = GAEOrchestrator()

        config = AnalysisConfig(
            name="test_analysis",
            algorithm="wcc",  # Now required (no default after Fix #1)
            vertex_collections=["v1"],
            edge_collections=["e1"],
        )

        result = AnalysisResult(
            config=config,
            status=AnalysisStatus.COMPLETED,
            start_time=datetime.now(),
            vertex_count=1000,
            edge_count=5000,
            documents_updated=1000,
            estimated_cost_usd=0.10,
            duration_seconds=60.0,
        )

        summary = orchestrator.get_summary(result)

        assert "test_analysis" in summary
        assert "1,000" in summary
        assert "5,000" in summary
        assert "0.10" in summary
