"""
Chart generator for analysis reports.

Creates interactive visualizations using Plotly for different graph algorithms.
"""

from typing import List, Dict, Any
from collections import Counter
import logging

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logging.warning("Plotly not available. Install with: pip install plotly")


class ChartGenerator:
    """
    Generates interactive charts for graph analysis results.

    Uses Plotly to create professional, interactive visualizations
    tailored to each graph algorithm's output.

    Example:
        >>> from graph_analytics_ai.ai.reporting import ChartGenerator
        >>>
        >>> generator = ChartGenerator()
        >>> chart_html = generator.generate_wcc_charts(results)
        >>>
        >>> # Embed in report
        >>> with open('report.html', 'w') as f:
        ...     f.write(chart_html)
    """

    def __init__(self, theme: str = "plotly_white"):
        """
        Initialize chart generator.

        Args:
            theme: Plotly theme (plotly, plotly_white, plotly_dark, etc.)
        """
        if not PLOTLY_AVAILABLE:
            raise ImportError(
                "Plotly is required for chart generation. Install with: pip install plotly"
            )

        self.theme = theme
        self.logger = logging.getLogger(__name__)

    def generate_pagerank_charts(
        self, results: List[Dict[str, Any]], top_n: int = 20
    ) -> Dict[str, str]:
        """
        Generate charts for PageRank results.

        Creates:
        - Top influencers bar chart
        - Rank distribution histogram

        Args:
            results: List of PageRank results with 'rank' field
            top_n: Number of top nodes to show

        Returns:
            Dictionary with chart HTML strings
        """
        charts = {}

        # Extract ranks
        ranks = [r.get("rank", 0) for r in results if "rank" in r]
        if not ranks:
            self.logger.warning("No rank data found in results")
            return charts

        # Chart 1: Top Influencers
        top_results = sorted(results, key=lambda x: x.get("rank", 0), reverse=True)[
            :top_n
        ]

        fig1 = go.Figure()
        fig1.add_trace(
            go.Bar(
                x=[
                    self._format_node_id(r.get("_key", r.get("id", f"Node {i}")))
                    for i, r in enumerate(top_results)
                ],
                y=[r.get("rank", 0) for r in top_results],
                text=[f"{r.get('rank', 0):.6f}" for r in top_results],
                textposition="auto",
                marker_color="rgb(55, 83, 109)",
                hovertemplate="<b>%{x}</b><br>PageRank: %{y:.6f}<extra></extra>",
            )
        )

        fig1.update_layout(
            title=f"Top {top_n} Most Influential Nodes",
            xaxis_title="Node",
            yaxis_title="PageRank Score",
            template=self.theme,
            height=500,
            showlegend=False,
        )

        fig1.update_xaxes(tickangle=45)
        charts["top_influencers"] = fig1.to_html(
            include_plotlyjs="cdn", div_id="pagerank-top"
        )

        # Chart 2: Distribution
        fig2 = go.Figure()
        fig2.add_trace(
            go.Histogram(
                x=ranks,
                nbinsx=50,
                marker_color="rgb(26, 118, 255)",
                hovertemplate="Rank Range: %{x}<br>Count: %{y}<extra></extra>",
            )
        )

        fig2.update_layout(
            title="PageRank Distribution",
            xaxis_title="PageRank Score",
            yaxis_title="Number of Nodes",
            template=self.theme,
            height=400,
            showlegend=False,
        )

        # Use log scale if distribution is very skewed
        if len(ranks) > 100:
            fig2.update_xaxes(type="log", title="PageRank Score (log scale)")

        charts["distribution"] = fig2.to_html(
            include_plotlyjs=False, div_id="pagerank-dist"
        )

        # Chart 3: Cumulative influence
        sorted_ranks = sorted(ranks, reverse=True)
        cumulative = []
        total = sum(sorted_ranks)
        cum_sum = 0
        for rank in sorted_ranks:
            cum_sum += rank
            cumulative.append((cum_sum / total) * 100)

        fig3 = go.Figure()
        fig3.add_trace(
            go.Scatter(
                x=list(range(1, len(cumulative) + 1)),
                y=cumulative,
                mode="lines",
                line=dict(color="rgb(255, 127, 14)", width=2),
                fill="tozeroy",
                hovertemplate="Top %{x} nodes<br>Control %{y:.1f}% of influence<extra></extra>",
            )
        )

        # Add reference lines
        if len(cumulative) >= 10:
            cumulative[9] if len(cumulative) > 9 else cumulative[-1]
            fig3.add_hline(
                y=80,
                line_dash="dash",
                line_color="red",
                annotation_text="80% threshold",
                annotation_position="right",
            )

        fig3.update_layout(
            title="Cumulative Influence Distribution",
            xaxis_title="Number of Top Nodes",
            yaxis_title="Cumulative % of Total Influence",
            template=self.theme,
            height=400,
            showlegend=False,
        )

        charts["cumulative"] = fig3.to_html(
            include_plotlyjs=False, div_id="pagerank-cumulative"
        )

        return charts

    def generate_wcc_charts(
        self, results: List[Dict[str, Any]], top_n: int = 10
    ) -> Dict[str, str]:
        """
        Generate charts for Weakly Connected Components results.

        Creates:
        - Component size distribution
        - Top N largest components
        - Connectivity overview (pie chart)

        Args:
            results: List of WCC results with 'component' field
            top_n: Number of top components to show

        Returns:
            Dictionary with chart HTML strings
        """
        charts = {}

        # Calculate component sizes
        components = [r.get("component", "") for r in results if "component" in r]
        if not components:
            self.logger.warning("No component data found in results")
            return charts

        component_sizes = Counter(components)
        sorted_components = component_sizes.most_common()

        # Chart 1: Top N Largest Components
        top_components = sorted_components[:top_n]

        fig1 = go.Figure()
        fig1.add_trace(
            go.Bar(
                x=[f"Component {i+1}" for i in range(len(top_components))],
                y=[size for _, size in top_components],
                text=[f"{size:,}" for _, size in top_components],
                textposition="auto",
                marker_color="steelblue",
                hovertemplate="<b>%{x}</b><br>Size: %{y:,} nodes<br>ID: "
                + "<br>".join(
                    [f"{self._format_node_id(comp)}" for comp, _ in top_components]
                )
                + "<extra></extra>",
                customdata=[self._format_node_id(comp) for comp, _ in top_components],
            )
        )

        fig1.update_layout(
            title=f"Top {top_n} Largest Components",
            xaxis_title="Component Rank",
            yaxis_title="Number of Nodes",
            template=self.theme,
            height=500,
            showlegend=False,
        )

        charts["top_components"] = fig1.to_html(
            include_plotlyjs="cdn", div_id="wcc-top"
        )

        # Chart 2: Size Distribution (histogram)
        sizes = [size for _, size in sorted_components]

        fig2 = go.Figure()
        fig2.add_trace(
            go.Histogram(
                x=sizes,
                nbinsx=min(50, len(set(sizes))),
                marker_color="rgb(26, 118, 255)",
                hovertemplate="Component Size: %{x}<br>Count: %{y}<extra></extra>",
            )
        )

        fig2.update_layout(
            title="Component Size Distribution",
            xaxis_title="Component Size (nodes)",
            yaxis_title="Number of Components",
            template=self.theme,
            height=400,
            showlegend=False,
        )

        # Use log scale for both axes if highly skewed
        if (
            len(sorted_components) > 100
            and sorted_components[0][1] > sorted_components[-1][1] * 100
        ):
            fig2.update_xaxes(type="log")
            fig2.update_yaxes(type="log")

        charts["size_distribution"] = fig2.to_html(
            include_plotlyjs=False, div_id="wcc-dist"
        )

        # Chart 3: Connectivity Overview (pie/donut chart)
        sorted_components[0][1] if sorted_components else 0
        len(results)

        # Group smaller components
        if len(sorted_components) > 5:
            top_5_sizes = [size for _, size in sorted_components[:5]]
            top_5_labels = [
                f"Component {i+1}<br>({size:,} nodes)"
                for i, (_, size) in enumerate(sorted_components[:5])
            ]

            other_size = sum(size for _, size in sorted_components[5:])
            if other_size > 0:
                top_5_sizes.append(other_size)
                top_5_labels.append(
                    f"Other {len(sorted_components) - 5}<br>Components<br>({other_size:,} nodes)"
                )
        else:
            top_5_sizes = [size for _, size in sorted_components]
            top_5_labels = [
                f"Component {i+1}<br>({size:,} nodes)"
                for i, (_, size) in enumerate(sorted_components)
            ]

        fig3 = go.Figure()
        fig3.add_trace(
            go.Pie(
                labels=top_5_labels,
                values=top_5_sizes,
                hole=0.3,
                marker=dict(
                    colors=[
                        "rgb(55, 83, 109)",
                        "rgb(26, 118, 255)",
                        "rgb(255, 127, 14)",
                        "rgb(44, 160, 44)",
                        "rgb(214, 39, 40)",
                        "rgb(148, 103, 189)",
                    ]
                ),
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>%{value:,} nodes<br>%{percent}<extra></extra>",
            )
        )

        fig3.update_layout(
            title="Network Connectivity Overview",
            template=self.theme,
            height=500,
            showlegend=True,
            annotations=[
                dict(
                    text=f"{len(sorted_components)}<br>Components",
                    x=0.5,
                    y=0.5,
                    font_size=20,
                    showarrow=False,
                )
            ],
        )

        charts["connectivity"] = fig3.to_html(
            include_plotlyjs=False, div_id="wcc-connectivity"
        )

        return charts

    def generate_betweenness_charts(
        self, results: List[Dict[str, Any]], top_n: int = 20
    ) -> Dict[str, str]:
        """
        Generate charts for Betweenness Centrality results.

        Creates:
        - Top bridge nodes bar chart
        - Betweenness distribution

        Args:
            results: List of betweenness results with 'centrality' or 'betweenness' field
            top_n: Number of top nodes to show

        Returns:
            Dictionary with chart HTML strings
        """
        charts = {}

        # Extract betweenness values (try both field names)
        betweenness_values = []
        for r in results:
            value = r.get("centrality", r.get("betweenness", 0))
            betweenness_values.append(value)

        if not betweenness_values or all(v == 0 for v in betweenness_values):
            self.logger.warning("No betweenness data found in results")
            return charts

        # Chart 1: Top Bridge Nodes
        # Create list with original index for sorting
        results_with_values = [
            (r, r.get("centrality", r.get("betweenness", 0))) for r in results
        ]
        top_results = sorted(results_with_values, key=lambda x: x[1], reverse=True)[
            :top_n
        ]

        fig1 = go.Figure()
        fig1.add_trace(
            go.Bar(
                x=[
                    self._format_node_id(r.get("_key", r.get("id", f"Node {i}")))
                    for i, (r, _) in enumerate(top_results)
                ],
                y=[value for _, value in top_results],
                text=[f"{value:.4f}" for _, value in top_results],
                textposition="auto",
                marker_color="rgb(214, 39, 40)",
                hovertemplate="<b>%{x}</b><br>Betweenness: %{y:.6f}<extra></extra>",
            )
        )

        fig1.update_layout(
            title=f"Top {top_n} Bridge Nodes (Critical for Network Flow)",
            xaxis_title="Node",
            yaxis_title="Betweenness Centrality",
            template=self.theme,
            height=500,
            showlegend=False,
        )

        fig1.update_xaxes(tickangle=45)
        charts["top_bridges"] = fig1.to_html(
            include_plotlyjs="cdn", div_id="betweenness-top"
        )

        # Chart 2: Distribution
        fig2 = go.Figure()
        fig2.add_trace(
            go.Histogram(
                x=betweenness_values,
                nbinsx=50,
                marker_color="rgb(255, 127, 14)",
                hovertemplate="Betweenness Range: %{x}<br>Count: %{y}<extra></extra>",
            )
        )

        fig2.update_layout(
            title="Betweenness Centrality Distribution",
            xaxis_title="Betweenness Score",
            yaxis_title="Number of Nodes",
            template=self.theme,
            height=400,
            showlegend=False,
        )

        # Use log scale if very skewed
        if len(betweenness_values) > 100:
            non_zero_values = [v for v in betweenness_values if v > 0]
            if non_zero_values:
                fig2.update_xaxes(type="log")

        charts["distribution"] = fig2.to_html(
            include_plotlyjs=False, div_id="betweenness-dist"
        )

        return charts

    def generate_label_propagation_charts(
        self, results: List[Dict[str, Any]], top_n: int = 10
    ) -> Dict[str, str]:
        """
        Generate charts for Label Propagation (community detection) results.

        Creates:
        - Community size distribution
        - Top N communities

        Args:
            results: List of results with 'community' field
            top_n: Number of top communities to show

        Returns:
            Dictionary with chart HTML strings
        """
        charts = {}

        # Calculate community sizes
        communities = [r.get("community", "") for r in results if "community" in r]
        if not communities:
            self.logger.warning("No community data found in results")
            return charts

        community_sizes = Counter(communities)
        sorted_communities = community_sizes.most_common()

        # Chart 1: Top N Communities
        top_communities = sorted_communities[:top_n]

        fig1 = go.Figure()
        fig1.add_trace(
            go.Bar(
                x=[f"Community {i+1}" for i in range(len(top_communities))],
                y=[size for _, size in top_communities],
                text=[f"{size:,}" for _, size in top_communities],
                textposition="auto",
                marker_color="rgb(44, 160, 44)",
                hovertemplate="<b>%{x}</b><br>Size: %{y:,} members<extra></extra>",
            )
        )

        fig1.update_layout(
            title=f"Top {top_n} Largest Communities",
            xaxis_title="Community Rank",
            yaxis_title="Number of Members",
            template=self.theme,
            height=500,
            showlegend=False,
        )

        charts["top_communities"] = fig1.to_html(
            include_plotlyjs="cdn", div_id="community-top"
        )

        # Chart 2: Size Distribution
        sizes = [size for _, size in sorted_communities]

        fig2 = go.Figure()
        fig2.add_trace(
            go.Histogram(
                x=sizes,
                nbinsx=min(50, len(set(sizes))),
                marker_color="rgb(148, 103, 189)",
                hovertemplate="Community Size: %{x}<br>Count: %{y}<extra></extra>",
            )
        )

        fig2.update_layout(
            title="Community Size Distribution",
            xaxis_title="Community Size (members)",
            yaxis_title="Number of Communities",
            template=self.theme,
            height=400,
            showlegend=False,
        )

        charts["size_distribution"] = fig2.to_html(
            include_plotlyjs=False, div_id="community-dist"
        )

        return charts

    def generate_scc_charts(
        self, results: List[Dict[str, Any]], top_n: int = 10
    ) -> Dict[str, str]:
        """
        Generate charts for Strongly Connected Components results.

        Creates:
        - SCC size distribution
        - Top N largest SCCs

        Args:
            results: List of SCC results with 'component' field
            top_n: Number of top SCCs to show

        Returns:
            Dictionary with chart HTML strings
        """
        # SCC uses same visualization as WCC but with different context
        return self.generate_wcc_charts(results, top_n)

    def generate_combined_summary(
        self, algorithm: str, total_nodes: int, key_metrics: Dict[str, Any]
    ) -> str:
        """
        Generate a summary metrics card/chart.

        Args:
            algorithm: Algorithm name
            total_nodes: Total nodes processed
            key_metrics: Dictionary of key metrics

        Returns:
            HTML string with metrics card
        """
        fig = go.Figure()

        # Create indicator/gauge charts for key metrics
        metrics_list = []
        for metric_name, metric_value in key_metrics.items():
            if isinstance(metric_value, (int, float)):
                metrics_list.append((metric_name, metric_value))

        if not metrics_list:
            return ""

        # Create subplots for each metric
        fig = make_subplots(
            rows=1,
            cols=len(metrics_list),
            subplot_titles=[name for name, _ in metrics_list],
            specs=[[{"type": "indicator"}] * len(metrics_list)],
        )

        for i, (name, value) in enumerate(metrics_list, 1):
            fig.add_trace(
                go.Indicator(
                    mode="number",
                    value=value,
                    title={"text": name},
                    number={"font": {"size": 40}},
                ),
                row=1,
                col=i,
            )

        fig.update_layout(height=200, template=self.theme, showlegend=False)

        return fig.to_html(include_plotlyjs=False, div_id="metrics-summary")

    def _format_node_id(self, node_id: str, max_length: int = 20) -> str:
        """
        Format node ID for display (truncate if too long).

        Args:
            node_id: Node identifier
            max_length: Maximum length before truncation

        Returns:
            Formatted node ID
        """
        if not isinstance(node_id, str):
            node_id = str(node_id)

        if len(node_id) <= max_length:
            return node_id

        # Truncate and add ellipsis
        return node_id[: max_length - 3] + "..."


def is_plotly_available() -> bool:
    """Check if Plotly is available."""
    return PLOTLY_AVAILABLE
