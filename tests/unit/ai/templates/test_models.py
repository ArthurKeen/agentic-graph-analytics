"""Tests for template models."""

import pytest
from graph_analytics_ai.ai.templates.models import (
    AlgorithmType,
    EngineSize,
    AlgorithmParameters,
    TemplateConfig,
    AnalysisTemplate,
    DEFAULT_ALGORITHM_PARAMS,
    recommend_engine_size
)


class TestAlgorithmType:
    """Tests for AlgorithmType enum."""
    
    def test_enum_values(self):
        """Test that all algorithm types have correct values."""
        assert AlgorithmType.PAGERANK.value == "pagerank"
        assert AlgorithmType.LOUVAIN.value == "louvain"
        assert AlgorithmType.SHORTEST_PATH.value == "shortest_path"
        assert AlgorithmType.BETWEENNESS_CENTRALITY.value == "betweenness_centrality"
        assert AlgorithmType.CLOSENESS_CENTRALITY.value == "closeness_centrality"
        assert AlgorithmType.LABEL_PROPAGATION.value == "label_propagation"
        assert AlgorithmType.WCC.value == "wcc"
        assert AlgorithmType.SCC.value == "scc"
    
    def test_enum_count(self):
        """Test that all expected algorithms are present."""
        assert len(AlgorithmType) == 8


class TestEngineSize:
    """Tests for EngineSize enum."""
    
    def test_enum_values(self):
        """Test that all engine sizes have correct values."""
        assert EngineSize.XSMALL.value == "xsmall"
        assert EngineSize.SMALL.value == "small"
        assert EngineSize.MEDIUM.value == "medium"
        assert EngineSize.LARGE.value == "large"
        assert EngineSize.XLARGE.value == "xlarge"
    
    def test_enum_count(self):
        """Test that all expected sizes are present."""
        assert len(EngineSize) == 5


class TestAlgorithmParameters:
    """Tests for AlgorithmParameters dataclass."""
    
    def test_init_default(self):
        """Test initialization with default parameters."""
        params = AlgorithmParameters(algorithm=AlgorithmType.PAGERANK)
        
        assert params.algorithm == AlgorithmType.PAGERANK
        assert params.parameters == {}
    
    def test_init_with_params(self):
        """Test initialization with custom parameters."""
        custom_params = {"threshold": 0.001, "max_iterations": 50}
        params = AlgorithmParameters(
            algorithm=AlgorithmType.PAGERANK,
            parameters=custom_params
        )
        
        assert params.algorithm == AlgorithmType.PAGERANK
        assert params.parameters == custom_params
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        params = AlgorithmParameters(
            algorithm=AlgorithmType.LOUVAIN,
            parameters={"resolution": 1.5}
        )
        
        result = params.to_dict()
        
        assert result["algorithm"] == "louvain"
        assert result["parameters"] == {"resolution": 1.5}


class TestTemplateConfig:
    """Tests for TemplateConfig dataclass."""
    
    def test_init_minimal(self):
        """Test initialization with minimal parameters."""
        config = TemplateConfig(graph_name="test_graph")
        
        assert config.graph_name == "test_graph"
        assert config.vertex_collections == []
        assert config.edge_collections == []
        assert config.engine_size == EngineSize.SMALL
        assert config.store_results is True
        assert config.result_collection is None
    
    def test_init_full(self):
        """Test initialization with all parameters."""
        config = TemplateConfig(
            graph_name="my_graph",
            vertex_collections=["users", "products"],
            edge_collections=["purchased"],
            engine_size=EngineSize.LARGE,
            store_results=False,
            result_collection="my_results"
        )
        
        assert config.graph_name == "my_graph"
        assert config.vertex_collections == ["users", "products"]
        assert config.edge_collections == ["purchased"]
        assert config.engine_size == EngineSize.LARGE
        assert config.store_results is False
        assert config.result_collection == "my_results"
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = TemplateConfig(
            graph_name="test_graph",
            vertex_collections=["users"],
            edge_collections=["follows"],
            engine_size=EngineSize.MEDIUM,
            store_results=True,
            result_collection="results"
        )
        
        result = config.to_dict()
        
        assert result["graph_name"] == "test_graph"
        assert result["vertex_collections"] == ["users"]
        assert result["edge_collections"] == ["follows"]
        assert result["engine_size"] == "medium"
        assert result["store_results"] is True
        assert result["result_collection"] == "results"


