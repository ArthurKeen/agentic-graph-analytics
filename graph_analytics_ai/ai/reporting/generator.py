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
        Validate insight quality and filter low-quality insights.
        
        Quality criteria:
        - Confidence >= 0.5 (increased from 0.2)
        - Title length >= 15 characters (more than "Top Node Found")
        - Description length >= 100 characters (substantive analysis)
        - Business impact is specific (not generic templates)
        - Contains numbers/metrics (data-driven)
        
        Args:
            insights: List of insights to validate

        Returns:
            Validated insights (may filter out very low quality ones)
        """
        import logging
        import re

        logger = logging.getLogger(__name__)

        validated_insights = []

        for insight in insights:
            quality_score = 1.0
            issues = []

            # Check 1: Confidence threshold
            if insight.confidence < 0.5:
                issues.append(f"Low confidence ({insight.confidence:.2f})")
                quality_score *= 0.5

            # Check 2: Title quality
            if len(insight.title) < 15:
                issues.append("Title too brief")
                quality_score *= 0.7

            # Check 3: Description quality
            if len(insight.description) < 100:
                issues.append(f"Description too brief ({len(insight.description)} chars)")
                quality_score *= 0.6

            # Check 4: Contains specific numbers/metrics
            has_numbers = bool(re.search(r'\d+\.?\d*%|\d+\.\d+|\d{2,}', insight.description))
            if not has_numbers:
                issues.append("No specific metrics/numbers")
                quality_score *= 0.7

            # Check 5: Business impact specificity
            generic_impacts = [
                'further analysis',
                'requires investigation',
                'derived from',
                'focus on',
                'improve'
            ]
            if any(phrase in insight.business_impact.lower() for phrase in generic_impacts):
                issues.append("Generic business impact")
                quality_score *= 0.8

            # Check 6: Title is not generic
            generic_titles = [
                'llm analysis',
                'analysis results',
                'insight',
                'finding',
                'most influential node identified'  # Too generic
            ]
            if insight.title.lower() in generic_titles:
                issues.append("Generic title")
                quality_score *= 0.5

            # Adjust confidence based on quality score
            insight.confidence *= quality_score

            # Minimum threshold for inclusion (raised from 0.2 to 0.4)
            if insight.confidence >= 0.4:
                validated_insights.append(insight)
                if issues:
                    logger.info(
                        f"Insight quality concerns: '{insight.title[:50]}' - {', '.join(issues)} (adjusted confidence: {insight.confidence:.2f})"
                    )
            else:
                logger.warning(
                    f"Filtered low-quality insight: '{insight.title[:50]}' (confidence: {insight.confidence:.2f}, issues: {', '.join(issues)})"
                )

        # If all insights filtered, log error but keep best ones
        if len(validated_insights) == 0 and len(insights) > 0:
            logger.error(
                "All insights filtered! Keeping top 2 by original confidence"
            )
            sorted_insights = sorted(insights, key=lambda x: x.confidence, reverse=True)
            validated_insights = sorted_insights[:2]

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
        """Generate statistical insights for PageRank results."""
        insights = []
        
        if not results:
            return insights
        
        # Extract scores
        scores = [r.get('result', 0) for r in results if 'result' in r]
        if not scores:
            return insights
        
        # Statistical analysis
        total_score = sum(scores)
        scores_sorted = sorted(scores, reverse=True)
        
        # Insight 1: Influence concentration
        if len(scores_sorted) >= 5:
            top_5_score = sum(scores_sorted[:5])
            top_5_pct = (top_5_score / total_score * 100) if total_score > 0 else 0
            
            insights.append(
                Insight(
                    title=f"Top 5 Nodes Hold {top_5_pct:.1f}% of Total Influence",
                    description=f"Analysis of {len(results)} nodes reveals influence concentration. The top 5 nodes account for {top_5_pct:.1f}% of cumulative PageRank score (total: {total_score:.4f}). This {'high' if top_5_pct > 50 else 'moderate' if top_5_pct > 30 else 'low'} concentration indicates {'few key influencers dominate' if top_5_pct > 50 else 'distributed influence pattern'}.",
                    insight_type=InsightType.PATTERN,
                    confidence=0.90,
                    supporting_data={
                        "top_5_score": top_5_score,
                        "total_score": total_score,
                        "concentration_pct": top_5_pct
                    },
                    business_impact=f"{'Focus resources on top 5 nodes - they drive majority of influence' if top_5_pct > 50 else 'Distributed influence allows for broader engagement strategy'}",
                )
            )
        
        # Insight 2: Top influencer details
        if len(results) > 0:
            top_node = results[0]
            top_score = top_node.get('result', 0)
            median_score = scores_sorted[len(scores_sorted)//2] if scores_sorted else 0
            multiplier = (top_score / median_score) if median_score > 0 else 0
            
            insights.append(
                Insight(
                    title=f"Leading Node {multiplier:.1f}x More Influential Than Median",
                    description=f"Node '{top_node.get('_key', 'unknown')}' has PageRank score of {top_score:.6f}, which is {multiplier:.1f}x higher than median node (score: {median_score:.6f}). This node is {'an extreme outlier' if multiplier > 10 else 'significantly more important' if multiplier > 5 else 'notably influential'}.",
                    insight_type=InsightType.KEY_FINDING,
                    confidence=0.95,
                    supporting_data={"top_node": top_node, "multiplier": multiplier},
                    business_impact=f"Prioritize engagement with this node. It has disproportionate network impact. Monitor for single point of failure risk.",
                )
            )
        
        # Insight 3: Long tail analysis
        if len(scores_sorted) > 10:
            bottom_50_score = sum(scores_sorted[len(scores_sorted)//2:])
            bottom_50_pct = (bottom_50_score / total_score * 100) if total_score > 0 else 0
            
            if bottom_50_pct < 10:
                insights.append(
                    Insight(
                        title=f"Bottom 50% of Nodes Account for Only {bottom_50_pct:.1f}% of Influence",
                        description=f"The lower half of nodes collectively hold just {bottom_50_pct:.1f}% of total influence, indicating a strong power law distribution. Many nodes have minimal individual impact.",
                        insight_type=InsightType.PATTERN,
                        confidence=0.85,
                        supporting_data={"bottom_50_pct": bottom_50_pct},
                        business_impact="Long tail nodes likely don't warrant individual attention. Consider batch strategies or deprioritization for resource efficiency.",
                    )
                )

        return insights

    def _label_propagation_insights(
        self, results: List[Dict[str, Any]]
    ) -> List[Insight]:
        """Generate insights for Label Propagation community detection."""
        insights = []

        if not results:
            return insights

        # Count communities/labels and sizes
        from collections import Counter
        labels = [r.get("label", 0) for r in results]
        label_counts = Counter(labels)
        
        num_communities = len(label_counts)
        total_nodes = len(results)
        
        insights.append(
            Insight(
                title=f"Discovered {num_communities} Communities in Network of {total_nodes} Nodes",
                description=f"Graph contains {num_communities} distinct communities via label propagation across {total_nodes} nodes. Average community size: {total_nodes/num_communities:.1f} nodes.",
                insight_type=InsightType.PATTERN,
                confidence=0.9,
                supporting_data={"community_count": num_communities, "total_nodes": total_nodes},
                business_impact="Target strategies per community segment. Develop community-specific engagement approaches.",
            )
        )
        
        # Analyze community size distribution
        if num_communities > 1:
            sizes = sorted(label_counts.values(), reverse=True)
            largest_community = sizes[0]
            largest_pct = (largest_community / total_nodes * 100) if total_nodes > 0 else 0
            
            insights.append(
                Insight(
                    title=f"Largest Community Contains {largest_pct:.1f}% of All Nodes",
                    description=f"The dominant community has {largest_community} nodes ({largest_pct:.1f}% of network). This {'indicates a core group with peripheral communities' if largest_pct > 50 else 'suggests relatively balanced community structure'}.",
                    insight_type=InsightType.PATTERN,
                    confidence=0.88,
                    supporting_data={"largest_size": largest_community, "largest_pct": largest_pct},
                    business_impact=f"{'Focus primary engagement on dominant community while nurturing smaller groups' if largest_pct > 50 else 'Balanced communities allow diverse segmentation strategies'}",
                )
            )

        return insights

    def _wcc_insights(self, results: List[Dict[str, Any]]) -> List[Insight]:
        """Generate insights for Weakly Connected Components."""
        insights = []

        if not results:
            return insights

        # Count components and analyze sizes
        from collections import Counter
        components = [r.get("component", 0) for r in results]
        component_counts = Counter(components)
        
        num_components = len(component_counts)
        total_nodes = len(results)
        
        insights.append(
            Insight(
                title=f"Found {num_components} Connected Components Across {total_nodes} Nodes",
                description=f"Graph has {num_components} separate weakly connected components. {'Network is highly fragmented' if num_components > total_nodes * 0.1 else 'Network has good overall connectivity' if num_components < 5 else 'Network has moderate fragmentation'}.",
                insight_type=InsightType.PATTERN,
                confidence=0.95,
                supporting_data={"component_count": num_components, "total_nodes": total_nodes},
                business_impact="Identify isolated clusters and network structure. Consider strategies to bridge disconnected components.",
            )
        )
        
        # Analyze component size distribution
        if num_components > 1:
            sizes = sorted(component_counts.values(), reverse=True)
            largest_component = sizes[0]
            largest_pct = (largest_component / total_nodes * 100) if total_nodes > 0 else 0
            singletons = sum(1 for size in sizes if size == 1)
            
            if singletons > 0:
                insights.append(
                    Insight(
                        title=f"{singletons} Isolated Nodes Detected ({singletons/total_nodes*100:.1f}% of Network)",
                        description=f"Found {singletons} completely isolated singleton nodes with no connections. Main component contains {largest_component} nodes ({largest_pct:.1f}%). Isolated nodes may indicate data quality issues or new additions.",
                        insight_type=InsightType.ANOMALY if singletons > total_nodes * 0.05 else InsightType.PATTERN,
                        confidence=0.92,
                        supporting_data={"singletons": singletons, "largest_component": largest_component},
                        business_impact="Investigate why nodes are isolated - likely onboarding issues or data quality problems. Connect isolated nodes to improve network health.",
                    )
                )

        return insights

    def _scc_insights(self, results: List[Dict[str, Any]]) -> List[Insight]:
        """Generate insights for Strongly Connected Components."""
        insights = []

        if not results:
            return insights

        # Count components and analyze sizes
        from collections import Counter
        components = [r.get("component", 0) for r in results]
        component_counts = Counter(components)
        
        num_components = len(component_counts)
        total_nodes = len(results)
        
        insights.append(
            Insight(
                title=f"Found {num_components} Strongly Connected Components with Bidirectional Paths",
                description=f"Graph has {num_components} strongly connected components where all nodes can reach each other via directed paths. Average component size: {total_nodes/num_components:.1f} nodes.",
                insight_type=InsightType.PATTERN,
                confidence=0.95,
                supporting_data={"scc_count": num_components, "total_nodes": total_nodes},
                business_impact="Understand reciprocal relationships and cycles. SCCs indicate mutual dependencies and feedback loops.",
            )
        )
        
        # Analyze SCC size distribution
        if num_components > 1:
            sizes = sorted(component_counts.values(), reverse=True)
            largest_scc = sizes[0]
            largest_pct = (largest_scc / total_nodes * 100) if total_nodes > 0 else 0
            singletons = sum(1 for size in sizes if size == 1)
            
            if largest_pct > 30:
                insights.append(
                    Insight(
                        title=f"Dominant SCC Contains {largest_pct:.1f}% of Nodes with Cyclic Dependencies",
                        description=f"The largest strongly connected component has {largest_scc} nodes ({largest_pct:.1f}%). This indicates a core group with strong mutual dependencies and potential feedback loops. {singletons} nodes have no bidirectional connections.",
                        insight_type=InsightType.PATTERN,
                        confidence=0.88,
                        supporting_data={"largest_scc": largest_scc, "largest_pct": largest_pct, "singletons": singletons},
                        business_impact="Core SCC represents tightly coupled system components. Changes propagate throughout this group. Consider resilience to cascading failures.",
                    )
                )

        return insights

    def _betweenness_insights(self, results: List[Dict[str, Any]]) -> List[Insight]:
        """Generate insights for Betweenness Centrality."""
        insights = []

        if not results:
            return insights

        # Extract betweenness scores
        betweenness_scores = [(r.get("_key"), r.get("betweenness", 0)) for r in results]
        betweenness_scores.sort(key=lambda x: x[1], reverse=True)
        
        if betweenness_scores:
            # Find highest betweenness nodes
            top_nodes = betweenness_scores[:5]
            top_score = top_nodes[0][1]
            
            # Calculate statistics
            all_scores = [score for _, score in betweenness_scores]
            avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
            median_score = all_scores[len(all_scores)//2] if all_scores else 0
            
            # Count critical bridges (significantly above average)
            critical_bridges = sum(1 for score in all_scores if score > avg_score * 3)

            insights.append(
                Insight(
                    title=f"{critical_bridges} Critical Bridge Nodes Control Network Flow",
                    description=f"Found {critical_bridges} nodes with exceptionally high betweenness centrality (>3x average). Top bridge node '{top_nodes[0][0]}' has betweenness of {top_score:.6f}, compared to median of {median_score:.6f}. These nodes are critical for connectivity between different network regions.",
                    insight_type=InsightType.KEY_FINDING,
                    confidence=0.9,
                    supporting_data={
                        "top_bridge_nodes": [n[0] for n in top_nodes],
                        "critical_count": critical_bridges,
                        "top_score": top_score,
                        "median_score": median_score
                    },
                    business_impact="These bridge nodes are organizational bottlenecks. Network flow depends on them. Ensure redundancy, document their role, and plan for succession. If they fail, connectivity breaks.",
                )
            )
            
            # Analyze concentration
            if len(all_scores) >= 10:
                top_5_betweenness = sum([score for _, score in top_nodes])
                total_betweenness = sum(all_scores)
                top_5_pct = (top_5_betweenness / total_betweenness * 100) if total_betweenness > 0 else 0
                
                if top_5_pct > 50:
                    insights.append(
                        Insight(
                            title=f"Top 5 Bridges Handle {top_5_pct:.1f}% of All Network Traffic",
                            description=f"Extreme concentration of betweenness centrality. Top 5 nodes account for {top_5_pct:.1f}% of all shortest paths. This creates single points of failure and potential bottlenecks.",
                            insight_type=InsightType.ANOMALY,
                            confidence=0.87,
                            supporting_data={"concentration_pct": top_5_pct},
                            business_impact="High risk of network disruption if key bridges fail. Diversify network structure or add redundant paths to reduce dependency on few critical nodes.",
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

    def _generate_insights_llm_with_reasoning(
        self,
        execution_result: ExecutionResult,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Insight]:
        """
        Generate insights using LLM with chain-of-thought reasoning.
        
        This variant asks the LLM to show its reasoning process before
        generating insights, improving quality and explainability.
        """
        try:
            job = execution_result.job
            results_sample = execution_result.results[:10]
            
            # Modified prompt with reasoning chain
            reasoning_prompt = self._create_reasoning_prompt(job, results_sample, context)
            
            # Get LLM analysis with reasoning
            response = self.llm_provider.generate(reasoning_prompt)
            
            # Parse response (includes reasoning + insights)
            insights = self._parse_llm_insights_with_reasoning(response.content)
            
            # Validate
            insights = self._validate_insights(insights)
            
            return insights
            
        except Exception as e:
            print(f"LLM insight generation with reasoning failed: {e}")
            return self._generate_insights_heuristic(execution_result)

    def _create_reasoning_prompt(
        self,
        job: AnalysisJob,
        results_sample: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """Create prompt that requests chain-of-thought reasoning."""
        
        # Get base prompt components
        base_prompt = self._create_insight_prompt(job, results_sample, context)
        
        # Add reasoning instructions
        reasoning_instructions = """

