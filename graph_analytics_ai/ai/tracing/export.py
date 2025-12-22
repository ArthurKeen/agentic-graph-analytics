"""
Trace export and visualization generators.

Exports workflow traces to various formats including JSON, HTML, and SVG.
"""

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from . import WorkflowTrace


class TraceExporter:
    """
    Exports workflow traces to various formats.

    Supports JSON, HTML timeline, SVG diagrams, and markdown reports.
    """

    def __init__(self, trace: WorkflowTrace):
        """
        Initialize exporter.

        Args:
            trace: Workflow trace to export
        """
        self.trace = trace

    def export_json(self, output_path: str, pretty: bool = True) -> None:
        """
        Export trace as JSON.

        Args:
            output_path: Output file path
            pretty: Whether to pretty-print JSON
        """
        data = self.trace.to_dict()

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            if pretty:
                json.dump(data, f, indent=2, default=str)
            else:
                json.dump(data, f, default=str)

        print(f"📊 Trace exported to JSON: {output_path}")

    def export_timeline_html(self, output_path: str) -> None:
        """
        Export interactive HTML timeline.

        Args:
            output_path: Output file path
        """
        html = self._generate_timeline_html()

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(html)

        print(f"📊 Timeline exported to HTML: {output_path}")

    def export_agent_diagram_svg(self, output_path: str) -> None:
        """
        Export agent interaction diagram as SVG.

        Args:
            output_path: Output file path
        """
        svg = self._generate_agent_diagram_svg()

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(svg)

        print(f"📊 Agent diagram exported to SVG: {output_path}")

    def export_markdown_report(self, output_path: str) -> None:
        """
        Export trace as markdown report.

        Args:
            output_path: Output file path
        """
        md = self._generate_markdown_report()

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(md)

        print(f"📊 Trace report exported to Markdown: {output_path}")

    def export_all(self, output_dir: str) -> None:
        """
        Export trace in all formats.

        Args:
            output_dir: Output directory
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        base_name = f"trace_{self.trace.trace_id}"

        self.export_json(str(output_path / f"{base_name}.json"))
        self.export_timeline_html(str(output_path / f"{base_name}_timeline.html"))
        self.export_agent_diagram_svg(str(output_path / f"{base_name}_agents.svg"))
        self.export_markdown_report(str(output_path / f"{base_name}_report.md"))

        print(f"\n✓ All trace formats exported to: {output_dir}")

    def _generate_timeline_html(self) -> str:
        """Generate interactive HTML timeline."""
        timeline = self.trace.get_timeline()
        perf = self.trace.performance.to_dict() if self.trace.performance else {}

        # Generate HTML with embedded CSS and JavaScript
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Workflow Trace Timeline - {self.trace.trace_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .header {{
            padding: 30px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .header h1 {{
            font-size: 24px;
            color: #333;
            margin-bottom: 10px;
        }}
        
        .header .meta {{
            color: #666;
            font-size: 14px;
        }}
        
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f9f9f9;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .metric {{
            background: white;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #4CAF50;
        }}
        
        .metric.warning {{
            border-left-color: #FF9800;
        }}
        
        .metric.error {{
            border-left-color: #F44336;
        }}
        
        .metric-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }}
        
        .metric-value {{
            font-size: 28px;
            font-weight: 600;
            color: #333;
        }}
        
        .metric-unit {{
            font-size: 14px;
            color: #999;
            margin-left: 4px;
        }}
        
        .timeline {{
            padding: 30px;
        }}
        
        .timeline-header {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #333;
        }}
        
        .timeline-event {{
            display: flex;
            margin-bottom: 20px;
            padding-left: 30px;
            position: relative;
        }}
        
        .timeline-event::before {{
            content: '';
            position: absolute;
            left: 7px;
            top: 0;
            bottom: -20px;
            width: 2px;
            background: #e0e0e0;
        }}
        
        .timeline-event:last-child::before {{
            display: none;
        }}
        
        .timeline-dot {{
            position: absolute;
            left: 0;
            top: 6px;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: #4CAF50;
            border: 3px solid white;
            box-shadow: 0 0 0 2px #4CAF50;
        }}
        
        .timeline-dot.agent {{
            background: #2196F3;
            box-shadow: 0 0 0 2px #2196F3;
        }}
        
        .timeline-dot.error {{
            background: #F44336;
            box-shadow: 0 0 0 2px #F44336;
        }}
        
        .timeline-content {{
            flex: 1;
            background: #f9f9f9;
            padding: 15px;
            border-radius: 6px;
        }}
        
        .timeline-time {{
            font-size: 12px;
            color: #999;
            margin-bottom: 5px;
        }}
        
        .timeline-title {{
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }}
        
        .timeline-summary {{
            font-size: 14px;
            color: #666;
        }}
        
        .timeline-duration {{
            display: inline-block;
            margin-left: 10px;
            padding: 2px 8px;
            background: #4CAF50;
            color: white;
            border-radius: 3px;
            font-size: 11px;
        }}
        
        .filter-bar {{
            padding: 20px 30px;
            background: #f9f9f9;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        
        .filter-btn {{
            padding: 8px 16px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }}
        
        .filter-btn:hover {{
            background: #f5f5f5;
        }}
        
        .filter-btn.active {{
            background: #2196F3;
            color: white;
            border-color: #2196F3;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Workflow Trace Timeline</h1>
            <div class="meta">
                <strong>Trace ID:</strong> {self.trace.trace_id} | 
                <strong>Workflow ID:</strong> {self.trace.workflow_id} | 
                <strong>Events:</strong> {len(self.trace.events)}
            </div>
        </div>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">Total Time</div>
                <div class="metric-value">
                    {perf.get('total_time_seconds', 0):.1f}
                    <span class="metric-unit">sec</span>
                </div>
            </div>
            
            <div class="metric">
                <div class="metric-label">LLM Calls</div>
                <div class="metric-value">
                    {perf.get('total_llm_calls', 0)}
                    <span class="metric-unit">calls</span>
                </div>
            </div>
            
            <div class="metric">
                <div class="metric-label">Total Tokens</div>
                <div class="metric-value">
                    {perf.get('total_llm_tokens', 0):,}
                    <span class="metric-unit">tokens</span>
                </div>
            </div>
            
            <div class="metric">
                <div class="metric-label">Est. Cost</div>
                <div class="metric-value">
                    ${perf.get('estimated_cost_usd', 0):.4f}
                    <span class="metric-unit">USD</span>
                </div>
            </div>
            
            <div class="metric {('error' if perf.get('total_errors', 0) > 0 else '')}">
                <div class="metric-label">Errors</div>
                <div class="metric-value">
                    {perf.get('total_errors', 0)}
                    <span class="metric-unit">errors</span>
                </div>
            </div>
            
            <div class="metric">
                <div class="metric-label">Messages</div>
                <div class="metric-value">
                    {perf.get('total_messages', 0)}
                    <span class="metric-unit">msgs</span>
                </div>
            </div>
        </div>
        
        <div class="filter-bar">
            <button class="filter-btn active" onclick="filterEvents('all')">All Events</button>
            <button class="filter-btn" onclick="filterEvents('agent')">Agent Events</button>
            <button class="filter-btn" onclick="filterEvents('step')">Workflow Steps</button>
            <button class="filter-btn" onclick="filterEvents('error')">Errors Only</button>
        </div>
        
        <div class="timeline">
            <div class="timeline-header">Event Timeline</div>
"""

        for event in timeline:
            event_type = event["event"].replace("_", " ").title()
            agent = event.get("agent", "System")
            summary = event.get("summary", "")
            duration = event.get("duration_ms", 0)
            timestamp = event["timestamp"]

            # Determine dot class
            dot_class = "timeline-dot"
            if "error" in event["event"].lower():
                dot_class += " error"
            elif "agent" in event["event"].lower():
                dot_class += " agent"

            # Determine event class for filtering
            event_class = []
            if "agent" in event["event"].lower():
                event_class.append("agent-event")
            if "step" in event["event"].lower():
                event_class.append("step-event")
            if "error" in event["event"].lower():
                event_class.append("error-event")

            html += f"""
            <div class="timeline-event {' '.join(event_class)}">
                <div class="{dot_class}"></div>
                <div class="timeline-content">
                    <div class="timeline-time">{timestamp}</div>
                    <div class="timeline-title">
                        {event_type} {f'({agent})' if agent != 'System' else ''}
                        {f'<span class="timeline-duration">{duration:.0f}ms</span>' if duration else ''}
                    </div>
                    <div class="timeline-summary">{summary}</div>
                </div>
            </div>
"""

        html += """
        </div>
    </div>
    
    <script>
        function filterEvents(filter) {
            // Update button states
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Filter events
            const events = document.querySelectorAll('.timeline-event');
            events.forEach(event => {
                if (filter === 'all') {
                    event.style.display = 'flex';
                } else if (filter === 'agent') {
                    event.style.display = event.classList.contains('agent-event') ? 'flex' : 'none';
                } else if (filter === 'step') {
                    event.style.display = event.classList.contains('step-event') ? 'flex' : 'none';
                } else if (filter === 'error') {
                    event.style.display = event.classList.contains('error-event') ? 'flex' : 'none';
                }
            });
        }
    </script>
</body>
</html>
"""

        return html

    def _generate_agent_diagram_svg(self) -> str:
        """Generate SVG diagram of agent interactions."""
        interactions = self.trace.get_agent_interactions()

        # Get unique agents
        agents = set()
        for interaction in interactions:
            agents.add(interaction["from_agent"])
            agents.add(interaction["to_agent"])

        agents = sorted(list(agents))
        agent_count = len(agents)

        # SVG dimensions
        width = 800
        height = 400
        agent_y = 80
        agent_spacing = width / (agent_count + 1)

        svg = f"""<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
    <style>
        .agent-box {{ fill: #2196F3; stroke: #1976D2; stroke-width: 2; }}
        .agent-text {{ fill: white; font-family: Arial, sans-serif; font-size: 12px; text-anchor: middle; }}
        .message-line {{ stroke: #4CAF50; stroke-width: 2; fill: none; opacity: 0.6; }}
        .message-arrow {{ fill: #4CAF50; }}
        .title {{ font-family: Arial, sans-serif; font-size: 16px; font-weight: bold; text-anchor: middle; }}
    </style>
    
    <text x="{width/2}" y="30" class="title">Agent Interaction Diagram</text>
"""

        # Draw agents
        agent_positions = {}
        for i, agent in enumerate(agents):
            x = (i + 1) * agent_spacing
            agent_positions[agent] = x

            svg += f"""
    <rect x="{x-50}" y="{agent_y}" width="100" height="40" rx="5" class="agent-box"/>
    <text x="{x}" y="{agent_y + 25}" class="agent-text">{agent[:15]}</text>
"""

        # Draw interactions
        message_y_start = agent_y + 60
        message_y_spacing = 15

        for i, interaction in enumerate(
            interactions[:20]
        ):  # Limit to first 20 for readability
            from_agent = interaction["from_agent"]
            to_agent = interaction["to_agent"]

            if from_agent not in agent_positions or to_agent not in agent_positions:
                continue

            x1 = agent_positions[from_agent]
            x2 = agent_positions[to_agent]
            y = message_y_start + (i * message_y_spacing)

            # Draw curved line
            control_y = y + 20
            svg += f"""
    <path d="M {x1} {y} Q {(x1+x2)/2} {control_y} {x2} {y + 5}" class="message-line"/>
    <polygon points="{x2-5},{y+5} {x2},{y+8} {x2-5},{y+11}" class="message-arrow"/>
"""

        svg += """
</svg>
"""

        return svg

    def _generate_markdown_report(self) -> str:
        """Generate markdown trace report."""
        perf = self.trace.performance.to_dict() if self.trace.performance else {}
        timeline = self.trace.get_timeline()

        md = f"""# Workflow Trace Report

**Trace ID:** `{self.trace.trace_id}`  
**Workflow ID:** `{self.trace.workflow_id}`  
**Generated:** {datetime.utcnow().isoformat()}  

---

## Performance Summary

| Metric | Value |
|--------|-------|
| **Total Time** | {perf.get('total_time_seconds', 0):.2f} seconds |
| **Steps Completed** | {perf.get('steps_completed', 0)} |
| **Avg Time/Step** | {perf.get('avg_time_per_step_ms', 0):.0f} ms |
| **LLM Calls** | {perf.get('total_llm_calls', 0)} |
| **LLM Time** | {perf.get('total_llm_time_ms', 0):.0f} ms |
| **Total Tokens** | {perf.get('total_llm_tokens', 0):,} |
| **Estimated Cost** | ${perf.get('estimated_cost_usd', 0):.4f} USD |
| **Messages Exchanged** | {perf.get('total_messages', 0)} |
| **Errors** | {perf.get('total_errors', 0)} |

---

## Slowest Agents

"""

        for i, agent in enumerate(perf.get("slowest_agents", []), 1):
            md += f"{i}. **{agent['agent']}**: {agent['total_time_ms']:.0f}ms ({agent['invocations']} invocations)\n"

        md += "\n---\n\n## Top LLM Consumers\n\n"

        for i, agent in enumerate(perf.get("top_llm_consumers", []), 1):
            md += f"{i}. **{agent['agent']}**: {agent['total_tokens']:,} tokens ({agent['llm_calls']} calls)\n"

        md += "\n---\n\n## Event Timeline\n\n"

        for event in timeline:
            timestamp = event["timestamp"].split("T")[1][:12]  # Just time
            summary = event.get("summary", "")
            duration = event.get("duration_ms", 0)

            md += f"**{timestamp}** - {summary}"
            if duration:
                md += f" `({duration:.0f}ms)`"
            md += "\n\n"

        md += "\n---\n\n## Agent Interactions\n\n"

        interactions = self.trace.get_agent_interactions()
        for interaction in interactions[:30]:  # Limit to first 30
            md += f"- `{interaction['from_agent']}` → `{interaction['to_agent']}` ({interaction['message_type']})\n"

        if len(interactions) > 30:
            md += f"\n_... and {len(interactions) - 30} more interactions_\n"

        md += "\n---\n\n## Detailed Metrics by Agent\n\n"

        agent_metrics = perf.get("agent_metrics", {})
        for agent_name, metrics in agent_metrics.items():
            md += f"### {agent_name}\n\n"
            md += f"- **Invocations:** {metrics['invocation_count']}\n"
            md += f"- **Total Time:** {metrics['total_time_ms']:.2f}ms\n"
            md += f"- **Avg Time:** {metrics['avg_time_ms']:.2f}ms\n"
            md += f"- **LLM Calls:** {metrics['llm_calls']}\n"
            md += f"- **LLM Time:** {metrics['llm_time_ms']:.2f}ms ({metrics['llm_time_percent']:.1f}%)\n"
            md += f"- **Total Tokens:** {metrics['total_tokens']:,}\n"
            md += f"- **Tool Calls:** {metrics['tool_calls']}\n"
            md += f"- **Messages Sent:** {metrics['messages_sent']}\n"
            md += f"- **Messages Received:** {metrics['messages_received']}\n"
            md += f"- **Errors:** {metrics['errors']}\n\n"

        return md


def export_trace(
    trace: WorkflowTrace, output_dir: str, formats: Optional[List[str]] = None
) -> None:
    """
    Export trace to specified formats.

    Args:
        trace: Workflow trace
        output_dir: Output directory
        formats: List of formats ('json', 'html', 'svg', 'markdown', 'all')
                 If None, exports all formats
    """
    if formats is None or "all" in formats:
        formats = ["json", "html", "svg", "markdown"]

    exporter = TraceExporter(trace)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    base_name = f"trace_{trace.trace_id}"

    if "json" in formats:
        exporter.export_json(str(output_path / f"{base_name}.json"))

    if "html" in formats:
        exporter.export_timeline_html(str(output_path / f"{base_name}_timeline.html"))

    if "svg" in formats:
        exporter.export_agent_diagram_svg(str(output_path / f"{base_name}_agents.svg"))

    if "markdown" in formats:
        exporter.export_markdown_report(str(output_path / f"{base_name}_report.md"))

    print(f"\n✓ Trace exported to: {output_dir}")
