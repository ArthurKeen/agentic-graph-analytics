"""Tests for template models."""

from graph_analytics_ai.ai.templates.models import (
    AlgorithmType,
    EngineSize,
    AlgorithmParameters,
    TemplateConfig,
    AnalysisTemplate,
    DEFAULT_ALGORITHM_PARAMS,
    recommend_engine_size,
)


class TestAlgorithmType:
    """Tests for AlgorithmType enum."""

    def test_algorithm_types_exist(self):
        """Test that all supported algorithm types exist."""
        assert AlgorithmType.PAGERANK.value == "pagerank"
        assert AlgorithmType.LABEL_PROPAGATION.value == "label_propagation"
        assert AlgorithmType.BETWEENNESS_CENTRALITY.value == "betweenness"
        assert AlgorithmType.WCC.value == "wcc"
        assert AlgorithmType.SCC.value == "scc"

    def test_algorithm_type_count(self):
        """Test that we have the expected number of algorithm types."""
        # Only 5 algorithms are currently implemented and working
        assert len(AlgorithmType) == 5


class TestEngineSize:
    """Tests for EngineSize enum."""

    def test_engine_sizes_exist(self):
        """Test that all expected engine sizes exist."""
        assert EngineSize.XSMALL.value == "xsmall"
        assert EngineSize.SMALL.value == "small"
        assert EngineSize.MEDIUM.value == "medium"
        assert EngineSize.LARGE.value == "large"
        assert EngineSize.XLARGE.value == "xlarge"

    def test_engine_size_count(self):
        """Test that we have the expected number of engine sizes."""
        assert len(EngineSize) == 5


class TestAlgorithmParameters:
    """Tests for AlgorithmParameters model."""

    def test_init_minimal(self):
        """Test initialization with minimal parameters."""
        params = AlgorithmParameters(algorithm=AlgorithmType.PAGERANK)

        assert params.algorithm == AlgorithmType.PAGERANK
        assert params.parameters == {}

    def test_init_with_parameters(self):
        """Test initialization with parameters."""
        params = AlgorithmParameters(
            algorithm=AlgorithmType.PAGERANK,
            parameters={"damping_factor": 0.85, "max_iterations": 100},
        )

        assert params.algorithm == AlgorithmType.PAGERANK
        assert params.parameters == {"damping_factor": 0.85, "max_iterations": 100}

    def test_to_dict(self):
        """Test conversion to dictionary."""
        params = AlgorithmParameters(
            algorithm=AlgorithmType.LABEL_PROPAGATION,
            parameters={"maximum_supersteps": 100},
        )

        result = params.to_dict()

        assert result == {
            "algorithm": "label_propagation",
            "parameters": {"maximum_supersteps": 100},
        }


class TestTemplateConfig:
    """Tests for TemplateConfig model."""

    def test_init_minimal(self):
        """Test initialization with minimal parameters."""
        config = TemplateConfig(graph_name="test_graph")

        assert config.graph_name == "test_graph"
        assert config.vertex_collections == []
        assert config.edge_collections == []
        assert config.engine_size == EngineSize.SMALL
        assert config.store_results is True
        assert config.result_collection is None

    def test_init_with_all_params(self):
        """Test initialization with all parameters."""
        config = TemplateConfig(
            graph_name="test_graph",
            vertex_collections=["users", "products"],
            edge_collections=["purchased", "viewed"],
            engine_size=EngineSize.MEDIUM,
            store_results=False,
            result_collection="my_results",
        )

        assert config.graph_name == "test_graph"
        assert config.vertex_collections == ["users", "products"]
        assert config.edge_collections == ["purchased", "viewed"]
        assert config.engine_size == EngineSize.MEDIUM
        assert config.store_results is False
        assert config.result_collection == "my_results"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = TemplateConfig(
            graph_name="test_graph",
            vertex_collections=["users"],
            edge_collections=["follows"],
            engine_size=EngineSize.LARGE,
            store_results=True,
            result_collection="results",
        )

        result = config.to_dict()

        assert result == {
            "graph_name": "test_graph",
            "vertex_collections": ["users"],
            "edge_collections": ["follows"],
            "engine_size": "large",
            "store_results": True,
            "result_collection": "results",
        }