# Analysis Process

Before providing insights, first think through:

## Step 1: Data Observation
What do I see in the results?
- Key metrics and their values
- Distributions (concentrated or spread out?)
- Outliers or anomalies
- Patterns or trends

## Step 2: Statistical Analysis
- Calculate: percentages, ratios, concentrations
- Compare: top vs bottom, median vs mean
- Identify: thresholds, breakpoints, clusters

## Step 3: Business Context
- How does this relate to stated objectives?
- What decisions does this inform?
- What are the business implications?
- What actions should be taken?

## Step 4: Generate Insights
Now provide 3-5 insights following the format below.

---

# YOUR ANALYSIS

## Reasoning:
[Show your thinking from Steps 1-3 above]

## Insights:

- Title: [specific, quantified title]
  Description: [detailed analysis with numbers]
  Business Impact: [concrete, actionable impact]
  Confidence: [0.0-1.0]

- Title: [next insight...]
  ...
"""
        
        return base_prompt + reasoning_instructions
    
    def _parse_llm_insights_with_reasoning(self, llm_response: str) -> List[Insight]:
        """
        Parse LLM response that includes reasoning section.
        
        Extracts both the reasoning and the insights, storing reasoning
        for potential future use.
        """
        import re
        
        # Try to separate reasoning from insights
        insights_section = llm_response
        if "## Insights:" in llm_response:
            parts = llm_response.split("## Insights:", 1)
            if len(parts) == 2:
                insights_section = parts[1]
        elif "# Insights" in llm_response:
            parts = llm_response.split("# Insights", 1)
            if len(parts) == 2:
                insights_section = parts[1]
        
        # Use standard parsing on insights section
        return self._parse_llm_insights(insights_section)

    def _parse_llm_insights(self, llm_response: str) -> List[Insight]:
        """
        Parse LLM response into insight objects.
        
        Expected format from LLM:
        - Title: [title]
          Description: [description]
          Business Impact: [impact]
          Confidence: [0.0-1.0]
        """
        import re
        
        insights = []
        
        # Split response into individual insights
        # Look for "Title:" or numbered bullets
        lines = llm_response.strip().split('\n')
        
        current_insight = {}
        current_field = None
        
        for line in lines:
            line = line.strip()
            
            # Match "- Title:" or "Title:" or "1. Title:"
            if re.match(r'^[-\d.]*\s*Title:', line, re.IGNORECASE):
                # Save previous insight if exists
                if current_insight:
                    insights.append(self._create_insight_from_dict(current_insight))
                current_insight = {'title': re.sub(r'^[-\d.]*\s*Title:\s*', '', line, flags=re.IGNORECASE)}
                current_field = 'title'
                
            elif re.match(r'^\s*Description:', line, re.IGNORECASE):
                current_insight['description'] = re.sub(r'^\s*Description:\s*', '', line, flags=re.IGNORECASE)
                current_field = 'description'
                
            elif re.match(r'^\s*Business Impact:', line, re.IGNORECASE):
                current_insight['business_impact'] = re.sub(r'^\s*Business Impact:\s*', '', line, flags=re.IGNORECASE)
                current_field = 'business_impact'
                
            elif re.match(r'^\s*Confidence:', line, re.IGNORECASE):
                conf_str = re.sub(r'^\s*Confidence:\s*', '', line, flags=re.IGNORECASE)
                try:
                    current_insight['confidence'] = float(conf_str)
                except:
                    current_insight['confidence'] = 0.7
                current_field = 'confidence'
                
            elif line and current_field and not line.startswith('-'):
                # Continuation of current field
                if current_field in current_insight:
                    current_insight[current_field] += ' ' + line
        
        # Don't forget last insight
        if current_insight:
            insights.append(self._create_insight_from_dict(current_insight))
        
        # Fallback if parsing failed - at least preserve some content
        if not insights and llm_response.strip():
            insights.append(
                Insight(
                    title="Analysis Results",
                    description=llm_response[:1000],  # Keep more than 500 chars
                    insight_type=InsightType.KEY_FINDING,
                    confidence=0.6,  # Lower confidence for fallback
                    business_impact="Further analysis recommended",
                )
            )
        
        return insights
    
    def _create_insight_from_dict(self, insight_dict: Dict[str, Any]) -> Insight:
        """Create Insight object from parsed dictionary."""
        return Insight(
            title=insight_dict.get('title', 'Insight'),
            description=insight_dict.get('description', ''),
            insight_type=self._infer_insight_type(insight_dict.get('title', '')),
            confidence=insight_dict.get('confidence', 0.7),
            business_impact=insight_dict.get('business_impact', 'Requires further analysis'),
        )
    
    def _infer_insight_type(self, title: str) -> InsightType:
        """Infer insight type from title."""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['anomaly', 'unusual', 'unexpected', 'outlier']):
            return InsightType.ANOMALY
        elif any(word in title_lower for word in ['pattern', 'trend', 'distribution']):
            return InsightType.PATTERN
        elif any(word in title_lower for word in ['correlation', 'relationship', 'connected']):
            return InsightType.CORRELATION
        else:
            return InsightType.KEY_FINDING

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
