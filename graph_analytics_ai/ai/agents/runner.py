"""
Agentic workflow runner.

High-level interface for running the agentic workflow.
"""

from typing import Dict, List, Optional, Any

from ..llm import create_llm_provider
from ...db_connection import get_db_connection

from .base import AgentState
from .orchestrator import OrchestratorAgent
from .specialized import (
    SchemaAnalysisAgent,
    RequirementsAgent,
    UseCaseAgent,
    TemplateAgent,
    ExecutionAgent,
    ReportingAgent,
)
from .constants import AgentNames


class AgenticWorkflowRunner:
    """
    High-level runner for agentic workflow.

    Sets up agents and orchestrates the complete workflow.

    Example:
        >>> from graph_analytics_ai.ai.agents import AgenticWorkflowRunner
        >>>
        >>> runner = AgenticWorkflowRunner()
        >>> state = runner.run()
        >>>
        >>> print(f"Generated {len(state.reports)} reports")
        >>> for report in state.reports:
        ...     print(f"- {report.title}")
    """

    def __init__(
        self,
        db_connection=None,
        llm_provider=None,
        graph_name: str = "graph",
        core_collections: Optional[List[str]] = None,
        satellite_collections: Optional[List[str]] = None,
        enable_tracing: bool = True,
        enable_debug_mode: bool = False,
    ):
        """
        Initialize workflow runner.

        Args:
            db_connection: Database connection (creates default if None)
            llm_provider: LLM provider (creates default if None)
            graph_name: Name of graph for templates
            core_collections: Core business entity collections for analysis
            satellite_collections: Satellite/metadata collections to exclude from connectivity algorithms
            enable_tracing: Whether to enable workflow tracing (default: True)
            enable_debug_mode: Whether to enable verbose debug mode (default: False)
        """
        self.db = db_connection or get_db_connection()
        self.llm_provider = llm_provider or create_llm_provider()
        self.graph_name = graph_name
        self.core_collections = core_collections or []
        self.satellite_collections = satellite_collections or []
        self.enable_tracing = enable_tracing
        self.enable_debug_mode = enable_debug_mode

        # Initialize tracing
        self.trace_collector = None
        self.debug_mode = None
        if enable_tracing:
            from ..tracing import TraceCollector
            from ..tracing.replay import DebugMode
            import time

            self.trace_collector = TraceCollector(
                workflow_id=f"workflow-{int(time.time() * 1000)}",
                enable_state_snapshots=enable_debug_mode,
            )

            if enable_debug_mode:
                self.debug_mode = DebugMode(enabled=True)
                self.trace_collector.debug_mode = self.debug_mode

        # Initialize agents (pass trace collector to them)
        self.agents = self._create_agents()

        # Initialize orchestrator
        self.orchestrator = OrchestratorAgent(
            llm_provider=self.llm_provider, agents=self.agents
        )
        if self.trace_collector:
            self.orchestrator.trace_collector = self.trace_collector

    def _create_agents(self) -> Dict[str, Any]:
        """Create all specialized agents."""
        return {
            AgentNames.SCHEMA_ANALYST: SchemaAnalysisAgent(
                llm_provider=self.llm_provider,
                db_connection=self.db,
                trace_collector=self.trace_collector,
            ),
            AgentNames.REQUIREMENTS_ANALYST: RequirementsAgent(
                llm_provider=self.llm_provider, trace_collector=self.trace_collector
            ),
            AgentNames.USE_CASE_EXPERT: UseCaseAgent(
                llm_provider=self.llm_provider, trace_collector=self.trace_collector
            ),
            AgentNames.TEMPLATE_ENGINEER: TemplateAgent(
                llm_provider=self.llm_provider,
                graph_name=self.graph_name,
                core_collections=self.core_collections,
                satellite_collections=self.satellite_collections,
                trace_collector=self.trace_collector,
            ),
            AgentNames.EXECUTION_SPECIALIST: ExecutionAgent(
                llm_provider=self.llm_provider, trace_collector=self.trace_collector
            ),
            AgentNames.REPORTING_SPECIALIST: ReportingAgent(
                llm_provider=self.llm_provider, trace_collector=self.trace_collector
            ),
        }

    def run(
        self,
        input_documents: Optional[List[Dict[str, Any]]] = None,
        database_config: Optional[Dict[str, Any]] = None,
        max_executions: int = 3,
    ) -> AgentState:
        """
        Run complete agentic workflow.

        Args:
            input_documents: Input requirement documents
            database_config: Database configuration
            max_executions: Maximum number of analyses to execute

        Returns:
            Final workflow state with all results
        """
        print("🤖 Starting Agentic Workflow")
        if self.enable_tracing:
            print("   📊 Tracing enabled")
        if self.enable_debug_mode:
            print("   🐛 Debug mode enabled")
        print("=" * 70)
        print()

        # Record workflow start
        if self.trace_collector:
            from ..tracing import TraceEventType

            self.trace_collector.record_event(
                TraceEventType.WORKFLOW_START, data={"graph_name": self.graph_name}
            )

        # Run workflow
        state = self.orchestrator.run_workflow(
            input_documents=input_documents, database_config=database_config
        )

        # Record workflow end
        if self.trace_collector:
            self.trace_collector.record_event(TraceEventType.WORKFLOW_END)

        print()
        print("=" * 70)
        print("🎉 Agentic Workflow Complete!")
        print()

        # Print summary
        self._print_summary(state)

        return state

    def _print_summary(self, state: AgentState) -> None:
        """Print workflow summary."""
        print("📊 Summary:")
        print(f"   • Steps completed: {len(state.completed_steps)}")
        print(f"   • Use cases: {len(state.use_cases)}")
        print(f"   • Templates: {len(state.templates)}")
        print(f"   • Executions: {len(state.execution_results)}")
        print(f"   • Reports: {len(state.reports)}")
        print(f"   • Messages exchanged: {len(state.messages)}")
        print(f"   • Errors: {len(state.errors)}")
        print()

        if state.reports:
            print("📄 Generated Reports:")
            for i, report in enumerate(state.reports, 1):
                print(f"   {i}. {report.title}")
                print(f"      • Insights: {len(report.insights)}")
                print(f"      • Recommendations: {len(report.recommendations)}")
        print()

        if state.errors:
            print("⚠️  Errors encountered:")
            for error in state.errors:
                print(f"   • {error['agent']}: {error['error']}")
            print()

    def get_agent_messages(self, state: AgentState) -> List[Dict[str, Any]]:
        """
        Get all agent communication messages.

        Args:
            state: Workflow state

        Returns:
            List of messages
        """
        return [msg.to_dict() for msg in state.messages]

    def export_state(self, state: AgentState, output_path: str) -> None:
        """
        Export workflow state to JSON.

        Args:
            state: Workflow state
            output_path: Output file path
        """
        import json
        from pathlib import Path

        data = state.to_dict()

        Path(output_path).write_text(json.dumps(data, indent=2, default=str))
        print(f"💾 State exported to: {output_path}")

    def export_reports(self, state: AgentState, output_dir: str) -> None:
        """
        Export reports to markdown files.

        Args:
            state: Workflow state
            output_dir: Output directory path
        """
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if not state.reports:
            print("⚠️  No reports to export")
            return

        for i, report in enumerate(state.reports, 1):
            # Generate filename from report title
            safe_title = "".join(
                c if c.isalnum() or c in (" ", "-", "_") else "_" for c in report.title
            )
            safe_title = safe_title.replace(" ", "_").lower()
            filename = f"report_{i:02d}_{safe_title}.md"

            filepath = output_path / filename

            # Write report as markdown
            with open(filepath, "w") as f:
                f.write(f"# {report.title}\n\n")
                f.write(f"**Generated:** {report.generated_at}\n\n")
                f.write(f"## Summary\n\n{report.summary}\n\n")

                if report.insights:
                    f.write(f"## Insights ({len(report.insights)})\n\n")
                    for j, insight in enumerate(report.insights, 1):
                        f.write(f"### {j}. {insight.title}\n\n")
                        f.write(f"{insight.description}\n\n")
                        f.write(f"- **Type:** {insight.insight_type}\n")
                        f.write(f"- **Confidence:** {insight.confidence:.0%}\n")
                        if insight.business_impact:
                            f.write(
                                f"- **Business Impact:** {insight.business_impact}\n"
                            )
                        f.write("\n")

                if report.recommendations:
                    f.write(f"## Recommendations ({len(report.recommendations)})\n\n")
                    for j, rec in enumerate(report.recommendations, 1):
                        f.write(f"### {j}. {rec.title}\n\n")
                        f.write(f"{rec.description}\n\n")
                        f.write(f"- **Priority:** {rec.priority}\n")
                        if hasattr(rec, "effort_estimate") and rec.effort_estimate:
                            f.write(f"- **Effort:** {rec.effort_estimate}\n")
                        if hasattr(rec, "expected_impact") and rec.expected_impact:
                            f.write(f"- **Expected Impact:** {rec.expected_impact}\n")
                        f.write("\n")

            print(f"📄 Report {i} exported to: {filepath}")

        print(f"\n✓ Exported {len(state.reports)} reports to {output_path}")

    def export_trace(
        self, output_dir: str, formats: Optional[List[str]] = None
    ) -> None:
        """
        Export workflow trace.

        Args:
            output_dir: Output directory
            formats: List of formats ('json', 'html', 'svg', 'markdown', 'all')
                     If None, exports all formats
        """
        if not self.trace_collector:
            print("⚠️  Tracing was not enabled for this workflow")
            return

        from ..tracing.export import export_trace

        # Finalize trace
        trace = self.trace_collector.finalize()

        # Export to requested formats
        export_trace(trace, output_dir, formats)

        # Also export debug log if debug mode was enabled
        if self.debug_mode:
            from pathlib import Path

            debug_path = Path(output_dir) / f"debug_log_{trace.trace_id}.json"
            self.debug_mode.export_log(str(debug_path))

    def get_trace(self):
        """
        Get the finalized workflow trace.

        Returns:
            WorkflowTrace object or None if tracing not enabled
        """
        if not self.trace_collector:
            return None

        return self.trace_collector.finalize()

    def print_trace_summary(self) -> None:
        """Print trace summary."""
        if not self.trace_collector:
            print("⚠️  Tracing was not enabled for this workflow")
            return

        trace = self.trace_collector.finalize()

        if trace.performance:
            perf = trace.performance

            print("\n" + "=" * 70)
            print("📊 Workflow Trace Summary")
            print("=" * 70 + "\n")

            print(f"Trace ID: {trace.trace_id}")
            print(f"Total Events: {len(trace.events)}")
            print()

            print("Performance:")
            print(f"  Total Time: {perf.total_time_ms/1000:.2f}s")
            print(f"  Steps Completed: {perf.steps_completed}")
            if perf.steps_completed > 0:
                print(f"  Avg Time/Step: {perf.avg_time_per_step_ms:.0f}ms")
            print()

            print("LLM Usage:")
            print(f"  Total Calls: {perf.total_llm_calls}")
            print(f"  Total Time: {perf.total_llm_time_ms/1000:.2f}s")
            print(f"  Total Tokens: {perf.total_llm_tokens:,}")
            print(f"  Estimated Cost: ${perf.llm_cost_estimate_usd:.4f} USD")
            print()

            print("Communication:")
            print(f"  Messages Exchanged: {perf.total_messages}")
            print(f"  Errors: {perf.total_errors}")
            print()

            slowest = perf.get_slowest_agents(3)
            if slowest:
                print("Slowest Agents:")
                for i, agent_info in enumerate(slowest, 1):
                    print(
                        f"  {i}. {agent_info['agent']}: {agent_info['total_time_ms']:.0f}ms"
                    )
                print()

            top_llm = perf.get_top_llm_consumers(3)
            if top_llm:
                print("Top LLM Consumers:")
                for i, agent_info in enumerate(top_llm, 1):
                    print(
                        f"  {i}. {agent_info['agent']}: {agent_info['total_tokens']:,} tokens"
                    )
                print()


def run_agentic_workflow(
    graph_name: str = "graph", max_executions: int = 3, enable_tracing: bool = True
) -> AgentState:
    """
    Convenience function to run agentic workflow.

    Args:
        graph_name: Name of graph
        max_executions: Max analyses to execute
        enable_tracing: Whether to enable tracing

    Returns:
        Final workflow state
    """
    runner = AgenticWorkflowRunner(graph_name=graph_name, enable_tracing=enable_tracing)
    return runner.run(max_executions=max_executions)
