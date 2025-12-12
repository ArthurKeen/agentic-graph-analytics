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


# LLM prompt for schema analysis
SCHEMA_ANALYSIS_PROMPT = """You are a graph database expert analyzing the structure of an ArangoDB graph.

Given the following graph schema, provide a comprehensive analysis.

# Graph Schema

{schema_json}

# Analysis Tasks

1. **Description**: Provide a clear, human-readable description of what this graph represents (2-3 sentences).

2. **Domain**: Identify the domain or use case (e.g., "social network", "supply chain", "knowledge graph", "fraud detection", "recommendation system", etc.).

3. **Key Entities**: List the 3 most important vertex collections based on their centrality in the graph.

4. **Key Relationships**: List the 3 most important edge collections based on their potential analytical value.

5. **Suggested Analyses**: Suggest 5 specific graph analytics that would be valuable for this graph:
   - Centrality analysis (PageRank, Betweenness, etc.)
   - Community detection
   - Pathfinding
   - Pattern detection
   - Risk/anomaly detection
   For each, explain why it's relevant to this specific graph.

6. **Complexity Score**: Rate the graph complexity on a scale of 0-10, where:
   - 0-3: Simple (few collections, clear structure)
   - 4-7: Moderate (multiple collections, some complexity)
   - 8-10: Complex (many collections, intricate relationships)

# Response Format

Respond with valid JSON matching this structure:

{{
  "description": "2-3 sentence description of the graph",
  "domain": "identified domain",
  "key_entities": ["collection1", "collection2", "collection3"],
  "key_relationships": ["edge1", "edge2", "edge3"],
  "suggested_analyses": [
    {{
      "type": "analysis type (e.g., pagerank, community_detection)",
      "title": "Human-readable title",
      "reason": "Why this analysis is valuable for this graph"
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
        self,
        schema: GraphSchema,
        include_samples: bool = True
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
            for col_info in schema_dict.get('vertex_collections', {}).values():
                col_info['sample_document'] = None
        
        # Format prompt
        prompt = SCHEMA_ANALYSIS_PROMPT.format(
            schema_json=json.dumps(schema_dict, indent=2)
        )
        
        # Generate analysis
        try:
            result = self.llm_provider.generate_structured(
                prompt,
                schema=self._get_response_schema()
            )
            
            # Create analysis object
            analysis = SchemaAnalysis(
                schema=schema,
                description=result.get('description', ''),
                domain=result.get('domain'),
                key_entities=result.get('key_entities', []),
                key_relationships=result.get('key_relationships', []),
                suggested_analyses=result.get('suggested_analyses', []),
                complexity_score=float(result.get('complexity_score', 0))
            )
            
            return analysis
        
        except Exception as e:
            # If LLM fails, return basic analysis
            return self._create_fallback_analysis(schema, error=str(e))
    
    def _get_response_schema(self) -> Dict[str, Any]:
        """Get JSON schema for LLM response."""
        return {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "domain": {"type": "string"},
                "key_entities": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "key_relationships": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "suggested_analyses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "title": {"type": "string"},
                            "reason": {"type": "string"}
                        }
                    }
                },
                "complexity_score": {"type": "number"}
            },
            "required": ["description", "domain", "key_entities", "complexity_score"]
        }
    
    def _create_fallback_analysis(
        self,
        schema: GraphSchema,
        error: Optional[str] = None
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
            len(schema.vertex_collections) +
            len(schema.edge_collections) +
            len(schema.document_collections)
        )
        relationships_count = len(schema.relationships)
        
        complexity = min(10.0, (total_collections / 3) + (relationships_count / 5))
        
        # Get top collections by document count
        all_vertex_cols = sorted(
            schema.vertex_collections.items(),
            key=lambda x: x[1].document_count,
            reverse=True
        )
        key_entities = [name for name, _ in all_vertex_cols[:3]]
        
        all_edge_cols = sorted(
            schema.edge_collections.items(),
            key=lambda x: x[1].document_count,
            reverse=True
        )
        key_relationships = [name for name, _ in all_edge_cols[:3]]
        
        # Create basic description
        description = (
            f"Graph database with {len(schema.vertex_collections)} vertex collections, "
            f"{len(schema.edge_collections)} edge collections, "
            f"and {schema.total_documents:,} total documents."
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
            suggested_analyses=[]
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
        report.append(f"- **Total Collections:** {len(schema.vertex_collections) + len(schema.edge_collections) + len(schema.document_collections)}")
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
                report.append(f"{i}. **{suggestion.get('title', 'Unknown')}** (`{suggestion.get('type', 'unknown')}`)")
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
