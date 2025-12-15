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
    ReportingAgent
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
        db_connection = None,
        llm_provider = None,
        graph_name: str = "graph"
    ):
        """
        Initialize workflow runner.
        
        Args:
            db_connection: Database connection (creates default if None)
            llm_provider: LLM provider (creates default if None)
            graph_name: Name of graph for templates
        """
        self.db = db_connection or get_db_connection()
        self.llm_provider = llm_provider or create_llm_provider()
        self.graph_name = graph_name
        
        # Initialize agents
        self.agents = self._create_agents()
        
        # Initialize orchestrator
        self.orchestrator = OrchestratorAgent(
            llm_provider=self.llm_provider,
            agents=self.agents
        )
    
    def _create_agents(self) -> Dict[str, Any]:
        """Create all specialized agents."""
        return {
            AgentNames.SCHEMA_ANALYST: SchemaAnalysisAgent(
                llm_provider=self.llm_provider,
                db_connection=self.db
            ),
            AgentNames.REQUIREMENTS_ANALYST: RequirementsAgent(
                llm_provider=self.llm_provider
            ),
            AgentNames.USE_CASE_EXPERT: UseCaseAgent(
                llm_provider=self.llm_provider
            ),
            AgentNames.TEMPLATE_ENGINEER: TemplateAgent(
                llm_provider=self.llm_provider,
                graph_name=self.graph_name
            ),
            AgentNames.EXECUTION_SPECIALIST: ExecutionAgent(
                llm_provider=self.llm_provider
            ),
            AgentNames.REPORTING_SPECIALIST: ReportingAgent(
                llm_provider=self.llm_provider
            )
        }
    
    def run(
        self,
        input_documents: Optional[List[Dict[str, Any]]] = None,
        database_config: Optional[Dict[str, Any]] = None,
        max_executions: int = 3
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
        print("=" * 70)
        print()
        
        # Run workflow
        state = self.orchestrator.run_workflow(
            input_documents=input_documents,
            database_config=database_config
        )
        
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
        
        data = {
            "workflow": state.to_dict(),
            "messages": self.get_agent_messages(state),
            "results": {
                "use_cases": len(state.use_cases),
                "templates": len(state.templates),
                "executions": len(state.execution_results),
                "reports": len(state.reports)
            }
        }
        
        Path(output_path).write_text(json.dumps(data, indent=2))
        print(f"💾 State exported to: {output_path}")


def run_agentic_workflow(
    graph_name: str = "graph",
    max_executions: int = 3
) -> AgentState:
    """
    Convenience function to run agentic workflow.
    
    Args:
        graph_name: Name of graph
        max_executions: Max analyses to execute
        
    Returns:
        Final workflow state
    """
    runner = AgenticWorkflowRunner(graph_name=graph_name)
    return runner.run(max_executions=max_executions)