class TestAnalysisTemplate:
    """Tests for AnalysisTemplate dataclass."""
    
    @pytest.fixture
    def sample_template(self):
        """Create a sample template for testing."""
        algorithm = AlgorithmParameters(
            algorithm=AlgorithmType.PAGERANK,
            parameters={"threshold": 0.0001}
        )
        
        config = TemplateConfig(
            graph_name="test_graph",
            vertex_collections=["users"],
            edge_collections=["follows"]
        )
        
        return AnalysisTemplate(
            name="Test Analysis",
            description="Test description",
            algorithm=algorithm,
            config=config,
            use_case_id="UC-001",
            estimated_runtime_seconds=10.5,
            metadata={"priority": "high"}
        )
    
    def test_init(self, sample_template):
        """Test template initialization."""
        assert sample_template.name == "Test Analysis"
        assert sample_template.description == "Test description"
        assert sample_template.algorithm.algorithm == AlgorithmType.PAGERANK
        assert sample_template.config.graph_name == "test_graph"
        assert sample_template.use_case_id == "UC-001"
        assert sample_template.estimated_runtime_seconds == 10.5
        assert sample_template.metadata == {"priority": "high"}
    
    def test_to_dict(self, sample_template):
        """Test conversion to dictionary."""
        result = sample_template.to_dict()
        
        assert result["name"] == "Test Analysis"
        assert result["description"] == "Test description"
        assert result["algorithm"]["algorithm"] == "pagerank"
        assert result["config"]["graph_name"] == "test_graph"
        assert result["use_case_id"] == "UC-001"
        assert result["estimated_runtime_seconds"] == 10.5
        assert result["metadata"] == {"priority": "high"}
    
    def test_to_analysis_config(self, sample_template):
        """Test conversion to analysis config format."""
        result = sample_template.to_analysis_config()
        
        assert result["name"] == "Test Analysis"
        assert result["graph"] == "test_graph"
        assert result["algorithm"] == "pagerank"
        assert result["params"] == {"threshold": 0.0001}
        assert result["vertex_collections"] == ["users"]
        assert result["edge_collections"] == ["follows"]
        assert result["engine_size"] == "small"
        assert result["store_results"] is True
        assert result["result_collection"] is None
    
    def test_minimal_template(self):
        """Test template with minimal required fields."""
        algorithm = AlgorithmParameters(algorithm=AlgorithmType.WCC)
        config = TemplateConfig(graph_name="minimal_graph")
        
        template = AnalysisTemplate(
            name="Minimal",
            description="Minimal template",
            algorithm=algorithm,
            config=config
        )
        
        assert template.use_case_id is None
        assert template.estimated_runtime_seconds is None
        assert template.metadata == {}


