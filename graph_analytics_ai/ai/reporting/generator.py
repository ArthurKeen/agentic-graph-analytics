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
    ReportFormat
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
        use_llm_interpretation: bool = True
    ):
        """
        Initialize report generator.
        
        Args:
            llm_provider: LLM provider for interpretation (creates default if None)
            use_llm_interpretation: Whether to use LLM for insights
        """
        self.llm_provider = llm_provider or create_llm_provider()
        self.use_llm_interpretation = use_llm_interpretation
    
    def generate_report(
        self,
        execution_result: ExecutionResult,
        context: Optional[Dict[str, Any]] = None
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
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
        )
        
        # Extract metrics from results
        report.metrics = self._extract_metrics(execution_result)
        
        # Generate insights
        if self.use_llm_interpretation and execution_result.results:
            report.insights = self._generate_insights_llm(execution_result, context)
        else:
            report.insights = self._generate_insights_heuristic(execution_result)
        
        # Generate recommendations
        report.recommendations = self._generate_recommendations(report.insights, context)
        
        # Generate summary
        report.summary = self._generate_summary(report)
        
        # Create report sections
        report.sections = self._create_sections(report, execution_result)
        
        return report
    
    def generate_batch_report(
        self,
        execution_results: List[ExecutionResult],
        title: str = "Batch Analysis Report"
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
                "failed": sum(1 for r in execution_results if not r.success)
            }
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
        self,
        report: AnalysisReport,
        format: ReportFormat = ReportFormat.MARKDOWN
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
            "avg_score": None
        }
        
        # Try to extract common score fields
        score_fields = ['score', 'rank', 'centrality', 'pagerank', 'result', 'value']
        
        for field in score_fields:
            scores = [r.get(field) for r in results if field in r and isinstance(r.get(field), (int, float))]
            if scores:
                metrics["has_scores"] = True
                metrics["score_field"] = field
                metrics["min_score"] = min(scores)
                metrics["max_score"] = max(scores)
                metrics["avg_score"] = sum(scores) / len(scores)
                break
        
        return metrics
    
    def _generate_insights_heuristic(
        self,
        execution_result: ExecutionResult
    ) -> List[Insight]:
        """Generate insights using heuristics (no LLM)."""
        insights = []
        job = execution_result.job
        results = execution_result.results
        
        if not results:
            insights.append(Insight(
                title="No Results Generated",
                description="The analysis completed but produced no results. This may indicate the graph structure doesn't support this algorithm or no qualifying nodes were found.",
                insight_type=InsightType.KEY_FINDING,
                confidence=1.0,
                business_impact="Unable to derive insights without results"
            ))
            return insights
        
        # Algorithm-specific insights
        if job.algorithm == "pagerank":
            insights.extend(self._pagerank_insights(results))
        elif job.algorithm == "louvain":
            insights.extend(self._louvain_insights(results))
        elif job.algorithm == "shortest_path":
            insights.extend(self._path_insights(results))
        
        return insights
    
    def _generate_insights_llm(
        self,
        execution_result: ExecutionResult,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Insight]:
        """Generate insights using LLM interpretation."""
        try:
            # Prepare data for LLM
            job = execution_result.job
            results_sample = execution_result.results[:10]  # Top 10 for context
            
            prompt = self._create_insight_prompt(job, results_sample, context)
            
            # Get LLM interpretation
            response = self.llm_provider.generate(prompt)
            
            # Parse LLM response into insights
            insights = self._parse_llm_insights(response.content)
            
            return insights
        
        except Exception as e:
            # Fallback to heuristic insights
            print(f"LLM insight generation failed, using heuristics: {e}")
            return self._generate_insights_heuristic(execution_result)
    
    def _generate_recommendations(
        self,
        insights: List[Insight],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Recommendation]:
        """Generate recommendations from insights."""
        recommendations = []
        
        for insight in insights:
            # Create recommendation based on insight
            if insight.insight_type == InsightType.ANOMALY:
                recommendations.append(Recommendation(
                    title=f"Investigate: {insight.title}",
                    description=f"Further investigation needed: {insight.description}",
                    recommendation_type=RecommendationType.INVESTIGATION,
                    priority="high",
                    effort="medium",
                    expected_impact="Identify root cause and potential issues",
                    related_insights=[insight.title]
                ))
            
            elif insight.confidence >= 0.8:
                recommendations.append(Recommendation(
                    title=f"Action: {insight.title}",
                    description=f"Take action based on: {insight.description}",
                    recommendation_type=RecommendationType.ACTION,
                    priority="medium",
                    effort="low",
                    expected_impact=insight.business_impact or "Improve outcomes",
                    related_insights=[insight.title]
                ))
        
        return recommendations[:10]  # Limit to top 10
    
    def _generate_summary(self, report: AnalysisReport) -> str:
        """Generate executive summary."""
        lines = []
        
        lines.append(f"Analysis of {report.dataset_info.get('result_count', 0)} results using {report.algorithm} algorithm.")
        
        if report.insights:
            lines.append(f"Found {len(report.insights)} key insights.")
        
        if report.recommendations:
            high_priority = len([r for r in report.recommendations if r.priority in ('high', 'critical')])
            if high_priority > 0:
                lines.append(f"Generated {len(report.recommendations)} recommendations, {high_priority} high priority.")
        
        return " ".join(lines)
    
    def _generate_batch_summary(
        self,
        report: AnalysisReport,
        execution_results: List[ExecutionResult]
    ) -> str:
        """Generate summary for batch report."""
        success_count = report.dataset_info.get('successful', 0)
        total_count = report.dataset_info.get('total_analyses', 0)
        
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
                insights.append(Insight(
                    title="Most Influential Node Identified",
                    description=f"Node {top_node.get('_key', 'unknown')} has the highest PageRank score.",
                    insight_type=InsightType.KEY_FINDING,
                    confidence=0.95,
                    supporting_data={"top_node": top_node},
                    business_impact="Focus engagement efforts on this influential node"
                ))
        
        return insights
    
    def _louvain_insights(self, results: List[Dict[str, Any]]) -> List[Insight]:
        """Generate insights for Louvain community detection."""
        insights = []
        
        # Count communities
        communities = set(r.get('community', 0) for r in results)
        
        insights.append(Insight(
            title=f"Discovered {len(communities)} Communities",
            description=f"Graph contains {len(communities)} distinct communities.",
            insight_type=InsightType.PATTERN,
            confidence=0.9,
            supporting_data={"community_count": len(communities)},
            business_impact="Target strategies per community segment"
        ))
        
        return insights
    
    def _path_insights(self, results: List[Dict[str, Any]]) -> List[Insight]:
        """Generate insights for shortest path results."""
        insights = []
        
        if results:
            avg_path_length = sum(len(r.get('path', [])) for r in results) / len(results)
            
            insights.append(Insight(
                title=f"Average Path Length: {avg_path_length:.1f} hops",
                description=f"Average shortest path contains {avg_path_length:.1f} nodes.",
                insight_type=InsightType.KEY_FINDING,
                confidence=0.95,
                supporting_data={"avg_path_length": avg_path_length},
                business_impact="Optimize recommendation chains"
            ))
        
        return insights
    
    def _create_insight_prompt(
        self,
        job: AnalysisJob,
        results_sample: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Create prompt for LLM insight generation."""
        return f"""Analyze these {job.algorithm} results and provide business insights:

Algorithm: {job.algorithm}
Sample Results: {results_sample}

Provide 3-5 key insights in this format:
- Title: [brief title]
  Description: [detailed finding]
  Business Impact: [how this affects business]
  Confidence: [0.0-1.0]
"""
    
    def _parse_llm_insights(self, llm_response: str) -> List[Insight]:
        """Parse LLM response into insight objects."""
        # Simple parsing - could be enhanced
        insights = []
        
        # For now, create one insight from the response
        insights.append(Insight(
            title="LLM Analysis",
            description=llm_response[:500],  # Truncate if too long
            insight_type=InsightType.KEY_FINDING,
            confidence=0.85,
            business_impact="Derived from AI analysis of results"
        ))
        
        return insights
    
    def _create_sections(
        self,
        report: AnalysisReport,
        execution_result: ExecutionResult
    ) -> List[ReportSection]:
        """Create report sections."""
        sections = []
        
        # Overview section
        sections.append(ReportSection(
            title="1. Overview",
            content=self._create_overview_content(report, execution_result)
        ))
        
        # Key Metrics section
        sections.append(ReportSection(
            title="2. Key Metrics",
            content=self._create_metrics_content(report)
        ))
        
        # Insights section
        if report.insights:
            sections.append(ReportSection(
                title="3. Key Insights",
                content=self._create_insights_content(report.insights)
            ))
        
        # Recommendations section
        if report.recommendations:
            sections.append(ReportSection(
                title="4. Recommendations",
                content=self._create_recommendations_content(report.recommendations)
            ))
        
        # Top Results section
        if execution_result.results:
            sections.append(ReportSection(
                title="5. Top Results",
                content=self._create_top_results_content(execution_result.results[:20])
            ))
        
        return sections
    
    def _create_batch_sections(
        self,
        report: AnalysisReport,
        execution_results: List[ExecutionResult]
    ) -> List[ReportSection]:
        """Create sections for batch report."""
        sections = []
        
        # Summary section
        sections.append(ReportSection(
            title="1. Executive Summary",
            content=report.summary
        ))
        
        # Per-analysis sections
        for i, result in enumerate(execution_results, 1):
            if result.success:
                sections.append(ReportSection(
                    title=f"{i+1}. {result.job.template_name}",
                    content=f"Algorithm: {result.job.algorithm}, Runtime: {result.job.execution_time_seconds:.1f}s"
                ))
        
        return sections
    
    def _create_overview_content(
        self,
        report: AnalysisReport,
        execution_result: ExecutionResult
    ) -> str:
        """Create overview section content."""
        job = execution_result.job
        
        lines = [
            f"**Algorithm:** {job.algorithm}",
            f"**Job ID:** {job.job_id}",
            f"**Execution Time:** {job.execution_time_seconds:.2f}s" if job.execution_time_seconds else "**Execution Time:** N/A",
            f"**Results:** {job.result_count or len(execution_result.results)} records",
            "",
            report.summary
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
    
    def _create_recommendations_content(self, recommendations: List[Recommendation]) -> str:
        """Create recommendations section content."""
        lines = []
        
        # Group by priority
        critical = [r for r in recommendations if r.priority == 'critical']
        high = [r for r in recommendations if r.priority == 'high']
        medium = [r for r in recommendations if r.priority == 'medium']
        low = [r for r in recommendations if r.priority == 'low']
        
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
        
        score_fields = ['score', 'rank', 'centrality', 'pagerank', 'result', 'value']
        score_field = None
        
        for field in score_fields:
            if results and field in results[0]:
                score_field = field
                break
        
        for i, result in enumerate(results[:20], 1):
            key = result.get('_key', result.get('vertex', 'N/A'))
            score = result.get(score_field, 'N/A') if score_field else 'N/A'
            
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
        lines.append(f"*Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}*")
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
        text = markdown.replace('#', '').replace('**', '').replace('*', '')
        return text


def generate_report(
    execution_result: ExecutionResult,
    format: ReportFormat = ReportFormat.MARKDOWN
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

