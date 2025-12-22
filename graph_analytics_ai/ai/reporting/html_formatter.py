"""
HTML report formatter with embedded charts.

Generates complete HTML reports with interactive Plotly charts.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from .models import AnalysisReport, Insight, Recommendation
from .chart_generator import ChartGenerator, is_plotly_available


class HTMLReportFormatter:
    """
    Formats analysis reports as HTML with embedded charts.

    Creates beautiful, interactive HTML reports with:
    - Executive summary
    - Interactive Plotly charts
    - Key insights and recommendations
    - Detailed metrics

    Example:
        >>> from graph_analytics_ai.ai.reporting import HTMLReportFormatter
        >>>
        >>> formatter = HTMLReportFormatter()
        >>> html = formatter.format_report(report, charts)
        >>>
        >>> # Save to file
        >>> with open('report.html', 'w') as f:
        ...     f.write(html)
    """

    def __init__(self, theme: str = "modern"):
        """
        Initialize HTML formatter.

        Args:
            theme: Visual theme (modern, classic, dark)
        """
        self.theme = theme
        self.chart_generator = ChartGenerator() if is_plotly_available() else None

    def format_report(
        self,
        report: AnalysisReport,
        charts: Optional[Dict[str, str]] = None,
        include_raw_data: bool = False,
    ) -> str:
        """
        Format complete report as HTML.

        Args:
            report: Analysis report to format
            charts: Dictionary of chart HTML strings
            include_raw_data: Include raw data section

        Returns:
            Complete HTML document string
        """
        charts = charts or {}

        # Build HTML document
        html_parts = [
            self._generate_html_header(report.title),
            self._generate_executive_summary(report),
            self._generate_charts_section(charts),
            self._generate_insights_section(report.insights),
            self._generate_recommendations_section(report.recommendations),
            self._generate_metrics_section(report.metrics, report.dataset_info),
        ]

        if include_raw_data:
            html_parts.append(self._generate_raw_data_section(report))

        html_parts.append(self._generate_footer(report.generated_at))
        html_parts.append(self._generate_html_close())

        return "\n".join(html_parts)

    def _generate_html_header(self, title: str) -> str:
        """Generate HTML header with styling."""
        css = self._get_css_styles()

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
{css}
    </style>
</head>
<body>
    <div class="container">
        <header class="report-header">
            <h1>{title}</h1>
        </header>
"""

    def _generate_executive_summary(self, report: AnalysisReport) -> str:
        """Generate executive summary section."""
        html = ['        <section class="section executive-summary">']
        html.append("            <h2>Executive Summary</h2>")
        html.append(f'            <p class="summary-text">{report.summary}</p>')

        # Key stats
        result_count = report.dataset_info.get("result_count", 0)
        execution_time = report.dataset_info.get("execution_time", 0)

        html.append('            <div class="key-stats">')
        html.append('                <div class="stat-card">')
        html.append(
            f'                    <div class="stat-value">{report.algorithm.upper()}</div>'
        )
        html.append('                    <div class="stat-label">Algorithm</div>')
        html.append("                </div>")
        html.append('                <div class="stat-card">')
        html.append(
            f'                    <div class="stat-value">{result_count:,}</div>'
        )
        html.append('                    <div class="stat-label">Results</div>')
        html.append("                </div>")
        html.append('                <div class="stat-card">')
        html.append(
            f'                    <div class="stat-value">{execution_time:.1f}s</div>'
        )
        html.append('                    <div class="stat-label">Execution Time</div>')
        html.append("                </div>")
        html.append('                <div class="stat-card">')
        html.append(
            f'                    <div class="stat-value">{len(report.insights)}</div>'
        )
        html.append('                    <div class="stat-label">Key Insights</div>')
        html.append("                </div>")
        html.append("            </div>")
        html.append("        </section>")

        return "\n".join(html)

    def _generate_charts_section(self, charts: Dict[str, str]) -> str:
        """Generate charts section."""
        if not charts:
            return ""

        html = ['        <section class="section charts-section">']
        html.append("            <h2>Visualizations</h2>")

        for chart_name, chart_html in charts.items():
            html.append('            <div class="chart-container">')
            html.append(chart_html)
            html.append("            </div>")

        html.append("        </section>")
        return "\n".join(html)

    def _generate_insights_section(self, insights: List[Insight]) -> str:
        """Generate insights section."""
        if not insights:
            return ""

        html = ['        <section class="section insights-section">']
        html.append("            <h2>Key Insights</h2>")

        for i, insight in enumerate(insights, 1):
            confidence_class = self._get_confidence_class(insight.confidence)

            html.append('            <div class="insight-card">')
            html.append('                <div class="insight-header">')
            html.append(f"                    <h3>{i}. {insight.title}</h3>")
            html.append(
                f'                    <span class="confidence-badge {confidence_class}">'
            )
            html.append(f"                        Confidence: {insight.confidence:.0%}")
            html.append("                    </span>")
            html.append("                </div>")
            html.append(
                f'                <p class="insight-description">{insight.description}</p>'
            )

            if insight.business_impact:
                html.append('                <div class="business-impact">')
                html.append(
                    f"                    <strong>Business Impact:</strong> {insight.business_impact}"
                )
                html.append("                </div>")

            html.append("            </div>")

        html.append("        </section>")
        return "\n".join(html)

    def _generate_recommendations_section(
        self, recommendations: List[Recommendation]
    ) -> str:
        """Generate recommendations section."""
        if not recommendations:
            return ""

        html = ['        <section class="section recommendations-section">']
        html.append("            <h2>Recommendations</h2>")

        # Group by priority
        critical = [r for r in recommendations if r.priority in ["critical", "high"]]
        medium = [r for r in recommendations if r.priority == "medium"]
        low = [r for r in recommendations if r.priority == "low"]

        if critical:
            html.append("            <h3>High Priority</h3>")
            for rec in critical:
                html.append(self._format_recommendation(rec, "high"))

        if medium:
            html.append("            <h3>Medium Priority</h3>")
            for rec in medium[:5]:  # Limit to 5
                html.append(self._format_recommendation(rec, "medium"))

        if low:
            html.append("            <h3>Low Priority</h3>")
            for rec in low[:3]:  # Limit to 3
                html.append(self._format_recommendation(rec, "low"))

        html.append("        </section>")
        return "\n".join(html)

    def _format_recommendation(self, rec: Recommendation, priority_class: str) -> str:
        """Format a single recommendation."""
        html = [f'            <div class="recommendation-card {priority_class}">']
        html.append('                <div class="rec-header">')
        html.append(f"                    <h4>{rec.title}</h4>")
        html.append(
            f'                    <span class="priority-badge {priority_class}">{rec.priority.upper()}</span>'
        )
        html.append("                </div>")
        html.append(f"                <p>{rec.description}</p>")

        if rec.expected_impact:
            html.append('                <div class="rec-impact">')
            html.append(
                f"                    <strong>Expected Impact:</strong> {rec.expected_impact}"
            )
            html.append("                </div>")

        html.append('                <div class="rec-meta">')
        html.append(f"                    <span>Effort: {rec.effort}</span>")
        html.append("                </div>")
        html.append("            </div>")

        return "\n".join(html)

    def _generate_metrics_section(
        self, metrics: Dict[str, Any], dataset_info: Dict[str, Any]
    ) -> str:
        """Generate detailed metrics section."""
        html = ['        <section class="section metrics-section">']
        html.append("            <h2>Detailed Metrics</h2>")

        html.append('            <div class="metrics-grid">')

        # Dataset info
        if dataset_info:
            html.append('                <div class="metric-group">')
            html.append("                    <h3>Dataset Information</h3>")
            html.append('                    <table class="metrics-table">')
            for key, value in dataset_info.items():
                if value is not None:
                    html.append("                        <tr>")
                    html.append(
                        f"                            <td>{self._format_label(key)}</td>"
                    )
                    html.append(
                        f"                            <td>{self._format_value(value)}</td>"
                    )
                    html.append("                        </tr>")
            html.append("                    </table>")
            html.append("                </div>")

        # Algorithm metrics
        if metrics:
            html.append('                <div class="metric-group">')
            html.append("                    <h3>Algorithm Metrics</h3>")
            html.append('                    <table class="metrics-table">')
            for key, value in metrics.items():
                if value is not None and not isinstance(value, dict):
                    html.append("                        <tr>")
                    html.append(
                        f"                            <td>{self._format_label(key)}</td>"
                    )
                    html.append(
                        f"                            <td>{self._format_value(value)}</td>"
                    )
                    html.append("                        </tr>")
            html.append("                    </table>")
            html.append("                </div>")

        html.append("            </div>")
        html.append("        </section>")
        return "\n".join(html)

    def _generate_raw_data_section(self, report: AnalysisReport) -> str:
        """Generate raw data section (collapsible)."""
        import json

        html = ['        <section class="section raw-data-section">']
        html.append("            <h2>Raw Data</h2>")
        html.append("            <details>")
        html.append("                <summary>Show raw JSON data</summary>")
        html.append('                <pre class="raw-data">')
        html.append(json.dumps(report.to_dict(), indent=2))
        html.append("                </pre>")
        html.append("            </details>")
        html.append("        </section>")
        return "\n".join(html)

    def _generate_footer(self, generated_at: datetime) -> str:
        """Generate report footer."""
        return f"""        <footer class="report-footer">
            <p>Generated on {generated_at.strftime('%Y-%m-%d at %H:%M:%S')}</p>
            <p>Powered by Graph Analytics AI Platform</p>
        </footer>
    </div>
"""

    def _generate_html_close(self) -> str:
        """Close HTML tags."""
        return """</body>
</html>"""

    def _get_css_styles(self) -> str:
        """Get CSS styles for the report."""
        return """        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .report-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .report-header h1 {
            font-size: 2.5em;
            font-weight: 700;
            margin: 0;
        }
        
        .section {
            background: white;
            padding: 30px;
            margin-bottom: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        .section h2 {
            color: #667eea;
            font-size: 1.8em;
            margin-bottom: 20px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }
        
        .section h3 {
            color: #555;
            font-size: 1.3em;
            margin: 20px 0 15px 0;
        }
        
        .key-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .stat-value {
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .chart-container {
            margin: 30px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 8px;
        }
        
        .insight-card {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        
        .insight-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .insight-header h3 {
            margin: 0;
            color: #333;
            font-size: 1.3em;
        }
        
        .confidence-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }
        
        .confidence-badge.high {
            background: #28a745;
            color: white;
        }
        
        .confidence-badge.medium {
            background: #ffc107;
            color: #333;
        }
        
        .confidence-badge.low {
            background: #dc3545;
            color: white;
        }
        
        .business-impact {
            margin-top: 15px;
            padding: 15px;
            background: white;
            border-radius: 5px;
            border-left: 3px solid #28a745;
        }
        
        .recommendation-card {
            border-left: 4px solid #ffc107;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 5px;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        .recommendation-card.high {
            border-left-color: #dc3545;
        }
        
        .recommendation-card.medium {
            border-left-color: #ffc107;
        }
        
        .recommendation-card.low {
            border-left-color: #17a2b8;
        }
        
        .rec-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .rec-header h4 {
            margin: 0;
            color: #333;
        }
        
        .priority-badge {
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.75em;
            font-weight: 700;
            text-transform: uppercase;
        }
        
        .priority-badge.high {
            background: #dc3545;
            color: white;
        }
        
        .priority-badge.medium {
            background: #ffc107;
            color: #333;
        }
        
        .priority-badge.low {
            background: #17a2b8;
            color: white;
        }
        
        .rec-impact {
            margin: 15px 0;
            padding: 12px;
            background: #e7f3ff;
            border-radius: 5px;
        }
        
        .rec-meta {
            margin-top: 10px;
            font-size: 0.9em;
            color: #666;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
        }
        
        .metric-group h3 {
            color: #667eea;
            margin-bottom: 15px;
        }
        
        .metrics-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .metrics-table tr {
            border-bottom: 1px solid #e0e0e0;
        }
        
        .metrics-table tr:last-child {
            border-bottom: none;
        }
        
        .metrics-table td {
            padding: 10px 5px;
        }
        
        .metrics-table td:first-child {
            font-weight: 600;
            color: #555;
            width: 50%;
        }
        
        .metrics-table td:last-child {
            text-align: right;
            color: #333;
        }
        
        details {
            cursor: pointer;
        }
        
        summary {
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
            font-weight: 600;
            color: #667eea;
        }
        
        .raw-data {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 0.85em;
            margin-top: 10px;
        }
        
        .report-footer {
            text-align: center;
            padding: 30px;
            color: #666;
            border-top: 2px solid #e0e0e0;
            margin-top: 30px;
        }
        
        .report-footer p {
            margin: 5px 0;
        }
        
        @media print {
            body {
                background: white;
            }
            
            .section {
                box-shadow: none;
                page-break-inside: avoid;
            }
            
            .chart-container {
                page-break-inside: avoid;
            }
        }"""

    def _get_confidence_class(self, confidence: float) -> str:
        """Get CSS class based on confidence level."""
        if confidence >= 0.8:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        else:
            return "low"

    def _format_label(self, key: str) -> str:
        """Format metric label for display."""
        return key.replace("_", " ").title()

    def _format_value(self, value: Any) -> str:
        """Format metric value for display."""
        if isinstance(value, float):
            return f"{value:,.2f}"
        elif isinstance(value, int):
            return f"{value:,}"
        else:
            return str(value)
