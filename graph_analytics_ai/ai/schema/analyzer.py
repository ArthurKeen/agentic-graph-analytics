"""
Schema analyzer that uses LLM to generate insights about graph structure.

This module takes extracted schema information and uses an LLM to:
- Generate human-readable descriptions
- Identify the domain/use case
- Suggest relevant graph analytics
- Assess complexity
"""

import json
from typing import Optional, Dict, Any

from ..llm import LLMProvider, get_default_provider
from .models import GraphSchema, SchemaAnalysis


# LLM prompt for schema analysis with few-shot examples
SCHEMA_ANALYSIS_PROMPT = """You are a graph database expert analyzing the structure of an ArangoDB graph.

# Example Analysis 1: E-commerce Graph

Input Schema:
{{
  "vertex_collections": {{
    "Customer": {{"document_count": 50000, "sample_document": {{"_key": "C123", "name": "John Doe", "email": "john@example.com", "registration_date": "2023-01-15"}}}},
    "Product": {{"document_count": 5000, "sample_document": {{"_key": "P456", "name": "Laptop", "price": 999.99, "category": "Electronics"}}}},
    "Order": {{"document_count": 200000, "sample_document": {{"_key": "O789", "total": 1299.99, "date": "2024-03-20"}}}}
  }},
  "edge_collections": {{
    "purchased": {{"document_count": 300000, "from": ["Customer"], "to": ["Product"], "sample_document": {{"_from": "Customer/C123", "_to": "Product/P456", "quantity": 2}}}},
    "reviewed": {{"document_count": 45000, "from": ["Customer"], "to": ["Product"]}}
  }}
}}

Expected Output:
{{
  "description": "E-commerce graph tracking customer purchase behavior across products and orders. The graph contains 50K customers who have made 200K orders, purchasing from 5K products. The purchase and review edges create a bipartite network enabling product recommendation and customer segmentation analytics.",
  "domain": "e-commerce",
  "key_entities": ["Customer", "Product", "Order"],
  "key_relationships": ["purchased", "reviewed"],
  "suggested_analyses": [
    {{
      "type": "pagerank",
      "title": "Product Popularity and Influence Ranking",
      "reason": "Identify influential products based on purchase patterns and review networks. High-rank products are popular and could be prioritized in recommendations."
    }},
    {{
      "type": "wcc",
      "title": "Customer Purchase Communities",
      "reason": "Detect disconnected customer segments to identify different market niches or isolated user groups requiring targeted marketing."
    }},
    {{
      "type": "label_propagation",
      "title": "Product Category Clustering",
      "reason": "Discover natural product groupings based on co-purchase patterns beyond predefined categories, enabling better cross-sell strategies."
    }},
    {{
      "type": "betweenness",
      "title": "Gateway Product Identification",
      "reason": "Find products that bridge different customer segments or product categories, useful for inventory optimization and promotional planning."
    }},
    {{
      "type": "scc",
      "title": "Customer Loyalty Loop Detection",
      "reason": "Identify groups of customers with cyclical purchase patterns indicating strong brand loyalty and potential for subscription models."
    }}
  ],
  "complexity_score": 4.5
}}

# Example Analysis 2: Social Network Graph

Input Schema:
{{
  "vertex_collections": {{
    "User": {{"document_count": 1000000, "sample_document": {{"_key": "U001", "username": "alice", "join_date": "2022-05-10"}}}},
    "Post": {{"document_count": 5000000, "sample_document": {{"_key": "POST001", "content": "Hello world", "timestamp": "2024-01-15T10:30:00"}}}},
    "Group": {{"document_count": 50000, "sample_document": {{"_key": "G001", "name": "Photography Enthusiasts", "members": 1500}}}}
  }},
  "edge_collections": {{
    "follows": {{"document_count": 10000000, "from": ["User"], "to": ["User"]}},
    "posted": {{"document_count": 5000000, "from": ["User"], "to": ["Post"]}},
    "member_of": {{"document_count": 2000000, "from": ["User"], "to": ["Group"]}}
  }}
}}

Expected Output:
{{
  "description": "Large-scale social network with 1M users creating 5M posts and participating in 50K groups. The follower network has 10M connections, creating a complex web of social relationships. This structure enables influence analysis, community detection, and content propagation studies.",
  "domain": "social network",
  "key_entities": ["User", "Post", "Group"],
  "key_relationships": ["follows", "posted", "member_of"],
  "suggested_analyses": [
    {{
      "type": "pagerank",
      "title": "Influencer Identification",
      "reason": "Rank users by their influence in the network, accounting for both follower count and the importance of their followers. Critical for identifying key opinion leaders."
    }},
    {{
      "type": "label_propagation",
      "title": "Organic Community Detection",
      "reason": "Discover natural communities beyond formal groups, revealing hidden social clusters and improving content recommendation algorithms."
    }},
    {{
      "type": "betweenness",
      "title": "Network Bridge User Identification",
      "reason": "Find users who connect disparate communities, important for information dissemination and network resilience analysis."
    }},
    {{
      "type": "wcc",
      "title": "Network Connectivity Analysis",
      "reason": "Identify disconnected user clusters or isolated users, helping improve engagement strategies and platform connectivity."
    }},
    {{
      "type": "scc",
      "title": "Reciprocal Relationship Groups",
      "reason": "Detect tightly-knit user groups with mutual connections, indicating strong relationships useful for targeted feature testing."
    }}
  ],
  "complexity_score": 7.5
}}

# Your Task

Given the following graph schema, provide a comprehensive analysis following the same format and reasoning depth as the examples above.

# Graph Schema

{schema_json}

# Analysis Guidelines

- **Key Entities**: Prioritize collections by document count, connectivity (degree centrality), and business relevance
- **Key Relationships**: Focus on edges with high counts, connecting important entities, or enabling valuable analysis patterns
- **Complexity Scoring**:
  - Count collections (vertices + edges)
  - Assess interconnectedness (many-to-many vs simple links)
  - Consider domain complexity (finance/healthcare = higher, simple catalogs = lower)
  - 0-3: ≤5 collections, simple relationships
  - 4-7: 6-15 collections, moderate interconnections
  - 8-10: >15 collections, complex multi-hop patterns

# Response Format

Respond with valid JSON matching this structure:

{{
  "description": "2-3 sentence description of the graph",
  "domain": "identified domain",
  "key_entities": ["collection1", "collection2", "collection3"],
  "key_relationships": ["edge1", "edge2", "edge3"],
  "suggested_analyses": [
    {{
      "type": "analysis type (e.g., pagerank, wcc, label_propagation, betweenness, scc)",
      "title": "Human-readable title",
      "reason": "Why this analysis is valuable for this specific graph"
    }},
    ...
  ],
  "complexity_score": 5.5
}}

Respond ONLY with the JSON, no additional text.
"""


