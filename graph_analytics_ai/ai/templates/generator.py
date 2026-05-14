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
    LpgProjection,
    TemplateConfig,
    EngineSize,
    DEFAULT_ALGORITHM_PARAMS,
    recommend_engine_size,
)

# Mapping from use case types to algorithm types
# Only includes algorithms that are actually supported by GAE
USE_CASE_TO_ALGORITHM = {
    UseCaseType.CENTRALITY: [AlgorithmType.PAGERANK],
    UseCaseType.COMMUNITY: [
        AlgorithmType.WCC,
        AlgorithmType.SCC,
        AlgorithmType.LABEL_PROPAGATION,
    ],
    UseCaseType.PATHFINDING: [
        AlgorithmType.PAGERANK  # Best available for path/influence analysis
    ],
    UseCaseType.PATTERN: [
        AlgorithmType.WCC,  # For connected pattern detection
        AlgorithmType.LABEL_PROPAGATION,
    ],
    UseCaseType.ANOMALY: [
        AlgorithmType.WCC,  # For anomaly clusters
        AlgorithmType.PAGERANK,  # For anomalous influence patterns
    ],
    UseCaseType.RECOMMENDATION: [AlgorithmType.PAGERANK],  # For recommendation scoring
    UseCaseType.SIMILARITY: [AlgorithmType.WCC, AlgorithmType.LABEL_PROPAGATION],
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
        auto_optimize: bool = True,
        satellite_collections: Optional[List[str]] = None,
        core_collections: Optional[List[str]] = None,
    ):
        """
        Initialize template generator.

        Args:
            graph_name: Name of the graph to analyze
            default_engine_size: Default engine size if not optimized
            auto_optimize: Whether to auto-optimize parameters
            satellite_collections: Collections to exclude from connectivity algorithms (WCC, SCC)
            core_collections: Core business entity collections (prioritized)
        """
        self.graph_name = graph_name
        self.default_engine_size = default_engine_size
        self.auto_optimize = auto_optimize
        self.satellite_collections = satellite_collections or []
        self.core_collections = core_collections or []

        # Build collection hints for CollectionSelector
        self.collection_hints = {}
        if self.satellite_collections:
            self.collection_hints["satellite_collections"] = self.satellite_collections
        if self.core_collections:
            self.collection_hints["core_collections"] = self.core_collections

        # Initialize collection selector
        try:
            from .collection_selector import CollectionSelector

            self.collection_selector = CollectionSelector()
        except (ImportError, AttributeError):
            # CollectionSelector not available, will use fallback
            self.collection_selector = None

    def generate_templates(
        self,
        use_cases: List[UseCase],
        schema: Optional[GraphSchema] = None,
        schema_analysis: Optional[SchemaAnalysis] = None,
        schema_bundle: Optional[Any] = None,
    ) -> List[AnalysisTemplate]:
        """
        Generate analysis templates from use cases.

        Args:
            use_cases: List of use cases to convert
            schema: Optional graph schema for optimization
            schema_analysis: Optional schema analysis for insights
            schema_bundle: Optional :class:`SchemaAcquisitionBundle`
                (PRD v0.6 / FR-71). When the bundle reports an LPG /
                hybrid source, the generator emits typed-projection
                plans alongside each template so the executor can
                materialize per-type projections before launching GAE.

        Returns:
            List of analysis templates ready for execution
        """
        templates = []

        print("\n[TEMPLATE DEBUG] ******************************************")
        print(
            f"[TEMPLATE DEBUG] Starting template generation for {len(use_cases)} use cases"
        )
        print(f"[TEMPLATE DEBUG] Graph name: {self.graph_name}")
        print(f"[TEMPLATE DEBUG] Core collections: {self.core_collections}")
        print(f"[TEMPLATE DEBUG] Satellite collections: {self.satellite_collections}")
        print(
            f"[TEMPLATE DEBUG] CollectionSelector available: {self.collection_selector is not None}"
        )
        print("[TEMPLATE DEBUG] ******************************************\n")

        for use_case in use_cases:
            print(f"\n[TEMPLATE DEBUG] Processing use case: {use_case.title}")
            print(f"  ID: {use_case.id}")
            print(f"  Type: {use_case.use_case_type}")
            print(f"  Data needs: {use_case.data_needs}")

            # Prefer explicit algorithm hints from the use case (when present)
            algorithms: List[AlgorithmType] = []
            if getattr(use_case, "graph_algorithms", None):
                for algo in use_case.graph_algorithms:
                    if not algo:
                        continue
                    key = str(algo).strip().lower()
                    # Normalize common aliases to supported enum values
                    alias = {
                        "betweeness": "betweenness",
                        "betweenness_centrality": "betweenness",
                        "labelprop": "label_propagation",
                        "label-propagation": "label_propagation",
                        "page_rank": "pagerank",
                        "page-rank": "pagerank",
                    }.get(key, key)
                    try:
                        algorithms.append(AlgorithmType(alias))
                    except Exception:
                        continue

            # Fall back to use-case-type mapping if no explicit algorithm was parsed
            if not algorithms:
                algorithms = USE_CASE_TO_ALGORITHM.get(
                    use_case.use_case_type, [AlgorithmType.PAGERANK]  # Default fallback
                )

            print(
                f"[TEMPLATE DEBUG] Mapped use case type '{use_case.use_case_type}' to algorithms: {[a.value for a in algorithms]}"
            )

            # Generate template for primary algorithm
            primary_algo = algorithms[0]
            print(f"[TEMPLATE DEBUG] Selected primary algorithm: {primary_algo.value}")

            template = self._create_template(
                use_case=use_case,
                algorithm_type=primary_algo,
                schema=schema,
                schema_analysis=schema_analysis,
                schema_bundle=schema_bundle,
            )
            templates.append(template)

            print("[TEMPLATE DEBUG] Template created:")
            print(f"  Name: {template.name}")
            print(f"  Algorithm: {template.algorithm.algorithm.value}")
            print(f"  Vertex collections: {template.config.vertex_collections}")
            print(f"  Edge collections: {template.config.edge_collections}")

        print(
            f"\n[TEMPLATE DEBUG] Template generation complete: {len(templates)} templates created\n"
        )

        return templates

    def _create_template(
        self,
        use_case: UseCase,
        algorithm_type: AlgorithmType,
        schema: Optional[GraphSchema] = None,
        schema_analysis: Optional[SchemaAnalysis] = None,
        schema_bundle: Optional[Any] = None,
    ) -> AnalysisTemplate:
        """Create a single analysis template."""

        # DEBUG LOGGING - Start of template creation
        print("\n[TEMPLATE DEBUG] ==========================================")
        print(f"[TEMPLATE DEBUG] Creating template for: {use_case.title}")
        print(f"[TEMPLATE DEBUG] Use case ID: {use_case.id}")
        print(f"[TEMPLATE DEBUG] Use case type: {use_case.use_case_type}")
        print(f"[TEMPLATE DEBUG] Selected algorithm type: {algorithm_type}")
        print(f"[TEMPLATE DEBUG] Core collections hint: {self.core_collections}")
        print(
            f"[TEMPLATE DEBUG] Satellite collections hint: {self.satellite_collections}"
        )

        # Get base parameters for algorithm
        params = DEFAULT_ALGORITHM_PARAMS.get(algorithm_type, {}).copy()

        # Optimize parameters if requested
        if self.auto_optimize and schema:
            params = self._optimize_parameters(
                algorithm_type=algorithm_type,
                params=params,
                schema=schema,
                schema_analysis=schema_analysis,
            )

        # Create algorithm parameters
        algorithm = AlgorithmParameters(algorithm=algorithm_type, parameters=params)

        print(
            f"[TEMPLATE DEBUG] Created AlgorithmParameters: algorithm={algorithm.algorithm.value}"
        )

        # Determine engine size
        engine_size = self._determine_engine_size(schema)

        # Extract collections from use case data needs
        vertex_collections, edge_collections = self._extract_collections(
            use_case, schema
        )

        print("[TEMPLATE DEBUG] Extracted from use case data needs:")
        print(f"  Vertex collections ({len(vertex_collections)}): {vertex_collections}")
        print(f"  Edge collections ({len(edge_collections)}): {edge_collections}")

        # Use CollectionSelector to choose algorithm-appropriate collections
        selection_metadata = {}
        if self.collection_selector and schema and schema.vertex_collections:
            print(
                "[TEMPLATE DEBUG] CollectionSelector is available, attempting to use it..."
            )
            try:
                collection_selection = self.collection_selector.select_collections(
                    algorithm=algorithm_type,
                    schema=schema,
                    collection_hints=(
                        self.collection_hints if self.collection_hints else None
                    ),
                    use_case_context=use_case.description,
                )

                print("[TEMPLATE DEBUG] CollectionSelector returned:")
                print(
                    f"  Vertex collections ({len(collection_selection.vertex_collections)}): {collection_selection.vertex_collections}"
                )
                print(
                    f"  Edge collections ({len(collection_selection.edge_collections)}): {collection_selection.edge_collections}"
                )
                print(f"  Reasoning: {collection_selection.reasoning}")

                # Override with algorithm-specific selection
                vertex_collections = collection_selection.vertex_collections
                edge_collections = collection_selection.edge_collections

                print("[TEMPLATE DEBUG] OVERRIDE: Using CollectionSelector results")

                # Store selection reasoning in template metadata
                selection_metadata = {
                    "collection_selection_reasoning": collection_selection.reasoning,
                    "excluded_collections": {
                        "vertices": collection_selection.excluded_vertices,
                        "edges": collection_selection.excluded_edges,
                    },
                    "estimated_graph_size": collection_selection.estimated_graph_size,
                }
            except Exception as e:
                # Fall back to manual extraction if collection selector fails
                print(f"[TEMPLATE DEBUG] CollectionSelector FAILED: {e}")
                print("[TEMPLATE DEBUG] Falling back to extracted collections")
                selection_metadata = {"collection_selection_error": str(e)}
        elif (not vertex_collections or not edge_collections) and schema:
            print(
                "[TEMPLATE DEBUG] CollectionSelector not available or schema missing, using fallback..."
            )
            # Fallback if selector can't be used
            if not vertex_collections and schema.vertex_collections:
                available = [
                    name
                    for name, coll in schema.vertex_collections.items()
                    if not any(
                        pattern in name.lower()
                        for pattern in ["uc_", "result", "_temp"]
                    )
                    and coll.document_count > 1000  # Only substantial collections
                ]
                vertex_collections = available[:5]  # Limit to first 5 substantial ones
                print(
                    f"[TEMPLATE DEBUG] Fallback vertex collections: {vertex_collections}"
                )
            if not edge_collections and schema.edge_collections:
                edge_collections = list(schema.edge_collections.keys())[:5]
                print(f"[TEMPLATE DEBUG] Fallback edge collections: {edge_collections}")

        print("[TEMPLATE DEBUG] FINAL collections for template:")
        print(f"  Vertex collections ({len(vertex_collections)}): {vertex_collections}")
        print(f"  Edge collections ({len(edge_collections)}): {edge_collections}")

        # Phase 6d (FR-71): plan LPG-style typed projections when the
        # source schema is LPG / hybrid. Generic collections become
        # per-type projection collections that GAE can consume natively.
        # For PG sources (or when no bundle is provided) this returns
        # an empty list and the template behaves identically to before.
        schema_kind, lpg_projections = self._plan_lpg_projections(
            schema_bundle=schema_bundle,
            vertex_collections=vertex_collections,
            edge_collections=edge_collections,
        )

        # Create template config
        config = TemplateConfig(
            graph_name=self.graph_name,
            vertex_collections=vertex_collections,
            edge_collections=edge_collections,
            engine_size=engine_size,
            store_results=True,
            result_collection=f"{use_case.id.lower().replace('-', '_')}_results",
            schema_kind=schema_kind,
            lpg_projections=lpg_projections,
        )

        # Estimate runtime (basic heuristic)
        estimated_runtime = self._estimate_runtime(
            algorithm_type=algorithm_type, schema=schema
        )

        # Create template
        template_metadata: Dict[str, Any] = {
            "priority": use_case.priority.value,
            "use_case_type": use_case.use_case_type.value,
            "algorithms": use_case.graph_algorithms,
            "success_metrics": use_case.success_metrics,
            **selection_metadata,  # Include collection selection info
        }
        if schema_kind:
            template_metadata["schema_kind"] = schema_kind
        if lpg_projections:
            template_metadata["lpg_projection_count"] = len(lpg_projections)
            template_metadata["requires_typed_projection"] = True

        template = AnalysisTemplate(
            name=f"{use_case.id}: {use_case.title}",
            description=use_case.description,
            algorithm=algorithm,
            config=config,
            use_case_id=use_case.id,
            estimated_runtime_seconds=estimated_runtime,
            metadata=template_metadata,
        )

        return template

    def _plan_lpg_projections(
        self,
        schema_bundle: Optional[Any],
        vertex_collections: List[str],
        edge_collections: List[str],
    ) -> tuple:
        """Build a typed-projection plan for LPG / hybrid sources.

        PRD v0.6 / FR-71. GAE consumes whole collections; when the
        source schema mixes many logical types in a single generic
        collection (LPG ``LABEL`` for nodes, ``GENERIC_WITH_TYPE`` for
        edges) the executor must materialize a per-type projection
        before launching the algorithm. This method generates the
        idempotent UPSERT-shaped AQL the executor can run verbatim.

        Returns ``(schema_kind, projections)``:

        - ``schema_kind`` — ``None`` when no bundle is provided,
          otherwise the bundle's reported kind (``"pg"`` / ``"lpg"`` /
          ``"hybrid"`` / ``"rpt"`` / ``"unknown"``).
        - ``projections`` — list of :class:`LpgProjection`. Empty for
          PG sources or when nothing in the requested vertex / edge
          collections matches an LPG style.
        """
        if schema_bundle is None:
            return None, []

        schema_kind = getattr(schema_bundle, "schema_kind", None)
        physical_mapping = getattr(schema_bundle, "physical_mapping", None) or {}

        # PG sources never need projections — collections already are
        # the typed unit GAE expects. RPT / unknown deliberately fall
        # through; their materialization story is upstream-owned.
        if schema_kind not in {"lpg", "hybrid"}:
            return schema_kind, []

        entities = physical_mapping.get("entities") or {}
        relationships = physical_mapping.get("relationships") or {}
        if not isinstance(entities, dict) or not isinstance(relationships, dict):
            return schema_kind, []

        wanted_vertex_collections = {c for c in vertex_collections}
        wanted_edge_collections = {c for c in edge_collections}

        projections: List[LpgProjection] = []

        for logical_type, spec in entities.items():
            if not isinstance(spec, dict):
                continue
            if spec.get("style") != "LABEL":
                continue
            source = spec.get("collectionName")
            field_name = spec.get("typeField")
            value = spec.get("typeValue")
            if not source or not field_name or value is None:
                continue
            # Only project for collections actually requested by the
            # template — don't materialize collections nobody asked for.
            if wanted_vertex_collections and source not in wanted_vertex_collections:
                continue
            target = self._projection_collection_name(source, field_name, str(value))
            projections.append(
                LpgProjection(
                    logical_type=str(logical_type),
                    source_collection=source,
                    discriminator_field=field_name,
                    discriminator_value=str(value),
                    kind="node",
                    materialization_collection=target,
                    materialization_aql=self._projection_aql(
                        source=source,
                        target=target,
                        field=field_name,
                        value=str(value),
                        is_edge=False,
                    ),
                )
            )

        for logical_type, spec in relationships.items():
            if not isinstance(spec, dict):
                continue
            if spec.get("style") != "GENERIC_WITH_TYPE":
                continue
            source = spec.get("edgeCollectionName")
            field_name = spec.get("typeField")
            value = spec.get("typeValue")
            if not source or not field_name or value is None:
                continue
            if wanted_edge_collections and source not in wanted_edge_collections:
                continue
            target = self._projection_collection_name(source, field_name, str(value))
            projections.append(
                LpgProjection(
                    logical_type=str(logical_type),
                    source_collection=source,
                    discriminator_field=field_name,
                    discriminator_value=str(value),
                    kind="edge",
                    materialization_collection=target,
                    materialization_aql=self._projection_aql(
                        source=source,
                        target=target,
                        field=field_name,
                        value=str(value),
                        is_edge=True,
                    ),
                )
            )

        return schema_kind, projections

    @staticmethod
    def _projection_collection_name(source: str, field: str, value: str) -> str:
        """Deterministic projection collection name.

        Pattern: ``_proj_<source>_<field>_<value>`` truncated +
        sanitized to satisfy ArangoDB collection-name rules
        (alphanumeric + underscore, <=64 chars).
        """
        import re as _re

        raw = f"_proj_{source}_{field}_{value}"
        sanitized = _re.sub(r"[^A-Za-z0-9_]", "_", raw)
        return sanitized[:64]

    @staticmethod
    def _projection_aql(
        source: str, target: str, field: str, value: str, is_edge: bool
    ) -> str:
        """Idempotent AQL to materialize a typed projection.

        Uses ``UPSERT`` keyed on ``_key`` so re-runs are no-ops when
        nothing has changed. Edge projections preserve ``_from`` /
        ``_to`` so GAE can traverse them as native edges.
        """
        if is_edge:
            return (
                f"FOR doc IN `{source}` "
                f"FILTER doc.`{field}` == @value "
                f"UPSERT {{ _key: doc._key }} "
                f"INSERT {{ _key: doc._key, _from: doc._from, _to: doc._to, "
                f'_source: "{source}", _logical_type: @value }} '
                f"UPDATE {{ _from: doc._from, _to: doc._to, "
                f"_logical_type: @value }} "
                f"IN `{target}`"
            )
        return (
            f"FOR doc IN `{source}` "
            f"FILTER doc.`{field}` == @value "
            f"UPSERT {{ _key: doc._key }} "
            f"INSERT MERGE(doc, {{ _logical_type: @value }}) "
            f"UPDATE MERGE(doc, {{ _logical_type: @value }}) "
            f"IN `{target}`"
        )

    def _optimize_parameters(
        self,
        algorithm_type: AlgorithmType,
        params: Dict[str, Any],
        schema: GraphSchema,
        schema_analysis: Optional[SchemaAnalysis] = None,
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
                optimized["maximum_supersteps"] = 50  # Fewer for large graphs
            elif total_docs < 1000:
                optimized["maximum_supersteps"] = 150  # More for small graphs

            # Adjust threshold based on density
            if avg_degree > 10:
                optimized["threshold"] = 0.0005  # Tighter for dense graphs

        elif algorithm_type == AlgorithmType.LABEL_PROPAGATION:
            # Adjust iterations based on graph size
            if total_docs > 10000:
                optimized["max_iterations"] = 30  # Fewer for large graphs
            elif total_docs < 1000:
                optimized["max_iterations"] = 100  # More for small graphs

        elif algorithm_type == AlgorithmType.WCC:
            # WCC doesn't have many tunable parameters
            # Result store name is set elsewhere
            pass

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
            vertex_count=schema.total_documents, edge_count=schema.total_edges
        )

    def _extract_collections(
        self, use_case: UseCase, schema: Optional[GraphSchema] = None
    ) -> tuple:
        """
        Extract vertex and edge collections from use case and schema.

        IMPORTANT: For proper graph analysis, we need to avoid:
        - Satellite collections that artificially connect everything
        - Result collections from previous analyses
        - Hub collections that aren't relevant to the use case

        Args:
            use_case: Use case with data requirements
            schema: Optional schema for available collections

        Returns:
            tuple: (vertex_collections, edge_collections)
        """
        vertex_collections = []
        edge_collections = []

        # If schema provided, get available collections
        available_vertices = set()
        available_edges = set()

        if schema:
            if hasattr(schema, "vertex_collections") and schema.vertex_collections:
                available_vertices = set(schema.vertex_collections.keys())
            if hasattr(schema, "edge_collections") and schema.edge_collections:
                available_edges = set(schema.edge_collections.keys())

        # Filter out result collections and common satellite collections
        exclude_patterns = ["uc_", "result", "_temp", "_backup"]

        # Parse data needs from use case
        for need in use_case.data_needs:
            need_lower = need.lower()

            # Device and IP focused (household resolution)
            if "device" in need_lower and "Device" in available_vertices:
                vertex_collections.append("Device")
            if "ip" in need_lower and "IP" in available_vertices:
                vertex_collections.append("IP")

            # Content focused (inventory, apps, sites)
            if (
                "app" in need_lower or "product" in need_lower
            ) and "AppProduct" in available_vertices:
                vertex_collections.append("AppProduct")
            if (
                "site" in need_lower or "web" in need_lower
            ) and "Site" in available_vertices:
                vertex_collections.append("Site")
            if "installedapp" in need_lower and "InstalledApp" in available_vertices:
                vertex_collections.append("InstalledApp")
            if "siteuse" in need_lower and "SiteUse" in available_vertices:
                vertex_collections.append("SiteUse")

            # Publisher/content providers (but be careful - these can be hubs)
            if "publisher" in need_lower and "Publisher" in available_vertices:
                vertex_collections.append("Publisher")

            # Edges
            if "seen_on_ip" in need_lower or (
                "device" in need_lower and "ip" in need_lower
            ):
                if "SEEN_ON_IP" in available_edges:
                    edge_collections.append("SEEN_ON_IP")
            if "seen_on_app" in need_lower or "app" in need_lower:
                if "SEEN_ON_APP" in available_edges:
                    edge_collections.append("SEEN_ON_APP")
            if "seen_on_site" in need_lower or "site" in need_lower:
                if "SEEN_ON_SITE" in available_edges:
                    edge_collections.append("SEEN_ON_SITE")
            if "instance_of" in need_lower:
                if "INSTANCE_OF" in available_edges:
                    edge_collections.append("INSTANCE_OF")

        # If nothing extracted from data_needs, infer from use case type and title
        if not vertex_collections and not edge_collections:
            title_lower = use_case.title.lower()
            desc_lower = use_case.description.lower()
            combined = f"{title_lower} {desc_lower}"

            # Household/identity resolution use cases
            if any(
                term in combined
                for term in ["household", "identity", "resolution", "device", "ip"]
            ):
                if "Device" in available_vertices:
                    vertex_collections.append("Device")
                if "IP" in available_vertices:
                    vertex_collections.append("IP")
                if "SEEN_ON_IP" in available_edges:
                    edge_collections.append("SEEN_ON_IP")

            # Fraud/anomaly detection
            elif any(term in combined for term in ["fraud", "anomaly", "bot"]):
                if "Device" in available_vertices:
                    vertex_collections.append("Device")
                if "IP" in available_vertices:
                    vertex_collections.append("IP")
                if "SEEN_ON_IP" in available_edges:
                    edge_collections.append("SEEN_ON_IP")

            # Content/inventory analysis
            elif any(
                term in combined
                for term in ["content", "inventory", "app", "site", "publisher"]
            ):
                if "AppProduct" in available_vertices:
                    vertex_collections.append("AppProduct")
                if "Site" in available_vertices:
                    vertex_collections.append("Site")
                if "Device" in available_vertices:
                    vertex_collections.append("Device")
                if "SEEN_ON_APP" in available_edges:
                    edge_collections.append("SEEN_ON_APP")
                if "SEEN_ON_SITE" in available_edges:
                    edge_collections.append("SEEN_ON_SITE")

        # Remove duplicates while preserving order
        vertex_collections = list(dict.fromkeys(vertex_collections))
        edge_collections = list(dict.fromkeys(edge_collections))

        # Filter out excluded patterns
        vertex_collections = [
            v
            for v in vertex_collections
            if not any(pattern in v.lower() for pattern in exclude_patterns)
        ]

        return vertex_collections, edge_collections

    def _estimate_runtime(
        self, algorithm_type: AlgorithmType, schema: Optional[GraphSchema]
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

        elif algorithm_type == AlgorithmType.LABEL_PROPAGATION:
            # O(iterations * m)
            return max(1.5, (n + m) / 8000)

        elif algorithm_type == AlgorithmType.WCC:
            # O(m) - usually fast
            return max(0.5, (n + m) / 15000)

        elif algorithm_type == AlgorithmType.SCC:
            # O(m) - similar to WCC
            return max(0.5, (n + m) / 15000)

        elif algorithm_type == AlgorithmType.BETWEENNESS_CENTRALITY:
            # O(n * m) - can be slow
            return max(5.0, (n * m) / 100000)

        else:
            # Default estimate
            return max(1.0, (n + m) / 15000)


def generate_template(
    use_case: UseCase,
    graph_name: str = "ecommerce_graph",
    schema: Optional[GraphSchema] = None,
    algorithm_type: Optional[AlgorithmType] = None,
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
            use_case.use_case_type, [AlgorithmType.PAGERANK]
        )
        algorithm_type = algorithms[0]

    return generator._create_template(
        use_case=use_case, algorithm_type=algorithm_type, schema=schema
    )
