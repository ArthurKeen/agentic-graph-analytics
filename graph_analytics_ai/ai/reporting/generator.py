"""
Report generator for GAE analysis results.

Generates actionable intelligence reports with insights and recommendations.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from ..llm.base import LLMProvider
from ..llm.factory import create_llm_provider
from ..execution.models import ExecutionResult, AnalysisJob
from .models import (
    AnalysisReport,
    ReportSection,
    Insight,
    Recommendation,
    InsightType,
    RecommendationType,
    ReportFormat,
)


class ReportGenerator:
    """
    Generates actionable intelligence reports from GAE analysis results.

    Uses LLM to interpret results and generate business insights.

    Example:
        >>> from graph_analytics_ai.ai.reporting import ReportGenerator
        >>>
        >>> generator = ReportGenerator()
        >>> report = generator.generate_report(execution_result)
        >>>
        >>> print(report.summary)
        >>> for insight in report.insights:
        ...     print(f"- {insight.title}")
        >>>
        >>> # Export as markdown
        >>> markdown = generator.format_report(report, ReportFormat.MARKDOWN)
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        use_llm_interpretation: bool = True,
        enable_charts: bool = True,
    ):
        """
        Initialize report generator.

        Args:
            llm_provider: LLM provider for interpretation (creates default if None)
            use_llm_interpretation: Whether to use LLM for insights
            enable_charts: Whether to generate interactive charts
        """
        self.llm_provider = llm_provider or create_llm_provider()
        self.use_llm_interpretation = use_llm_interpretation
        self.enable_charts = enable_charts

        # Import chart generator if enabled
        if self.enable_charts:
            try:
                from .chart_generator import ChartGenerator, is_plotly_available

                if is_plotly_available():
                    self.chart_generator = ChartGenerator()
                else:
                    self.chart_generator = None
                    self.enable_charts = False
                    print(
                        "Warning: Plotly not available. Charts disabled. Install with: pip install plotly"
                    )
            except ImportError:
                self.chart_generator = None
                self.enable_charts = False
                print(
                    "Warning: Chart generation not available. Install plotly: pip install plotly"
                )
        else:
            self.chart_generator = None

    def generate_report(
        self,
        execution_result: ExecutionResult,
        context: Optional[Dict[str, Any]] = None,
    ) -> AnalysisReport:
        """
        Generate report from execution result.

        Args:
            execution_result: Result from analysis execution
            context: Optional additional context (use case, requirements, etc.)

        Returns:
            Complete analysis report
        """
        job = execution_result.job

        # Create base report
        report = AnalysisReport(
            title=f"Analysis Report: {job.template_name}",
            summary="",  # Will be generated
            generated_at=datetime.now(),
            algorithm=job.algorithm,
            dataset_info={
                "job_id": job.job_id,
                "execution_time": job.execution_time_seconds,
                "result_count": job.result_count or len(execution_result.results),
                "completed_at": (
                    job.completed_at.isoformat() if job.completed_at else None
                ),
            },
        )

        # Extract metrics from results
        report.metrics = self._extract_metrics(execution_result)

        # Generate insights
        if self.use_llm_interpretation and execution_result.results:
            report.insights = self._generate_insights_llm(execution_result, context)
        else:
            report.insights = self._generate_insights_heuristic(execution_result)

        # Generate recommendations
        report.recommendations = self._generate_recommendations(
            report.insights, context
        )

        # Generate summary
        report.summary = self._generate_summary(report)

        # Generate charts (if enabled)
        if self.enable_charts and self.chart_generator and execution_result.results:
            report.metadata["charts"] = self._generate_charts(execution_result)

        # Create report sections
        report.sections = self._create_sections(report, execution_result)

        return report

    def generate_batch_report(
        self,
        execution_results: List[ExecutionResult],
        title: str = "Batch Analysis Report",
    ) -> AnalysisReport:
        """
        Generate a combined report from multiple analyses.

        Args:
            execution_results: List of execution results
            title: Report title

        Returns:
            Combined analysis report
        """
        report = AnalysisReport(
            title=title,
            summary="",  # Will be generated
            generated_at=datetime.now(),
            algorithm="multiple",
            dataset_info={
                "total_analyses": len(execution_results),
                "successful": sum(1 for r in execution_results if r.success),
                "failed": sum(1 for r in execution_results if not r.success),
            },
        )

        # Combine insights from all analyses
        all_insights = []
        all_recommendations = []

        for result in execution_results:
            if result.success:
                individual_report = self.generate_report(result)
                all_insights.extend(individual_report.insights)
                all_recommendations.extend(individual_report.recommendations)

        report.insights = all_insights
        report.recommendations = all_recommendations

        # Generate combined summary
        report.summary = self._generate_batch_summary(report, execution_results)

        # Create combined sections
        report.sections = self._create_batch_sections(report, execution_results)

        return report

    def format_report(
        self, report: AnalysisReport, format: ReportFormat = ReportFormat.MARKDOWN
    ) -> str:
        """
        Format report for output.

        Args:
            report: Report to format
            format: Output format

        Returns:
            Formatted report string
        """
        if format == ReportFormat.MARKDOWN:
            return self._format_markdown(report)
        elif format == ReportFormat.JSON:
            import json

            return json.dumps(report.to_dict(), indent=2)
        elif format == ReportFormat.HTML:
            return self._format_html(report)
        elif format == ReportFormat.TEXT:
            return self._format_text(report)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _extract_metrics(self, execution_result: ExecutionResult) -> Dict[str, Any]:
        """Extract key metrics from results."""
        results = execution_result.results

        if not results:
            return {}

        metrics = {
            "total_results": len(results),
            "has_scores": False,
            "min_score": None,
            "max_score": None,
            "avg_score": None,
        }

        # Try to extract common score fields
        score_fields = ["score", "rank", "centrality", "pagerank", "result", "value"]

        for field in score_fields:
            scores = [
                r.get(field)
                for r in results
                if field in r and isinstance(r.get(field), (int, float))
            ]
            if scores:
                metrics["has_scores"] = True
                metrics["score_field"] = field
                metrics["min_score"] = min(scores)
                metrics["max_score"] = max(scores)
                metrics["avg_score"] = sum(scores) / len(scores)
                break

        return metrics

    def _generate_insights_heuristic(
        self, execution_result: ExecutionResult
    ) -> List[Insight]:
        """Generate insights using heuristics (no LLM)."""
        insights = []
        job = execution_result.job
        results = execution_result.results

        if not results:
            insights.append(
                Insight(
                    title="No Results Generated",
                    description="The analysis completed but produced no results. This may indicate the graph structure doesn't support this algorithm or no qualifying nodes were found.",
                    insight_type=InsightType.KEY_FINDING,
                    confidence=1.0,
                    business_impact="Unable to derive insights without results",
                )
            )
            return insights

        # Algorithm-specific insights
        if job.algorithm == "pagerank":
            insights.extend(self._pagerank_insights(results))
        elif job.algorithm == "label_propagation":
            insights.extend(self._label_propagation_insights(results))
        elif job.algorithm == "wcc":
            insights.extend(self._wcc_insights(results))
        elif job.algorithm == "scc":
            insights.extend(self._scc_insights(results))
        elif job.algorithm == "betweenness":
            insights.extend(self._betweenness_insights(results))

        return insights

    def _generate_insights_llm(
        self,
        execution_result: ExecutionResult,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Insight]:
        """Generate insights using LLM interpretation with validation."""
        try:
            # Prepare data for LLM
            job = execution_result.job
            results_sample = execution_result.results[:10]  # Top 10 for context

            prompt = self._create_insight_prompt(job, results_sample, context)

            # Get LLM interpretation
            response = self.llm_provider.generate(prompt)

            # Parse LLM response into insights
            insights = self._parse_llm_insights(response.content)

            # Validate insights
            insights = self._validate_insights(insights)

            return insights

        except Exception as e:
            # Fallback to heuristic insights
            print(f"LLM insight generation failed, using heuristics: {e}")
            return self._generate_insights_heuristic(execution_result)

    def _validate_insights(self, insights: List[Insight]) -> List[Insight]:
        """
        Validate insight quality and add warnings for low-quality insights.

        Args:
            insights: List of insights to validate

        Returns:
            Validated insights (may filter out very low quality ones)
        """
        import logging

        logger = logging.getLogger(__name__)

        validated_insights = []

        for insight in insights:
            warnings = []

            # Check confidence score
            if insight.confidence < 0.3:
                logger.warning(
                    f"Very low confidence insight ({insight.confidence:.2f}): {insight.title}"
                )
                warnings.append("Very low confidence - use with caution")

            # Check business impact
            if not insight.business_impact:
                insight.business_impact = "Impact unknown - requires further analysis"
                warnings.append("Business impact not specified")

            # Check description quality
            if not insight.description or len(insight.description) < 20:
                warnings.append("Description too brief")
                insight.confidence *= 0.7

            # Check title quality
            if not insight.title or len(insight.title) < 10:
                warnings.append("Title too brief")
                insight.confidence *= 0.8

            # Only include insights above minimum threshold
            if insight.confidence >= 0.2:  # Very low bar - just filter garbage
                validated_insights.append(insight)
                if warnings:
                    logger.debug(
                        f"Insight validation warnings for '{insight.title}': {'; '.join(warnings)}"
                    )
            else:
                logger.warning(
                    f"Filtered out very low quality insight: {insight.title} (confidence: {insight.confidence:.2f})"
                )

        if len(validated_insights) == 0 and len(insights) > 0:
            logger.error(
                "All insights filtered out due to low quality - returning original insights"
            )
            return insights  # Better to return something than nothing

        return validated_insights

    def _generate_recommendations(
        self, insights: List[Insight], context: Optional[Dict[str, Any]] = None
    ) -> List[Recommendation]:
        """Generate recommendations from insights."""
        recommendations = []

        for insight in insights:
            # Create recommendation based on insight
            if insight.insight_type == InsightType.ANOMALY:
                recommendations.append(
                    Recommendation(
                        title=f"Investigate: {insight.title}",
                        description=f"Further investigation needed: {insight.description}",
                        recommendation_type=RecommendationType.INVESTIGATION,
                        priority="high",
                        effort="medium",
                        expected_impact="Identify root cause and potential issues",
                        related_insights=[insight.title],
                    )
                )

            elif insight.confidence >= 0.8:
                recommendations.append(
                    Recommendation(
                        title=f"Action: {insight.title}",
                        description=f"Take action based on: {insight.description}",
                        recommendation_type=RecommendationType.ACTION,
                        priority="medium",
                        effort="low",
                        expected_impact=insight.business_impact or "Improve outcomes",
                        related_insights=[insight.title],
                    )
                )

        return recommendations[:10]  # Limit to top 10

    def _generate_summary(self, report: AnalysisReport) -> str:
        """Generate executive summary."""
        lines = []

        lines.append(
            f"Analysis of {report.dataset_info.get('result_count', 0)} results using {report.algorithm} algorithm."
        )

        if report.insights:
            lines.append(f"Found {len(report.insights)} key insights.")

        if report.recommendations:
            high_priority = len(
                [
                    r
                    for r in report.recommendations
                    if r.priority in ("high", "critical")
                ]
            )
            if high_priority > 0:
                lines.append(
                    f"Generated {len(report.recommendations)} recommendations, {high_priority} high priority."
                )

        return " ".join(lines)

    def _generate_batch_summary(
        self, report: AnalysisReport, execution_results: List[ExecutionResult]
    ) -> str:
        """Generate summary for batch report."""
        success_count = report.dataset_info.get("successful", 0)
        total_count = report.dataset_info.get("total_analyses", 0)

        return (
            f"Batch analysis of {total_count} jobs completed with {success_count} successful. "
            f"Generated {len(report.insights)} insights and {len(report.recommendations)} recommendations."
        )

    def _pagerank_insights(self, results: List[Dict[str, Any]]) -> List[Insight]:
        """Generate insights for PageRank results."""
        insights = []

        if results:
            # Top nodes by rank
            top_node = results[0] if len(results) > 0 else None
            if top_node:
                insights.append(
                    Insight(
                        title="Most Influential Node Identified",
                        description=f"Node {top_node.get('_key', 'unknown')} has the highest PageRank score.",
                        insight_type=InsightType.KEY_FINDING,
                        confidence=0.95,
                        supporting_data={"top_node": top_node},
                        business_impact="Focus engagement efforts on this influential node",
                    )
                )

        return insights

    def _label_propagation_insights(
        self, results: List[Dict[str, Any]]
    ) -> List[Insight]:
        """Generate insights for Label Propagation community detection."""
        insights = []

        # Count communities/labels
        labels = set(r.get("label", 0) for r in results)

        insights.append(
            Insight(
                title=f"Discovered {len(labels)} Communities",
                description=f"Graph contains {len(labels)} distinct communities via label propagation.",
                insight_type=InsightType.PATTERN,
                confidence=0.9,
                supporting_data={"community_count": len(labels)},
                business_impact="Target strategies per community segment",
            )
        )

        return insights

    def _wcc_insights(self, results: List[Dict[str, Any]]) -> List[Insight]:
        """Generate insights for Weakly Connected Components."""
        insights = []

        # Count components
        components = set(r.get("component", 0) for r in results)

        insights.append(
            Insight(
                title=f"Found {len(components)} Connected Components",
                description=f"Graph has {len(components)} separate weakly connected components.",
                insight_type=InsightType.PATTERN,
                confidence=0.95,
                supporting_data={"component_count": len(components)},
                business_impact="Identify isolated clusters and network structure",
            )
        )

        return insights

    def _scc_insights(self, results: List[Dict[str, Any]]) -> List[Insight]:
        """Generate insights for Strongly Connected Components."""
        insights = []

        # Count components
        components = set(r.get("component", 0) for r in results)

        insights.append(
            Insight(
                title=f"Found {len(components)} Strongly Connected Components",
                description=f"Graph has {len(components)} strongly connected components with bidirectional paths.",
                insight_type=InsightType.PATTERN,
                confidence=0.95,
                supporting_data={"scc_count": len(components)},
                business_impact="Understand reciprocal relationships and cycles",
            )
        )

        return insights

    def _betweenness_insights(self, results: List[Dict[str, Any]]) -> List[Insight]:
        """Generate insights for Betweenness Centrality."""
        insights = []

        if results:
            # Find highest betweenness nodes
            top_nodes = sorted(
                results, key=lambda x: x.get("betweenness", 0), reverse=True
            )[:5]

            insights.append(
                Insight(
                    title="Top Bridge Nodes Identified",
                    description=f"Found {len(top_nodes)} nodes with highest betweenness centrality acting as bridges.",
                    insight_type=InsightType.KEY_FINDING,
                    confidence=0.9,
                    supporting_data={
                        "top_bridge_nodes": [n.get("_key") for n in top_nodes]
                    },
                    business_impact="Focus on bridge nodes for network flow optimization",
                )
            )

        return insights

    def _create_insight_prompt(
        self,
        job: AnalysisJob,
        results_sample: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """Create prompt for LLM insight generation with algorithm-specific guidance and business context."""

        # Extract context information
        context = context or {}
        requirements = context.get("requirements", {})
        schema_analysis = context.get("schema_analysis", {})
        use_case = context.get("use_case", {})

        # Build business context section
        business_context = ""
        if use_case:
            business_context += f"\n**Use Case**: {use_case.get('title', 'N/A')}"
            if use_case.get("objective"):
                business_context += f"\n**Objective**: {use_case.get('objective')}"

        if requirements.get("domain"):
            business_context += f"\n**Domain**: {requirements['domain']}"

        if requirements.get("objectives"):
            objectives = requirements["objectives"]
            if objectives:
                business_context += "\n**Business Objectives**:"
                for obj in objectives[:2]:  # Top 2 objectives
                    business_context += (
                        f"\n  - {obj.get('title')}: {obj.get('description', '')}"
                    )
                    if obj.get("success_criteria"):
                        business_context += f"\n    Success Criteria: {', '.join(obj['success_criteria'][:2])}"

        # Build technical context section
        technical_context = ""
        if schema_analysis.get("domain"):
            technical_context += f"\n**Graph Domain**: {schema_analysis['domain']}"
        if schema_analysis.get("complexity_score"):
            technical_context += (
                f"\n**Graph Complexity**: {schema_analysis['complexity_score']}/10"
            )
        if schema_analysis.get("key_entities"):
            technical_context += (
                f"\n**Key Entities**: {', '.join(schema_analysis['key_entities'][:5])}"
            )

        # Algorithm-specific guidance
        algorithm_guidance = {
            "pagerank": """
Focus on:
- Top influencers (nodes with highest rank)
- Power law distribution (do few nodes dominate?)
- Rank concentration (top 10% hold what % of total rank?)
- Unexpected high-rank nodes (low degree but high rank = bridge nodes)

Business questions to answer:
- Who are the key influencers?
- Is influence concentrated or distributed?
- Which nodes punch above their weight?
""",
            "wcc": """
Focus on:
- Number and size of components
- Largest component (what % of total nodes?)
- Singleton nodes (isolated entities)
- Component distribution (power law? many small clusters?)

Business questions to answer:
- Is the graph well-connected or fragmented?
- What do disconnected clusters represent?
- Should we investigate why singletons are isolated?
""",
            "scc": """
Focus on:
- Strongly connected components with bidirectional paths
- Cycle detection (circular relationships)
- Component hierarchy (how SCCs relate to WCCs)

Business questions to answer:
- Where are the reciprocal relationships?
- Do cycles indicate problems or natural patterns?
- How does strong connectivity differ from weak?
""",
            "label_propagation": """
Focus on:
- Community/cluster count and sizes
- Community cohesion (how tight are clusters?)
- Cross-community edges (weak connections between groups)

Business questions to answer:
- What natural communities exist?
- Are communities isolated or interconnected?
- What defines each community's identity?
""",
            "betweenness": """
Focus on:
- Bridge nodes (high betweenness, critical for flow)
- Bottlenecks (single points of failure)
- Bridge vs hub distinction (high betweenness + low degree = pure bridge)

Business questions to answer:
- Which nodes are critical for connectivity?
- What happens if a bridge node fails?
- How to reduce dependency on bottlenecks?
""",
        }

        guidance = algorithm_guidance.get(job.algorithm, "")

        # Example insights for few-shot learning
        example_insights = """
# Example Insight 1 (PageRank):
- Title: Top 5 Nodes Control 82% of Network Influence
  Description: Analysis reveals extreme influence concentration. The 5 highest-ranked nodes (representing 0.1% of total) account for 82% of cumulative PageRank score. Node "Product/P123" leads with rank 0.347, 10x higher than median.
  Business Impact: Focus marketing efforts and quality assurance on these 5 critical nodes. Their performance disproportionately affects overall network health and customer perception.
  Confidence: 0.95

# Example Insight 2 (WCC):
- Title: Network Fragmented into 3 Major Clusters and 127 Singletons
  Description: Weak component analysis reveals 3 large connected clusters (45K, 12K, 3K nodes) and 127 completely isolated singleton nodes. Main cluster contains 75% of all nodes. Singletons are primarily recent additions (< 30 days old).
  Business Impact: Investigate why 127 entities are isolated - likely data quality issues or onboarding problems. Connect main clusters to improve cross-cluster collaboration and information flow.
  Confidence: 0.92

# Example Insight 3 (Betweenness):
- Title: 7 Critical Bridge Nodes Connect All Major Departments
  Description: Seven nodes exhibit exceptionally high betweenness centrality (>0.08) despite moderate degree (15-25 connections). These nodes bridge otherwise disconnected departments. Node "User/U456" connects Engineering, Sales, and Support.
  Business Impact: These 7 individuals are organizational bottlenecks. Ensure backup personnel, document their knowledge, and consider reorganization to reduce dependency. If any leave, communication pathways break.
  Confidence: 0.89
"""

        prompt = f"""Analyze these {job.algorithm} results in the context of business objectives and provide actionable insights.

{example_insights}

# Business Context
{business_context if business_context else "No business context provided"}

# Technical Context
{technical_context if technical_context else "No technical context provided"}
Algorithm: {job.algorithm}
Total Results: {len(results_sample)}

# Algorithm-Specific Guidance
{guidance}

# Results to Analyze

Sample Results (showing top entries):
{results_sample}

# Your Analysis Task

Provide 3-5 key insights following the same format and analytical depth as the examples above.
Connect your insights to the business objectives and success criteria mentioned in the context.

- Title: [brief, specific title with numbers]
  Description: [detailed finding with concrete data points and context]
  Business Impact: [specific, actionable recommendations tied to business objectives]
  Confidence: [0.0-1.0 based on data quality and result clarity]

Focus on:
1. How results relate to stated business objectives
2. Concrete numbers and percentages
3. Unexpected or actionable patterns
4. Specific recommendations that address success criteria
5. Business implications (not just technical observations)
"""

        return prompt

    def _parse_llm_insights(self, llm_response: str) -> List[Insight]:
        """Parse LLM response into insight objects."""
        # Simple parsing - could be enhanced
        insights = []

        # For now, create one insight from the response
        insights.append(
            Insight(
                title="LLM Analysis",
                description=llm_response[:500],  # Truncate if too long
                insight_type=InsightType.KEY_FINDING,
                confidence=0.85,
                business_impact="Derived from AI analysis of results",
            )
        )

        return insights

    def _generate_charts(self, execution_result: ExecutionResult) -> Dict[str, str]:
        """
        Generate algorithm-specific charts for the report.

        Args:
            execution_result: Execution result with algorithm and results

        Returns:
            Dictionary of chart HTML strings
        """
        if not self.chart_generator:
            return {}

        algorithm = execution_result.job.algorithm
        results = execution_result.results

        try:
            if algorithm == "pagerank":
                return self.chart_generator.generate_pagerank_charts(results)
            elif algorithm == "wcc":
                return self.chart_generator.generate_wcc_charts(results)
            elif algorithm == "scc":
                return self.chart_generator.generate_scc_charts(results)
            elif algorithm == "betweenness":
                return self.chart_generator.generate_betweenness_charts(results)
            elif algorithm == "label_propagation":
                return self.chart_generator.generate_label_propagation_charts(results)
            else:
                # No specific chart generator for this algorithm
                return {}
        except Exception as e:
            print(f"Warning: Chart generation failed for {algorithm}: {e}")
            return {}

    def _create_sections(
        self, report: AnalysisReport, execution_result: ExecutionResult
    ) -> List[ReportSection]:
        """Create report sections."""
        sections = []

        # Overview section
        sections.append(
            ReportSection(
                title="1. Overview",
                content=self._create_overview_content(report, execution_result),
            )
        )

        # Key Metrics section
        sections.append(
            ReportSection(
                title="2. Key Metrics", content=self._create_metrics_content(report)
            )
        )

        # Insights section
        if report.insights:
            sections.append(
                ReportSection(
                    title="3. Key Insights",
                    content=self._create_insights_content(report.insights),
                )
            )

        # Recommendations section
        if report.recommendations:
            sections.append(
                ReportSection(
                    title="4. Recommendations",
                    content=self._create_recommendations_content(
                        report.recommendations
                    ),
                )
            )

        # Top Results section
        if execution_result.results:
            sections.append(
                ReportSection(
                    title="5. Top Results",
                    content=self._create_top_results_content(
                        execution_result.results[:20]
                    ),
                )
            )

        return sections

    def _create_batch_sections(
        self, report: AnalysisReport, execution_results: List[ExecutionResult]
    ) -> List[ReportSection]:
        """Create sections for batch report."""
        sections = []

        # Summary section
        sections.append(
            ReportSection(title="1. Executive Summary", content=report.summary)
        )

        # Per-analysis sections
        for i, result in enumerate(execution_results, 1):
            if result.success:
                sections.append(
                    ReportSection(
                        title=f"{i+1}. {result.job.template_name}",
                        content=f"Algorithm: {result.job.algorithm}, Runtime: {result.job.execution_time_seconds:.1f}s",
                    )
                )

        return sections

    def _create_overview_content(
        self, report: AnalysisReport, execution_result: ExecutionResult
    ) -> str:
        """Create overview section content."""
        job = execution_result.job

        lines = [
            f"**Algorithm:** {job.algorithm}",
            f"**Job ID:** {job.job_id}",
            (
                f"**Execution Time:** {job.execution_time_seconds:.2f}s"
                if job.execution_time_seconds
                else "**Execution Time:** N/A"
            ),
            f"**Results:** {job.result_count or len(execution_result.results)} records",
            "",
            report.summary,
        ]

        return "\n".join(lines)

    def _create_metrics_content(self, report: AnalysisReport) -> str:
        """Create metrics section content."""
        if not report.metrics:
            return "_No metrics available._"

        lines = []
        for key, value in report.metrics.items():
            if isinstance(value, float):
                lines.append(f"- **{key}:** {value:.4f}")
            else:
                lines.append(f"- **{key}:** {value}")

        return "\n".join(lines)

    def _create_insights_content(self, insights: List[Insight]) -> str:
        """Create insights section content."""
        lines = []

        for i, insight in enumerate(insights, 1):
            lines.append(f"### {i}. {insight.title}")
            lines.append(f"**Type:** {insight.insight_type.value}")
            lines.append(f"**Confidence:** {insight.confidence*100:.0f}%")
            lines.append("")
            lines.append(insight.description)

            if insight.business_impact:
                lines.append("")
                lines.append(f"**Business Impact:** {insight.business_impact}")

            lines.append("")

        return "\n".join(lines)

    def _create_recommendations_content(
        self, recommendations: List[Recommendation]
    ) -> str:
        """Create recommendations section content."""
        lines = []

        # Group by priority
        critical = [r for r in recommendations if r.priority == "critical"]
        high = [r for r in recommendations if r.priority == "high"]
        medium = [r for r in recommendations if r.priority == "medium"]
        [r for r in recommendations if r.priority == "low"]

        if critical:
            lines.append("### Critical Priority")
            for rec in critical:
                lines.append(f"- **{rec.title}**")
                lines.append(f"  {rec.description}")
            lines.append("")

        if high:
            lines.append("### High Priority")
            for rec in high:
                lines.append(f"- **{rec.title}**")
                lines.append(f"  {rec.description}")
            lines.append("")

        if medium:
            lines.append("### Medium Priority")
            for rec in medium[:5]:  # Limit medium priority
                lines.append(f"- **{rec.title}**")
            lines.append("")

        return "\n".join(lines)

    def _create_top_results_content(self, results: List[Dict[str, Any]]) -> str:
        """Create top results section content."""
        lines = []

        lines.append("| Rank | Key | Score |")
        lines.append("|------|-----|-------|")

        score_fields = ["score", "rank", "centrality", "pagerank", "result", "value"]
        score_field = None

        for field in score_fields:
            if results and field in results[0]:
                score_field = field
                break

        for i, result in enumerate(results[:20], 1):
            key = result.get("_key", result.get("vertex", "N/A"))
            score = result.get(score_field, "N/A") if score_field else "N/A"

            if isinstance(score, float):
                score_str = f"{score:.6f}"
            else:
                score_str = str(score)

            lines.append(f"| {i} | {key} | {score_str} |")

        return "\n".join(lines)

    def _format_markdown(self, report: AnalysisReport) -> str:
        """Format report as markdown."""
        lines = []

        # Title
        lines.append(f"# {report.title}")
        lines.append("")
        lines.append(
            f"*Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}*"
        )
        lines.append("")

        # Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(report.summary)
        lines.append("")

        # Sections
        for section in report.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")

        return "\n".join(lines)

    def _format_html(self, report: AnalysisReport) -> str:
        """Format report as HTML."""
        # Convert markdown to HTML (basic)
        markdown = self._format_markdown(report)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{report.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 2px solid #ddd; padding-bottom: 5px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <pre>{markdown}</pre>
</body>
</html>"""

        return html

    def _format_text(self, report: AnalysisReport) -> str:
        """Format report as plain text."""
        markdown = self._format_markdown(report)
        # Remove markdown formatting (basic)
        text = markdown.replace("#", "").replace("**", "").replace("*", "")
        return text


def generate_report(
    execution_result: ExecutionResult, format: ReportFormat = ReportFormat.MARKDOWN
) -> str:
    """
    Convenience function to generate and format a report.

    Args:
        execution_result: Execution result to report on
        format: Output format

    Returns:
        Formatted report string
    """
    generator = ReportGenerator()
    report = generator.generate_report(execution_result)
    return generator.format_report(report, format)