class SchemaAnalyzer:
    """
    Analyze graph schema using LLM to generate insights.

    Example:
        >>> from graph_analytics_ai.ai.schema import SchemaExtractor, SchemaAnalyzer
        >>> from graph_analytics_ai.ai.llm import create_llm_provider
        >>>
        >>> # Extract schema
        >>> extractor = create_extractor(...)
        >>> schema = extractor.extract()
        >>>
        >>> # Analyze with LLM
        >>> provider = create_llm_provider()
        >>> analyzer = SchemaAnalyzer(provider)
        >>> analysis = analyzer.analyze(schema)
        >>>
        >>> print(analysis.description)
        >>> print(f"Domain: {analysis.domain}")
        >>> print(f"Complexity: {analysis.complexity_score}/10")
        >>>
        >>> for suggestion in analysis.suggested_analyses:
        ...     print(f"- {suggestion['title']}: {suggestion['reason']}")
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize schema analyzer.

        Args:
            llm_provider: LLM provider to use. If None, uses default from environment.
        """
        self.llm_provider = llm_provider or get_default_provider()

    def analyze(
        self, schema: GraphSchema, include_samples: bool = True
    ) -> SchemaAnalysis:
        """
        Analyze schema and generate insights.

        Args:
            schema: Graph schema to analyze.
            include_samples: Whether to include sample documents in LLM prompt.

        Returns:
            SchemaAnalysis with LLM-generated insights.

        Raises:
            LLMProviderError: If LLM generation fails.
        """
        # Convert schema to summary format for LLM
        schema_dict = schema.to_summary_dict()

        # Optionally remove sample documents to reduce token usage
        if not include_samples:
            for col_info in schema_dict.get("vertex_collections", {}).values():
                col_info["sample_document"] = None

        # Format prompt
        prompt = SCHEMA_ANALYSIS_PROMPT.format(
            schema_json=json.dumps(schema_dict, indent=2)
        )

        # Generate analysis
        try:
            result = self.llm_provider.generate_structured(
                prompt, schema=self._get_response_schema()
            )

            # Create analysis object
            analysis = SchemaAnalysis(
                schema=schema,
                description=result.get("description", ""),
                domain=result.get("domain"),
                key_entities=result.get("key_entities", []),
                key_relationships=result.get("key_relationships", []),
                suggested_analyses=result.get("suggested_analyses", []),
                complexity_score=float(result.get("complexity_score", 0)),
            )

            # Validate and add confidence/warnings
            analysis = self._validate_analysis(analysis, schema)

            return analysis

        except Exception as e:
            # If LLM fails, return basic analysis
            return self._create_fallback_analysis(schema, error=str(e))

    def _validate_analysis(
        self, analysis: SchemaAnalysis, schema: GraphSchema
    ) -> SchemaAnalysis:
        """
        Validate analysis quality and add confidence score with warnings.

        Args:
            analysis: Initial analysis from LLM
            schema: Original schema

        Returns:
            Analysis with confidence and warnings added
        """
        warnings = []
        confidence = 1.0

        # Validate key entities
        if len(analysis.key_entities) < 3:
            warnings.append(
                f"Only {len(analysis.key_entities)} key entities identified (expected 3)"
            )
            confidence *= 0.8

        # Check if key entities actually exist in schema
        actual_collections = set(schema.vertex_collections.keys())
        invalid_entities = [
            e for e in analysis.key_entities if e not in actual_collections
        ]
        if invalid_entities:
            warnings.append(
                f"Invalid key entities (not in schema): {', '.join(invalid_entities)}"
            )
            confidence *= 0.6

        # Validate key relationships
        if len(analysis.key_relationships) < 3:
            warnings.append(
                f"Only {len(analysis.key_relationships)} key relationships identified (expected 3)"
            )
            confidence *= 0.8

        actual_edges = set(schema.edge_collections.keys())
        invalid_relationships = [
            r for r in analysis.key_relationships if r not in actual_edges
        ]
        if invalid_relationships:
            warnings.append(
                f"Invalid relationships (not in schema): {', '.join(invalid_relationships)}"
            )
            confidence *= 0.6

        # Validate complexity score
        if analysis.complexity_score < 0 or analysis.complexity_score > 10:
            warnings.append(
                f"Invalid complexity score: {analysis.complexity_score} (must be 0-10)"
            )
            # Clamp to valid range
            analysis.complexity_score = max(0, min(10, analysis.complexity_score))
            confidence *= 0.5

        # Validate suggested analyses
        if len(analysis.suggested_analyses) < 5:
            warnings.append(
                f"Only {len(analysis.suggested_analyses)} analyses suggested (expected 5)"
            )
            confidence *= 0.9

        # Check domain is not empty/generic
        if not analysis.domain or analysis.domain.lower() in [
            "unknown",
            "general",
            "graph",
        ]:
            warnings.append("Domain identification unclear or too generic")
            confidence *= 0.7

        # Check description quality
        if not analysis.description or len(analysis.description) < 50:
            warnings.append("Description too brief or missing")
            confidence *= 0.7

        # Add validation metadata (if SchemaAnalysis supports it)
        # For now, log warnings
        if warnings:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                f"Schema analysis validation issues (confidence: {confidence:.2f}): {'; '.join(warnings)}"
            )

        return analysis

    def _get_response_schema(self) -> Dict[str, Any]:
        """Get JSON schema for LLM response."""
        return {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "domain": {"type": "string"},
                "key_entities": {"type": "array", "items": {"type": "string"}},
                "key_relationships": {"type": "array", "items": {"type": "string"}},
                "suggested_analyses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "title": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                    },
                },
                "complexity_score": {"type": "number"},
            },
            "required": ["description", "domain", "key_entities", "complexity_score"],
        }

    def _create_fallback_analysis(
        self, schema: GraphSchema, error: Optional[str] = None
    ) -> SchemaAnalysis:
        """
        Create basic analysis without LLM if LLM fails.

        Args:
            schema: Graph schema.
            error: Optional error message.

        Returns:
            Basic SchemaAnalysis.
        """
        # Calculate simple complexity score
        total_collections = (
            len(schema.vertex_collections)
            + len(schema.edge_collections)
            + len(schema.document_collections)
        )
        relationships_count = len(schema.relationships)

        complexity = min(10.0, (total_collections / 3) + (relationships_count / 5))

        # Get top collections by document count
        all_vertex_cols = sorted(
            schema.vertex_collections.items(),
            key=lambda x: x[1].document_count,
            reverse=True,
        )
        key_entities = [name for name, _ in all_vertex_cols[:3]]

        all_edge_cols = sorted(
            schema.edge_collections.items(),
            key=lambda x: x[1].document_count,
            reverse=True,
        )
        key_relationships = [name for name, _ in all_edge_cols[:3]]

        # Create basic description
        # Build a richer description that surfaces collection sizes (helps tests and users)
        top_entities_desc = ""
        if key_entities:
            parts = []
            for name in key_entities:
                col = schema.vertex_collections.get(name)
                if col:
                    parts.append(f"{name} ({col.document_count:,} docs)")
            if parts:
                top_entities_desc = f" Top entities: {', '.join(parts)}."

        description = (
            f"Graph database with {len(schema.vertex_collections)} vertex collections, "
            f"{len(schema.edge_collections)} edge collections, "
            f"and {schema.total_documents:,} total documents."
            f"{top_entities_desc}"
        )

        if error:
            description += f" (Note: LLM analysis failed: {error[:100]})"

        return SchemaAnalysis(
            schema=schema,
            description=description,
            domain="Unknown (LLM analysis unavailable)",
            key_entities=key_entities,
            key_relationships=key_relationships,
            complexity_score=complexity,
            suggested_analyses=[],
        )

    def generate_report(self, analysis: SchemaAnalysis) -> str:
        """
        Generate a human-readable report from schema analysis.

        Args:
            analysis: Schema analysis to report on.

        Returns:
            Formatted report string.
        """
        schema = analysis.schema

        report = []
        report.append("=" * 80)
        report.append("GRAPH SCHEMA ANALYSIS REPORT")
        report.append("=" * 80)
        report.append("")

        # Overview
        report.append("## Overview")
        report.append("")
        report.append(f"**Database:** {schema.database_name}")
        report.append(f"**Domain:** {analysis.domain or 'Unknown'}")
        report.append(f"**Complexity:** {analysis.complexity_score:.1f}/10")
        if analysis.is_simple_graph:
            report.append("  _(Simple graph structure)_")
        elif analysis.is_complex_graph:
            report.append("  _(Complex graph structure)_")
        report.append("")
        report.append(f"**Description:** {analysis.description}")
        report.append("")

        # Statistics
        report.append("## Statistics")
        report.append("")
        report.append(
            f"- **Total Collections:** {len(schema.vertex_collections) + len(schema.edge_collections) + len(schema.document_collections)}"
        )
        report.append(f"- **Vertex Collections:** {len(schema.vertex_collections)}")
        report.append(f"- **Edge Collections:** {len(schema.edge_collections)}")
        report.append(f"- **Total Documents:** {schema.total_documents:,}")
        report.append(f"- **Total Edges:** {schema.total_edges:,}")
        report.append(f"- **Relationships:** {len(schema.relationships)}")
        report.append("")

        # Key Entities
        if analysis.key_entities:
            report.append("## Key Entity Collections")
            report.append("")
            for entity in analysis.key_entities:
                col = schema.vertex_collections.get(entity)
                if col:
                    report.append(f"- **{entity}**: {col.document_count:,} documents")
                    key_attrs = col.get_key_attributes(3)
                    if key_attrs:
                        report.append(f"  - Key attributes: {', '.join(key_attrs)}")
            report.append("")

        # Key Relationships
        if analysis.key_relationships:
            report.append("## Key Relationships")
            report.append("")
            for edge_name in analysis.key_relationships:
                col = schema.edge_collections.get(edge_name)
                if col:
                    report.append(f"- **{edge_name}**: {col.document_count:,} edges")
                    if col.from_collections and col.to_collections:
                        for from_col in col.from_collections:
                            for to_col in col.to_collections:
                                report.append(f"  - {from_col} → {to_col}")
            report.append("")

        # Suggested Analyses
        if analysis.suggested_analyses:
            report.append("## Recommended Graph Analytics")
            report.append("")
            for i, suggestion in enumerate(analysis.suggested_analyses, 1):
                report.append(
                    f"{i}. **{suggestion.get('title', 'Unknown')}** (`{suggestion.get('type', 'unknown')}`)"
                )
                report.append(f"   - {suggestion.get('reason', 'No reason provided')}")
                report.append("")

        # All Relationships
        if schema.relationships:
            report.append("## All Relationships")
            report.append("")
            for rel in schema.relationships:
                report.append(f"- {str(rel)} ({rel.edge_count:,} edges)")
            report.append("")

        report.append("=" * 80)

        return "\n".join(report)