class TestDefaultAlgorithmParams:
    """Tests for DEFAULT_ALGORITHM_PARAMS constant."""
    
    def test_pagerank_defaults(self):
        """Test PageRank default parameters."""
        params = DEFAULT_ALGORITHM_PARAMS[AlgorithmType.PAGERANK]
        
        assert "threshold" in params
        assert "max_iterations" in params
        assert "damping_factor" in params
        assert params["damping_factor"] == 0.85
    
    def test_louvain_defaults(self):
        """Test Louvain default parameters."""
        params = DEFAULT_ALGORITHM_PARAMS[AlgorithmType.LOUVAIN]
        
        assert "resolution" in params
        assert "min_community_size" in params
        assert params["resolution"] == 1.0
    
    def test_shortest_path_defaults(self):
        """Test shortest path default parameters."""
        params = DEFAULT_ALGORITHM_PARAMS[AlgorithmType.SHORTEST_PATH]
        
        assert "direction" in params
        assert params["direction"] == "outbound"
    
    def test_centrality_defaults(self):
        """Test centrality algorithm defaults."""
        betweenness = DEFAULT_ALGORITHM_PARAMS[AlgorithmType.BETWEENNESS_CENTRALITY]
        assert "normalized" in betweenness
        assert betweenness["normalized"] is True
        
        closeness = DEFAULT_ALGORITHM_PARAMS[AlgorithmType.CLOSENESS_CENTRALITY]
        assert "normalized" in closeness
        assert closeness["normalized"] is True
    
    def test_label_propagation_defaults(self):
        """Test label propagation defaults."""
        params = DEFAULT_ALGORITHM_PARAMS[AlgorithmType.LABEL_PROPAGATION]
        
        assert "max_iterations" in params
        assert params["max_iterations"] == 100
    
    def test_wcc_scc_defaults(self):
        """Test WCC and SCC defaults (empty)."""
        assert DEFAULT_ALGORITHM_PARAMS[AlgorithmType.WCC] == {}
        assert DEFAULT_ALGORITHM_PARAMS[AlgorithmType.SCC] == {}
    
    def test_all_algorithms_have_defaults(self):
        """Test that all algorithm types have default parameters."""
        for algo_type in AlgorithmType:
            assert algo_type in DEFAULT_ALGORITHM_PARAMS


class TestRecommendEngineSize:
    """Tests for recommend_engine_size function."""
    
    def test_xsmall_graph(self):
        """Test recommendation for very small graphs."""
        size = recommend_engine_size(vertex_count=100, edge_count=200)
        assert size == EngineSize.XSMALL
    
    def test_small_graph(self):
        """Test recommendation for small graphs."""
        size = recommend_engine_size(vertex_count=1000, edge_count=2000)
        assert size == EngineSize.SMALL
    
    def test_medium_graph(self):
        """Test recommendation for medium graphs."""
        size = recommend_engine_size(vertex_count=10000, edge_count=50000)
        assert size == EngineSize.MEDIUM
    
    def test_large_graph(self):
        """Test recommendation for large graphs."""
        size = recommend_engine_size(vertex_count=100000, edge_count=500000)
        assert size == EngineSize.LARGE
    
    def test_xlarge_graph(self):
        """Test recommendation for very large graphs."""
        size = recommend_engine_size(vertex_count=1000000, edge_count=5000000)
        assert size == EngineSize.XLARGE
    
    def test_boundary_cases(self):
        """Test recommendations at boundary values."""
        # Just under 1000 total elements
        size = recommend_engine_size(vertex_count=500, edge_count=499)
        assert size == EngineSize.XSMALL
        
        # Exactly 1000 total elements
        size = recommend_engine_size(vertex_count=500, edge_count=500)
        assert size == EngineSize.SMALL
        
        # Just under 10000 total elements
        size = recommend_engine_size(vertex_count=5000, edge_count=4999)
        assert size == EngineSize.SMALL
        
        # Exactly 10000 total elements
        size = recommend_engine_size(vertex_count=5000, edge_count=5000)
        assert size == EngineSize.MEDIUM
    
    def test_zero_vertices(self):
        """Test with zero vertices."""
        size = recommend_engine_size(vertex_count=0, edge_count=100)
        assert size == EngineSize.XSMALL
    
    def test_zero_edges(self):
        """Test with zero edges."""
        size = recommend_engine_size(vertex_count=100, edge_count=0)
        assert size == EngineSize.XSMALL
    
    def test_sparse_large_graph(self):
        """Test sparse graph with many vertices but few edges."""
        size = recommend_engine_size(vertex_count=50000, edge_count=1000)
        assert size == EngineSize.MEDIUM
    
    def test_dense_small_graph(self):
        """Test dense graph with few vertices but many edges."""
        size = recommend_engine_size(vertex_count=100, edge_count=50000)
        assert size == EngineSize.MEDIUM

