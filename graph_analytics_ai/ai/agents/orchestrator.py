"""
Orchestrator agent (Supervisor pattern).

Coordinates all specialized agents and manages workflow execution.
"""

from typing import Dict, List, Optional, Any

from ..llm.base import LLMProvider
from .base import Agent, AgentType, AgentMessage, AgentState
from .constants import AgentNames, WorkflowSteps, AgentDefaults


class OrchestratorAgent(Agent):
    """
    Orchestrator Agent (Supervisor).
    
    Responsibilities:
    - Break down high-level goals into tasks
    - Assign tasks to specialized agents
    - Monitor progress and handle errors
    - Make strategic decisions about workflow direction
    - Coordinate agent collaboration
    
    Uses a supervisor pattern to delegate work to specialized agents.
    """
    
    SYSTEM_PROMPT = """You are the Orchestrator Agent - the strategic coordinator of a multi-agent system.

Your role:
- Coordinate specialized agents (Schema, Requirements, UseCase, Template, Execution, Reporting)
- Break down complex goals into agent-specific tasks
- Monitor progress and adapt workflow based on results
- Handle errors and make recovery decisions
- Ensure efficient collaboration between agents

Your goal: Successfully orchestrate the complete workflow from requirements to insights."""
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        agents: Dict[str, Agent]
    ):
        """
        Initialize orchestrator.
        
        Args:
            llm_provider: LLM provider for reasoning
            agents: Dictionary of specialized agents by name
        """
        super().__init__(
            agent_type=AgentType.ORCHESTRATOR,
            name=AgentNames.ORCHESTRATOR,
            llm_provider=llm_provider
        )
        self.agents = agents
        self.workflow_steps = WorkflowSteps.STANDARD_WORKFLOW
    
    def process(self, message: AgentMessage, state: AgentState) -> AgentMessage:
        """
        Process message and coordinate workflow.
        
        Args:
            message: Incoming message
            state: Shared state
            
        Returns:
            Response message
        """
        message_type = message.message_type
        
        if message_type == "start":
            return self._handle_start(message, state)
        elif message_type == "result":
            return self._handle_result(message, state)
        elif message_type == "error":
            return self._handle_error(message, state)
        else:
            return self.create_message(
                to_agent=message.from_agent,
                message_type="error",
                content={"error": f"Unknown message type: {message_type}"},
                reply_to=message.message_id
            )
    
    def _handle_start(self, message: AgentMessage, state: AgentState) -> AgentMessage:
        """Handle workflow start."""
        self.log("🚀 Starting agentic workflow orchestration")
        
        # Determine first step
        next_step = self._determine_next_step(state)
        
        if next_step:
            self.log(f"Next step: {next_step}")
            return self._delegate_to_agent(next_step, message, state)
        else:
            self.log("✅ Workflow complete!")
            return self.create_message(
                to_agent="user",
                message_type="complete",
                content={
                    "status": "success",
                    "message": "Workflow completed successfully",
                    "completed_steps": state.completed_steps
                }
            )
    
    def _handle_result(self, message: AgentMessage, state: AgentState) -> AgentMessage:
        """Handle agent result."""
        from_agent = message.from_agent
        content = message.content
        
        self.log(f"✓ Received result from {from_agent}: {content.get('status')}")
        
        # Determine next step
        next_step = self._determine_next_step(state)
        
        if next_step:
            self.log(f"Next step: {next_step}")
            return self._delegate_to_agent(next_step, message, state)
        else:
            self.log("✅ Workflow complete!")
            return self.create_message(
                to_agent="user",
                message_type="complete",
                content={
                    "status": "success",
                    "message": "Workflow completed successfully",
                    "completed_steps": state.completed_steps,
                    "summary": self._create_summary(state)
                }
            )
    
    def _handle_error(self, message: AgentMessage, state: AgentState) -> AgentMessage:
        """Handle agent error."""
        from_agent = message.from_agent
        error = message.content.get("error")
        
        self.log(f"✗ Error from {from_agent}: {error}", "error")
        
        # Decide on recovery strategy
        strategy = self._decide_recovery_strategy(from_agent, error, state)
        
        if strategy == "retry":
            self.log(f"Retrying {from_agent}")
            return self._delegate_to_agent(state.current_step, message, state)
        
        elif strategy == "skip":
            self.log(f"Skipping {state.current_step}")
            state.mark_step_complete(state.current_step)
            next_step = self._determine_next_step(state)
            if next_step:
                return self._delegate_to_agent(next_step, message, state)
        
        # Abort
        self.log("Aborting workflow", "error")
        return self.create_message(
            to_agent="user",
            message_type="error",
            content={
                "status": "failed",
                "error": f"Workflow failed at {state.current_step}: {error}",
                "completed_steps": state.completed_steps
            }
        )
    
    def _determine_next_step(self, state: AgentState) -> Optional[str]:
        """
        Determine next workflow step.
        
        Args:
            state: Current state
            
        Returns:
            Next step name or None if workflow complete
        """
        for step in self.workflow_steps:
            if step not in state.completed_steps:
                return step
        return None
    
    def _delegate_to_agent(
        self,
        step: str,
        original_message: AgentMessage,
        state: AgentState
    ) -> AgentMessage:
        """
        Delegate task to appropriate agent.
        
        Args:
            step: Workflow step
            original_message: Original message
            state: Current state
            
        Returns:
            Message to send to agent
        """
        # Map steps to agents
        step_to_agent = {
            WorkflowSteps.SCHEMA_ANALYSIS: AgentNames.SCHEMA_ANALYST,
            WorkflowSteps.REQUIREMENTS_EXTRACTION: AgentNames.REQUIREMENTS_ANALYST,
            WorkflowSteps.USE_CASE_GENERATION: AgentNames.USE_CASE_EXPERT,
            WorkflowSteps.TEMPLATE_GENERATION: AgentNames.TEMPLATE_ENGINEER,
            WorkflowSteps.EXECUTION: AgentNames.EXECUTION_SPECIALIST,
            WorkflowSteps.REPORTING: AgentNames.REPORTING_SPECIALIST
        }
        
        agent_name = step_to_agent.get(step)
        if not agent_name or agent_name not in self.agents:
            self.log(f"Unknown step or agent: {step}", "error")
            return self.create_message(
                to_agent="user",
                message_type="error",
                content={"error": f"Unknown step: {step}"}
            )
        
        state.current_step = step
        
        # Create task message for agent
        task_message = self.create_message(
            to_agent=agent_name,
            message_type="task",
            content={
                "step": step,
                "instructions": f"Execute {step}"
            }
        )
        
        state.add_message(task_message)
        
        # Execute agent
        agent = self.agents[agent_name]
        response = agent.process(task_message, state)
        
        state.add_message(response)
        
        # Process agent response
        return self.process(response, state)
    
    def _decide_recovery_strategy(
        self,
        agent_name: str,
        error: str,
        state: AgentState
    ) -> str:
        """
        Decide error recovery strategy.
        
        Args:
            agent_name: Agent that failed
            error: Error message
            state: Current state
            
        Returns:
            Strategy: "retry", "skip", or "abort"
        """
        # Simple heuristic - could use LLM reasoning
        
        # If it's a non-critical step, skip
        skippable_steps = ["requirements_extraction"]
        if state.current_step in skippable_steps:
            return "skip"
        
        # Check retry count
        error_count = len([e for e in state.errors if e["agent"] == agent_name])
        if error_count < 2:
            return "retry"
        
        # Otherwise abort
        return "abort"
    
    def _create_summary(self, state: AgentState) -> Dict[str, Any]:
        """Create workflow summary."""
        return {
            "completed_steps": len(state.completed_steps),
            "total_steps": len(self.workflow_steps),
            "use_cases_generated": len(state.use_cases),
            "templates_generated": len(state.templates),
            "analyses_executed": len(state.execution_results),
            "reports_generated": len(state.reports),
            "errors": len(state.errors)
        }
    
    def run_workflow(
        self,
        input_documents: Optional[List[Dict[str, Any]]] = None,
        database_config: Optional[Dict[str, Any]] = None
    ) -> AgentState:
        """
        Run complete workflow.
        
        Args:
            input_documents: Input requirement documents
            database_config: Database configuration
            
        Returns:
            Final workflow state
        """
        # Initialize state
        state = AgentState(
            input_documents=input_documents or [],
            database_config=database_config or {}
        )
        
        # Start workflow
        start_message = self.create_message(
            to_agent="Orchestrator",
            message_type="start",
            content={"goal": "Complete graph analytics workflow"}
        )
        
        self.process(start_message, state)
        
        return state
