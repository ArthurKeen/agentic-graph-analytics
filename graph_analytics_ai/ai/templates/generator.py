"""
GAE template generator.

Converts use cases into executable GAE analysis templates.
"""

from typing import List, Optional, Dict, Any

from ..generation.use_cases import UseCase, UseCaseType
from ..schema.models import GraphSchema, SchemaAnalysis
from .models import (
    AnalysisTemplate,
    AlgorithmType,
    AlgorithmParameters,
    TemplateConfig,
    EngineSize,
    DEFAULT_ALGORITHM_PARAMS,
    recommend_engine_size
)


# Mapping from use case types to algorithm types
USE_CASE_TO_ALGORITHM = {
    UseCaseType.CENTRALITY: [
        AlgorithmType.PAGERANK,
        AlgorithmType.BETWEENNESS_CENTRALITY,
        AlgorithmType.CLOSENESS_CENTRALITY
    ],
    UseCaseType.COMMUNITY: [
        AlgorithmType.LOUVAIN,
        AlgorithmType.LABEL_PROPAGATION,
        AlgorithmType.WCC
    ],
    UseCaseType.PATHFINDING: [
        AlgorithmType.SHORTEST_PATH
    ],
    UseCaseType.PATTERN: [
        AlgorithmType.PAGERANK,  # Can help identify patterns
        AlgorithmType.LOUVAIN
    ],
    UseCaseType.ANOMALY: [
        AlgorithmType.BETWEENNESS_CENTRALITY,  # Unusual connections
        AlgorithmType.PAGERANK  # Unusual importance
    ],
    UseCaseType.RECOMMENDATION: [
        AlgorithmType.SHORTEST_PATH,
        AlgorithmType.PAGERANK
    ],
    UseCaseType.SIMILARITY: [
        AlgorithmType.LOUVAIN,
        AlgorithmType.LABEL_PROPAGATION
    ]
}


