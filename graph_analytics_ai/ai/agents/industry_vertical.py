"""
IndustryVerticalAgent - Generates custom industry verticals from business requirements.

This agent analyzes business requirements documents and graph schemas to automatically
generate domain-specific prompts and pattern definitions for graph analytics.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from graph_analytics_ai.ai.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class IndustryVerticalAgent:
    """
    Agent that generates custom industry verticals from business requirements.

    This agent:
    1. Analyzes business requirements to understand the domain
    2. Identifies key entities (nodes/edges) from the graph schema
    3. Extracts domain-specific terminology and metrics
    4. Generates an LLM prompt tailored to the industry
    5. Defines pattern templates for common algorithms
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize the IndustryVerticalAgent.

        Args:
            llm_provider: LLM provider for generating prompts (optional, will create if needed)
        """
        self.llm_provider = llm_provider
        if self.llm_provider is None:
            from graph_analytics_ai.ai.llm.factory import create_llm_provider

            self.llm_provider = create_llm_provider()

    async def generate_vertical(
        self,
        business_requirements: str,
        graph_name: str,
        graph_connection: Optional[Any] = None,
        domain_description: Optional[str] = None,
        base_vertical: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a complete custom industry vertical.

        Args:
            business_requirements: Content of business requirements document
            graph_name: Name of the graph to analyze
            graph_connection: Connection to graph database (optional)
            domain_description: Additional domain description (optional)
            base_vertical: Name of existing vertical to base on (optional)

        Returns:
            Dictionary containing the complete vertical configuration
        """
        logger.info("Starting custom vertical generation...")

        # Step 1: Analyze the domain
        logger.info("Step 1/4: Analyzing domain context...")
        domain_analysis = await self.analyze_domain(
            business_requirements, domain_description, graph_name, graph_connection
        )

        # Step 2: Generate the analysis prompt
        logger.info("Step 2/4: Generating industry-specific prompt...")
        analysis_prompt = await self.generate_prompt(domain_analysis, base_vertical)

        # Step 3: Generate pattern definitions
        logger.info("Step 3/4: Generating pattern definitions...")
        pattern_definitions = await self.generate_pattern_definitions(domain_analysis)

        # Step 4: Assemble the vertical
        logger.info("Step 4/4: Assembling vertical configuration...")
        vertical = {
            "metadata": {
                "name": domain_analysis["industry_key"],
                "display_name": domain_analysis["industry_display_name"],
                "version": "1.0",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "generated_by": "IndustryVerticalAgent",
                "source_documents": domain_analysis.get("source_documents", []),
            },
            "domain_context": {
                "industry": domain_analysis["industry_display_name"],
                "business_focus": domain_analysis["business_focus"],
                "key_entities": domain_analysis["key_entities"],
                "key_metrics": domain_analysis.get("key_metrics", []),
                "terminology": domain_analysis.get("terminology", {}),
            },
            "analysis_prompt": analysis_prompt,
            "pattern_definitions": pattern_definitions,
            "user_validated": False,
            "user_notes": "",
        }

        logger.info(
            f"✓ Generated custom vertical: {vertical['metadata']['display_name']}"
        )
        return vertical

    async def analyze_domain(
        self,
        business_requirements: str,
        domain_description: Optional[str],
        graph_name: str,
        graph_connection: Optional[Any],
    ) -> Dict[str, Any]:
        """
        Analyze business requirements to extract domain characteristics.

        Returns:
            Dictionary with domain analysis results
        """
        # Combine all available context
        context = f"# Business Requirements\n\n{business_requirements}\n\n"
        if domain_description:
            context += f"# Domain Description\n\n{domain_description}\n\n"

        # Get graph schema if available
        schema_info = ""
        if graph_connection:
            try:
                # Try to get collections/schema
                schema_info = await self._extract_graph_schema(
                    graph_connection, graph_name
                )
            except Exception as e:
                logger.warning(f"Could not extract graph schema: {e}")

        if schema_info:
            context += f"# Graph Schema\n\n{schema_info}\n\n"

        # Use LLM to analyze the domain
        analysis_prompt = f"""Analyze the following business requirements and extract key domain characteristics for graph analytics.

{context}

Extract and return a JSON object with the following structure:
{{
  "industry_key": "machine_readable_name",
  "industry_display_name": "Human Readable Name",
  "business_focus": "Primary business objective or focus area",
  "key_entities": {{
    "nodes": ["NodeType: Description", ...],
    "edges": ["edgeType: Description", ...]
  }},
  "key_metrics": ["Metric 1", "Metric 2", ...],
  "terminology": {{
    "currency": "Primary currency (USD, EUR, etc.)",
    "units": ["unit1", "unit2", ...],
    "regulations": ["Regulation 1", ...],
    "thresholds": {{
      "threshold_name": "threshold_value"
    }}
  }},
  "source_documents": ["business_requirements.md"]
}}

Focus on extracting concrete, specific information that will help generate domain-specific graph analysis insights.
"""

        response = await self.llm_provider.generate_async(
            prompt=analysis_prompt, max_tokens=2000, temperature=0.3
        )

        # Parse JSON from response
        try:
            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(response[json_start:json_end])
            else:
                analysis = json.loads(response)

            return analysis
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse domain analysis JSON: {e}")
            logger.error(f"Response was: {response}")
            # Return minimal fallback
            return {
                "industry_key": "custom",
                "industry_display_name": "Custom Domain",
                "business_focus": "Graph analysis",
                "key_entities": {"nodes": [], "edges": []},
                "source_documents": [],
            }

    async def generate_prompt(
        self, domain_analysis: Dict[str, Any], base_vertical: Optional[str] = None
    ) -> str:
        """
        Generate industry-specific LLM prompt for analysis.

        Args:
            domain_analysis: Results from analyze_domain()
            base_vertical: Optional existing vertical to base prompt on

        Returns:
            Generated prompt string
        """
        # Get base prompt if specified
        base_prompt_context = ""
        if base_vertical:
            try:
                from graph_analytics_ai.ai.reporting.prompts import get_industry_prompt

                base_prompt = get_industry_prompt(base_vertical)
                base_prompt_context = f"\n\nReference this example prompt structure:\n\n{base_prompt[:2000]}...\n\n"
            except Exception as e:
                logger.warning(f"Could not load base vertical {base_vertical}: {e}")

        # Create prompt generation request
        generation_prompt = f"""Generate a comprehensive LLM prompt for analyzing graph data in the following domain:

**Industry:** {domain_analysis['industry_display_name']}
**Business Focus:** {domain_analysis['business_focus']}

**Key Entities:**
Nodes: {', '.join(domain_analysis['key_entities'].get('nodes', [])[:10])}
Edges: {', '.join(domain_analysis['key_entities'].get('edges', [])[:10])}

**Key Metrics:** {', '.join(domain_analysis.get('key_metrics', [])[:10])}

**Terminology:**
{json.dumps(domain_analysis.get('terminology', {}), indent=2)}

{base_prompt_context}

Generate a detailed prompt that will guide an LLM to:
1. Understand the domain context (nodes, edges, business goals)
2. Know what metrics and patterns to look for
3. Use domain-specific terminology correctly
4. Provide actionable business insights
5. Include risk classifications and recommended actions

The prompt should be similar in structure to industry prompts like those for ad-tech or fintech,
but customized for this specific domain. Make it comprehensive (1500-3000 words) and include:

- Domain Context section (nodes, edges, business goals)
- Key Metrics to Analyze section
- Specific Patterns to Look For section (with examples)
- Analysis Framework section (how to quantify, assess impact, classify risk, recommend actions)
- Output Format section (how insights should be structured)

Return ONLY the prompt text, no explanations before or after.
"""

        response = await self.llm_provider.generate_async(
            prompt=generation_prompt, max_tokens=4000, temperature=0.7
        )

        return response.strip()

    async def generate_pattern_definitions(
        self, domain_analysis: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate pattern definitions for graph algorithms.

        Args:
            domain_analysis: Results from analyze_domain()

        Returns:
            Dictionary mapping algorithm names to pattern definitions
        """
        # Use LLM to generate pattern definitions
        pattern_prompt = f"""Generate pattern definitions for graph algorithm analysis in this domain:

**Industry:** {domain_analysis['industry_display_name']}
**Business Focus:** {domain_analysis['business_focus']}
**Key Entities:** {json.dumps(domain_analysis['key_entities'], indent=2)}

For each of these graph algorithms, define 2-3 important patterns to detect:

1. WCC (Weakly Connected Components) - What connected groups indicate in this domain?
2. PageRank - What does centrality/importance mean in this domain?

For each pattern, provide:
- name: Pattern identifier (snake_case)
- description: What this pattern indicates
- indicators: List of signals that indicate this pattern
- risk_level: CRITICAL, HIGH, MEDIUM, or LOW
- example: Brief example of how this manifests
- business_impact: What actions to take when detected

Return as JSON:
{{
  "wcc": [
    {{
      "name": "pattern_name",
      "description": "...",
      "indicators": ["..."],
      "risk_level": "HIGH",
      "example": "...",
      "business_impact": "..."
    }}
  ],
  "pagerank": [...]
}}

Return ONLY valid JSON, no explanations.
"""

        response = await self.llm_provider.generate_async(
            prompt=pattern_prompt, max_tokens=2000, temperature=0.5
        )

        try:
            # Extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                patterns = json.loads(response[json_start:json_end])
            else:
                patterns = json.loads(response)

            return patterns
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse pattern definitions JSON: {e}")
            # Return empty patterns
            return {"wcc": [], "pagerank": [], "cycles": []}

    async def _extract_graph_schema(
        self, graph_connection: Any, graph_name: str
    ) -> str:
        """Extract schema information from graph database."""
        try:
            # Try to get collections
            if hasattr(graph_connection, "list_collections"):
                collections = graph_connection.list_collections()
                schema_parts = ["Collections:"]
                for coll in collections[:20]:  # Limit to first 20
                    schema_parts.append(f"  - {coll.get('name', coll)}")
                return "\n".join(schema_parts)
            elif hasattr(graph_connection, "db"):
                db = graph_connection.db
                collections = [c["name"] for c in db.collections()]
                return "Collections: " + ", ".join(collections[:20])
        except Exception as e:
            logger.debug(f"Could not extract schema: {e}")

        return ""

    async def save_vertical(self, vertical: Dict[str, Any], output_path: Path) -> None:
        """
        Save generated vertical to file.

        Args:
            vertical: Dictionary containing the custom vertical configuration
            output_path: Path where to save the vertical JSON file
        """
        from graph_analytics_ai.ai.reporting.custom_verticals import (
            save_custom_vertical,
        )

        save_custom_vertical(vertical, output_path)