class TestAnalysisTemplate:
    """Tests for AnalysisTemplate model."""

    def test_init_minimal(self):
        """Test initialization with minimal parameters."""
        algo_params = AlgorithmParameters(algorithm=AlgorithmType.PAGERANK)
        config = TemplateConfig(graph_name="test_graph")

        template = AnalysisTemplate(
            name="Test Analysis",
            description="Test description",
            algorithm=algo_params,
            config=config,
        )

        assert template.name == "Test Analysis"
        assert template.description == "Test description"
        assert template.algorithm == algo_params
        assert template.config == config
        assert template.use_case_id is None
        assert template.estimated_runtime_seconds is None
        assert template.metadata == {}

    def test_init_with_all_params(self):
        """Test initialization with all parameters."""
        algo_params = AlgorithmParameters(
            algorithm=AlgorithmType.PAGERANK, parameters={"damping_factor": 0.85}
        )
        config = TemplateConfig(graph_name="test_graph")

        template = AnalysisTemplate(
            name="PageRank Analysis",
            description="Identify influential nodes",
            algorithm=algo_params,
            config=config,
            use_case_id="UC-001",
            estimated_runtime_seconds=120.5,
            metadata={"priority": "high", "version": "1.0"},
        )

        assert template.name == "PageRank Analysis"
        assert template.use_case_id == "UC-001"
        assert template.estimated_runtime_seconds == 120.5
        assert template.metadata == {"priority": "high", "version": "1.0"}

    def test_to_dict(self):
        """Test conversion to dictionary."""
        template = AnalysisTemplate(
            name="test_analysis",
            description="Test description",
            algorithm=AlgorithmParameters(algorithm=AlgorithmType.WCC, parameters={}),
            config=TemplateConfig(
                graph_name="test_graph",
                vertex_collections=["users"],
                edge_collections=["follows"],
                engine_size=EngineSize.SMALL,
                store_results=True,
                result_collection="wcc_results",
            ),
            use_case_id="UC-002",
        )

        result = template.to_dict()

        assert result["name"] == "test_analysis"
        assert result["description"] == "Test description"
        assert result["algorithm"]["algorithm"] == "wcc"
        assert result["config"]["graph_name"] == "test_graph"
        assert result["use_case_id"] == "UC-002"
        assert result["use_case_id"] == "UC-002"

    def test_to_analysis_config(self):
        """Test conversion to AnalysisConfig format."""
        algo_params = AlgorithmParameters(
            algorithm=AlgorithmType.PAGERANK,
            parameters={"damping_factor": 0.85, "max_iterations": 100},
        )
        config = TemplateConfig(
            graph_name="my_graph",
            vertex_collections=["users"],
            edge_collections=["follows"],
            engine_size=EngineSize.SMALL,
            store_results=True,
            result_collection="pagerank_results",
        )

        template = AnalysisTemplate(
            name="Influence Analysis",
            description="Find influencers",
            algorithm=algo_params,
            config=config,
        )

        result = template.to_analysis_config()

        assert result["name"] == "Influence Analysis"
        assert result["graph"] == "my_graph"
        assert result["algorithm"] == "pagerank"
        assert result["params"] == {"damping_factor": 0.85, "max_iterations": 100}
        assert result["vertex_collections"] == ["users"]
        assert result["edge_collections"] == ["follows"]
        assert result["engine_size"] == "small"
        assert result["store_results"] is True
        assert result["result_collection"] == "pagerank_results"


class TestDefaultAlgorithmParams:
    """Tests for DEFAULT_ALGORITHM_PARAMS."""

    def test_pagerank_defaults(self):
        """Test PageRank default parameters."""
        params = DEFAULT_ALGORITHM_PARAMS[AlgorithmType.PAGERANK]

        assert "damping_factor" in params
        assert "maximum_supersteps" in params
        assert params["damping_factor"] == 0.85

    def test_label_propagation_defaults(self):
        """Test Label Propagation default parameters."""
        params = DEFAULT_ALGORITHM_PARAMS[AlgorithmType.LABEL_PROPAGATION]

        assert "start_label_attribute" in params
        assert "synchronous" in params
        assert "random_tiebreak" in params
        assert "maximum_supersteps" in params

    def test_betweenness_defaults(self):
        """Test Betweenness Centrality default parameters."""
        params = DEFAULT_ALGORITHM_PARAMS[AlgorithmType.BETWEENNESS_CENTRALITY]

        assert "maximum_supersteps" in params
        assert params["maximum_supersteps"] == 100

    def test_wcc_defaults(self):
        """Test WCC default parameters (should be empty)."""
        params = DEFAULT_ALGORITHM_PARAMS[AlgorithmType.WCC]
        assert params == {}

    def test_scc_defaults(self):
        """Test SCC default parameters (should be empty)."""
        params = DEFAULT_ALGORITHM_PARAMS[AlgorithmType.SCC]
        assert params == {}

    def test_all_algorithms_have_defaults(self):
        """Test that all algorithms have default parameters."""
        for algo_type in AlgorithmType:
            assert algo_type in DEFAULT_ALGORITHM_PARAMS


class TestRecommendEngineSize:
    """Tests for recommend_engine_size function."""

    def test_xsmall_for_tiny_graph(self):
        """Test XSMALL recommendation for tiny graphs."""
        size = recommend_engine_size(vertex_count=100, edge_count=200)
        assert size == EngineSize.XSMALL

    def test_small_for_small_graph(self):
        """Test SMALL recommendation for small graphs."""
        size = recommend_engine_size(vertex_count=2000, edge_count=5000)
        assert size == EngineSize.SMALL

    def test_medium_for_medium_graph(self):
        """Test MEDIUM recommendation for medium graphs."""
        size = recommend_engine_size(vertex_count=20000, edge_count=50000)
        assert size == EngineSize.MEDIUM

    def test_large_for_large_graph(self):
        """Test LARGE recommendation for large graphs."""
        size = recommend_engine_size(vertex_count=200000, edge_count=500000)
        assert size == EngineSize.LARGE

    def test_xlarge_for_huge_graph(self):
        """Test XLARGE recommendation for huge graphs."""
        size = recommend_engine_size(vertex_count=2000000, edge_count=5000000)
        assert size == EngineSize.XLARGE

    def test_boundary_conditions(self):
        """Test boundary conditions for size recommendations."""
        # Right at boundary (999 total)
        assert recommend_engine_size(500, 499) == EngineSize.XSMALL

        # Just over boundary (1000 total)
        assert recommend_engine_size(500, 500) == EngineSize.SMALL

        # Right at next boundary (9999 total)
        assert recommend_engine_size(5000, 4999) == EngineSize.SMALL

        # Just over next boundary (10000 total)
        assert recommend_engine_size(5000, 5000) == EngineSize.MEDIUM

    def test_zero_counts(self):
        """Test with zero vertex or edge counts."""
        size = recommend_engine_size(0, 0)
        assert size == EngineSize.XSMALL

    def test_only_vertices(self):
        """Test with only vertices, no edges."""
        size = recommend_engine_size(5000, 0)
        assert size == EngineSize.SMALL

    def test_only_edges(self):
        """Test with only edges, no vertices."""
        size = recommend_engine_size(0, 5000)
        assert size == EngineSize.SMALL