class TemplateGenerator:
    """
    Generates GAE analysis templates from use cases.
    
    Converts high-level use case descriptions into executable
    GAE analysis configurations with optimized parameters.
    
    Example:
        >>> from graph_analytics_ai.ai.templates import TemplateGenerator
        >>> from graph_analytics_ai.ai.generation import generate_use_cases
        >>> 
        >>> generator = TemplateGenerator(graph_name="my_graph")
        >>> use_cases = generate_use_cases(requirements, schema_analysis)
        >>> templates = generator.generate_templates(use_cases, schema)
        >>> 
        >>> for template in templates:
        ...     print(f"{template.name}: {template.algorithm.algorithm.value}")
    """
    
    def __init__(
        self,
        graph_name: str = "ecommerce_graph",
        default_engine_size: EngineSize = EngineSize.SMALL,
        auto_optimize: bool = True
    ):
        """
        Initialize template generator.
        
        Args:
            graph_name: Name of the graph to analyze
            default_engine_size: Default engine size if not optimized
            auto_optimize: Whether to auto-optimize parameters
        """
        self.graph_name = graph_name
        self.default_engine_size = default_engine_size
        self.auto_optimize = auto_optimize
    
    def generate_templates(
        self,
        use_cases: List[UseCase],
        schema: Optional[GraphSchema] = None,
        schema_analysis: Optional[SchemaAnalysis] = None
    ) -> List[AnalysisTemplate]:
        """
        Generate analysis templates from use cases.
        
        Args:
            use_cases: List of use cases to convert
            schema: Optional graph schema for optimization
            schema_analysis: Optional schema analysis for insights
            
        Returns:
            List of analysis templates ready for execution
        """
        templates = []
        
        for use_case in use_cases:
            # Get suitable algorithms for this use case type
            algorithms = USE_CASE_TO_ALGORITHM.get(
                use_case.use_case_type,
                [AlgorithmType.PAGERANK]  # Default fallback
            )
            
            # Generate template for primary algorithm
            primary_algo = algorithms[0]
            template = self._create_template(
                use_case=use_case,
                algorithm_type=primary_algo,
                schema=schema,
                schema_analysis=schema_analysis
            )
            templates.append(template)
        
        return templates
    
    def _create_template(
        self,
        use_case: UseCase,
        algorithm_type: AlgorithmType,
        schema: Optional[GraphSchema] = None,
        schema_analysis: Optional[SchemaAnalysis] = None
    ) -> AnalysisTemplate:
        """Create a single analysis template."""
        
        # Get base parameters for algorithm
        params = DEFAULT_ALGORITHM_PARAMS.get(algorithm_type, {}).copy()
        
        # Optimize parameters if requested
        if self.auto_optimize and schema:
            params = self._optimize_parameters(
                algorithm_type=algorithm_type,
                params=params,
                schema=schema,
                schema_analysis=schema_analysis
            )
        
        # Create algorithm parameters
        algorithm = AlgorithmParameters(
            algorithm=algorithm_type,
            parameters=params
        )
        
        # Determine engine size
        engine_size = self._determine_engine_size(schema)
        
        # Extract collections from use case data needs
        vertex_collections, edge_collections = self._extract_collections(use_case)
        
        # Create template config
        config = TemplateConfig(
            graph_name=self.graph_name,
            vertex_collections=vertex_collections,
            edge_collections=edge_collections,
            engine_size=engine_size,
            store_results=True,
            result_collection=f"{use_case.id.lower().replace('-', '_')}_results"
        )
        
        # Estimate runtime (basic heuristic)
        estimated_runtime = self._estimate_runtime(
            algorithm_type=algorithm_type,
            schema=schema
        )
        
        # Create template
        template = AnalysisTemplate(
            name=f"{use_case.id}: {use_case.title}",
            description=use_case.description,
            algorithm=algorithm,
            config=config,
            use_case_id=use_case.id,
            estimated_runtime_seconds=estimated_runtime,
            metadata={
                "priority": use_case.priority.value,
                "use_case_type": use_case.use_case_type.value,
                "algorithms": use_case.graph_algorithms,
                "success_metrics": use_case.success_metrics
            }
        )
        
        return template
    
    def _optimize_parameters(
        self,
        algorithm_type: AlgorithmType,
        params: Dict[str, Any],
        schema: GraphSchema,
        schema_analysis: Optional[SchemaAnalysis] = None
    ) -> Dict[str, Any]:
        """
        Optimize algorithm parameters based on graph characteristics.
        
        Args:
            algorithm_type: Algorithm to optimize for
            params: Base parameters
            schema: Graph schema
            schema_analysis: Optional analysis for insights
            
        Returns:
            Optimized parameters
        """
        optimized = params.copy()
        
        # Get graph stats
        total_docs = schema.total_documents
        total_edges = schema.total_edges
        avg_degree = (2 * total_edges) / total_docs if total_docs > 0 else 0
        
        # Algorithm-specific optimizations
        if algorithm_type == AlgorithmType.PAGERANK:
            # Adjust iterations based on graph size
            if total_docs > 10000:
                optimized["max_iterations"] = 50  # Fewer for large graphs
            elif total_docs < 1000:
                optimized["max_iterations"] = 150  # More for small graphs
            
            # Adjust threshold based on density
            if avg_degree > 10:
                optimized["threshold"] = 0.0005  # Tighter for dense graphs
        
        elif algorithm_type == AlgorithmType.LOUVAIN:
            # Adjust resolution based on graph size
            if total_docs > 10000:
                optimized["resolution"] = 1.5  # Larger communities
            elif total_docs < 500:
                optimized["resolution"] = 0.5  # Smaller communities
            
            # Adjust min community size
            min_size = max(2, int(total_docs * 0.005))  # 0.5% of documents
            optimized["min_community_size"] = min_size
        
        elif algorithm_type == AlgorithmType.BETWEENNESS_CENTRALITY:
            # For very large graphs, might want to sample
            if total_docs > 50000:
                optimized["sample_size"] = 1000  # Sample nodes
        
        return optimized
    
    def _determine_engine_size(self, schema: Optional[GraphSchema]) -> EngineSize:
        """Determine appropriate engine size for the graph."""
        if not schema:
            return self.default_engine_size
        
        return recommend_engine_size(
            vertex_count=schema.total_documents,
            edge_count=schema.total_edges
        )
    
    def _extract_collections(self, use_case: UseCase) -> tuple:
        """Extract vertex and edge collections from use case."""
        vertex_collections = []
        edge_collections = []
        
        # Parse data needs
        for need in use_case.data_needs:
            need_lower = need.lower()
            
            # Common patterns
            if "user" in need_lower or "customer" in need_lower:
                vertex_collections.append("users")
            if "product" in need_lower:
                vertex_collections.append("products")
            if "category" in need_lower or "categories" in need_lower:
                vertex_collections.append("categories")
            
            if "purchase" in need_lower or "buy" in need_lower or "transaction" in need_lower:
                edge_collections.append("purchased")
            if "view" in need_lower or "browse" in need_lower:
                edge_collections.append("viewed")
            if "rating" in need_lower or "review" in need_lower:
                edge_collections.append("rated")
            if "follow" in need_lower or "social" in need_lower:
                edge_collections.append("follows")
        
        # Remove duplicates while preserving order
        vertex_collections = list(dict.fromkeys(vertex_collections))
        edge_collections = list(dict.fromkeys(edge_collections))
        
        return vertex_collections, edge_collections
    
    def _estimate_runtime(
        self,
        algorithm_type: AlgorithmType,
        schema: Optional[GraphSchema]
    ) -> Optional[float]:
        """Estimate runtime in seconds (very rough heuristic)."""
        if not schema:
            return None
        
        n = schema.total_documents
        m = schema.total_edges
        
        # Very rough complexity estimates
        if algorithm_type == AlgorithmType.PAGERANK:
            # O(iterations * m)
            return max(1.0, (n + m) / 10000)  # ~10k elements per second
        
        elif algorithm_type == AlgorithmType.LOUVAIN:
            # O(m * log(n))
            import math
            return max(2.0, (m * math.log(max(n, 2))) / 5000)
        
        elif algorithm_type == AlgorithmType.SHORTEST_PATH:
            # Depends on start/end, but roughly O(n + m)
            return max(0.5, (n + m) / 20000)
        
        elif algorithm_type in (AlgorithmType.BETWEENNESS_CENTRALITY, AlgorithmType.CLOSENESS_CENTRALITY):
            # O(n * m) - can be slow
            return max(5.0, (n * m) / 100000)
        
        else:
            # Default estimate
            return max(1.0, (n + m) / 15000)


def generate_template(
    use_case: UseCase,
    graph_name: str = "ecommerce_graph",
    schema: Optional[GraphSchema] = None,
    algorithm_type: Optional[AlgorithmType] = None
) -> AnalysisTemplate:
    """
    Convenience function to generate a single template.
    
    Args:
        use_case: Use case to convert
        graph_name: Name of the graph
        schema: Optional schema for optimization
        algorithm_type: Optional specific algorithm (auto-detected if None)
        
    Returns:
        Analysis template
    """
    generator = TemplateGenerator(graph_name=graph_name)
    
    if algorithm_type is None:
        # Auto-detect algorithm
        algorithms = USE_CASE_TO_ALGORITHM.get(
            use_case.use_case_type,
            [AlgorithmType.PAGERANK]
        )
        algorithm_type = algorithms[0]
    
    return generator._create_template(
        use_case=use_case,
        algorithm_type=algorithm_type,
        schema=schema
    )

