"""
Orchestrator agent (Supervisor pattern).

Coordinates all specialized agents and manages workflow execution.
"""

import asyncio
from typing import Dict, List, Optional, Any

from ..llm.base import LLMProvider
from .base import Agent, AgentType, AgentMessage, AgentState
from .constants import AgentNames, WorkflowSteps


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

    SYSTEM_PROMPT = """You are the Orchestrator Agent - the strategic coordinator of a multi-agent graph analytics workflow.

Your role:
- Coordinate specialized agents (Schema, Requirements, UseCase, Template, Execution, Reporting)
- Break down complex goals into agent-specific tasks
- Monitor progress and adapt workflow based on results
- Handle errors and make recovery decisions
- Ensure efficient collaboration between agents

# Decision Framework

## Workflow Adaptation Strategies

**Schema Complexity Assessment:**
- If schema complexity > 7: Recommend larger engine sizes for execution
- If schema has >20 collections: Suggest focusing on most important entities
- If graph is highly interconnected: Prioritize community detection algorithms

**Requirements Quality Check:**
- If requirements are vague or incomplete: Flag for user clarification before proceeding
- If no explicit objectives: Create default objectives based on domain
- If success criteria missing: Infer measurable goals from requirements text

**Template Validation:**
- If template generation fails: Simplify use case complexity and retry
- If algorithm not suitable for graph: Suggest alternative algorithms
- If resource requirements exceed limits: Adjust engine size or sample data

**Execution Monitoring:**
- If execution fails: Retry once with same parameters
- If retry fails: Try smaller engine size or reduced dataset
- If persistent failures: Escalate to user with detailed error context

## Agent Coordination Patterns

**Sequential Dependencies:**
1. Schema Analysis → Requirements Extraction (can run in parallel if both data sources available)
2. Schema + Requirements → Use Case Generation
3. Use Cases → Template Generation (sequential, validate each template)
4. Templates → Execution (can batch by algorithm type)
5. Execution Results → Report Generation (include full context chain)

**Parallel Opportunities:**
- Schema extraction and requirements extraction can run simultaneously
- Multiple templates can be validated in parallel
- Multiple executions can run concurrently (with resource limits)
- Multiple reports can be generated in parallel

**Error Recovery Strategies:**

1. **Schema Extraction Fails:**
   - Use fallback basic schema (collection names only)
   - Notify user of limited analysis capabilities
   - Proceed with reduced confidence

2. **Requirements Extraction Fails:**
   - Use default requirements template for domain
   - Flag all outputs as "low confidence - based on defaults"
   - Suggest user provide clearer requirements

3. **Template Generation Fails:**
   - Reduce use case complexity (simplify parameters)
   - Try alternative algorithm for same use case
   - Skip failing use case, continue with others

4. **Execution Fails:**
   - First retry: Same configuration
   - Second retry: Reduce engine size by one level
   - Third attempt: Sample data (if applicable)
   - If all fail: Report error with diagnostics, continue with successful executions

5. **Reporting Fails:**
   - Fall back to heuristic insights (no LLM)
   - Generate basic statistical summary
   - Flag report as "automated analysis only"

## Quality Assurance Checkpoints

**After Schema Analysis:**
- Verify: key_entities identified (>0)
- Verify: domain detected
- Verify: complexity_score in valid range (0-10)
- If any fail: Log warning, use fallback values

**After Requirements Extraction:**
- Verify: At least 1 objective or requirement extracted
- Verify: Domain identified matches schema domain (if both present)
- If mismatch: Flag inconsistency, prefer requirements domain

**After Template Generation:**
- Verify: All templates have valid algorithm types
- Verify: Resource requirements are reasonable
- Verify: Required collections exist in schema
- If any fail: Remove invalid template, log reason

**After Execution:**
- Verify: Results returned (>0 documents)
- Verify: Execution time reasonable (<5 minutes for standard, <30 min for large)
- Verify: Result structure matches expected algorithm output
- If any fail: Mark execution as suspect, flag in report

## Success Criteria

Workflow is successful if:
- At least 1 use case generated
- At least 1 template executed successfully
- At least 1 report with actionable insights
- No critical errors preventing completion
- All quality checkpoints passed or handled gracefully

## Cost & Performance Optimization

**Resource Management:**
- Batch similar algorithms together for engine reuse
- Reuse schema analysis across multiple workflows
- Cache requirements extraction for iterative refinements
- Limit concurrent executions to avoid cost spikes

**Execution Priorities:**
- Critical priority use cases run first
- High-value algorithms (PageRank, WCC) prioritized
- Quick algorithms (label_propagation) before slow ones (betweenness)
- Fail fast: Cancel long-running jobs if they exceed expected time by 3x

Your goal: Maximize successful completion while maintaining quality, minimizing cost, and providing clear diagnostics on any failures."""

    def __init__(self, llm_provider: LLMProvider, agents: Dict[str, Agent]):
        """
        Initialize orchestrator.

        Args:
            llm_provider: LLM provider for reasoning
            agents: Dictionary of specialized agents by name
        """
        super().__init__(
            agent_type=AgentType.ORCHESTRATOR,
            name=AgentNames.ORCHESTRATOR,
            llm_provider=llm_provider,
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
                reply_to=message.message_id,
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
                    "completed_steps": state.completed_steps,
                },
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
                    "summary": self._create_summary(state),
                },
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
                "completed_steps": state.completed_steps,
            },
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
        self, step: str, original_message: AgentMessage, state: AgentState
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
            WorkflowSteps.REPORTING: AgentNames.REPORTING_SPECIALIST,
        }

        agent_name = step_to_agent.get(step)
        if not agent_name or agent_name not in self.agents:
            self.log(f"Unknown step or agent: {step}", "error")
            return self.create_message(
                to_agent="user",
                message_type="error",
                content={"error": f"Unknown step: {step}"},
            )

        state.current_step = step

        # Create task message for agent
        task_message = self.create_message(
            to_agent=agent_name,
            message_type="task",
            content={"step": step, "instructions": f"Execute {step}"},
        )

        state.add_message(task_message)

        # Execute agent
        agent = self.agents[agent_name]
        response = agent.process(task_message, state)

        state.add_message(response)

        # Process agent response
        return self.process(response, state)

    def _decide_recovery_strategy(
        self, agent_name: str, error: str, state: AgentState
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
            "errors": len(state.errors),
        }

    def run_workflow(
        self,
        input_documents: Optional[List[Dict[str, Any]]] = None,
        database_config: Optional[Dict[str, Any]] = None,
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
            input_documents=input_documents or [], database_config=database_config or {}
        )

        # Start workflow
        start_message = self.create_message(
            to_agent="Orchestrator",
            message_type="start",
            content={"goal": "Complete graph analytics workflow"},
        )

        self.process(start_message, state)

        return state

    async def run_workflow_async(
        self,
        input_documents: Optional[List[Dict[str, Any]]] = None,
        database_config: Optional[Dict[str, Any]] = None,
        enable_parallelism: bool = True,
    ) -> AgentState:
        """
        Run complete workflow with parallel execution (async version).

        This method enables parallel execution of independent workflow steps:
        - Schema analysis and requirements extraction run in parallel
        - Template generation can process multiple templates concurrently
        - Execution runs multiple analyses in parallel
        - Report generation processes all reports concurrently

        Args:
            input_documents: Input requirement documents
            database_config: Database configuration
            enable_parallelism: Enable parallel execution of independent steps

        Returns:
            Final workflow state with performance metrics
        """
        # Initialize state
        state = AgentState(
            input_documents=input_documents or [], database_config=database_config or {}
        )

        self.log("🚀 Starting parallel agentic workflow orchestration")

        if enable_parallelism:
            await self._run_parallel_workflow(state)
        else:
            await self._run_sequential_workflow(state)

        self.log("✅ Workflow complete!")
        return state

    async def _run_sequential_workflow(self, state: AgentState):
        """Run workflow sequentially using async agents."""
        for step in self.workflow_steps:
            self.log(f"Executing step: {step}")
            await self._execute_step_async(step, state)
            state.mark_step_complete(step)

    async def _run_parallel_workflow(self, state: AgentState):
        """
        Run workflow with parallelism where possible.

        Parallelization strategy:
        1. Phase 1 (Parallel): Schema analysis + Requirements extraction
        2. Phase 2 (Sequential): Use case generation (depends on both phase 1 outputs)
        3. Phase 3 (Sequential): Template generation
        4. Phase 4 (Parallel): Execute all templates concurrently
        5. Phase 5 (Parallel): Generate all reports concurrently
        """

        # Phase 1: Run schema analysis and requirements extraction in parallel
        self.log("Phase 1: Parallel schema + requirements analysis")
        schema_task = self._execute_step_async(WorkflowSteps.SCHEMA_ANALYSIS, state)
        requirements_task = self._execute_step_async(
            WorkflowSteps.REQUIREMENTS_EXTRACTION, state
        )

        await asyncio.gather(schema_task, requirements_task)
        await state.mark_step_complete_async(WorkflowSteps.SCHEMA_ANALYSIS)
        await state.mark_step_complete_async(WorkflowSteps.REQUIREMENTS_EXTRACTION)

        # Phase 2: Generate use cases (sequential - depends on both schema and requirements)
        self.log("Phase 2: Use case generation")
        await self._execute_step_async(WorkflowSteps.USE_CASE_GENERATION, state)
        await state.mark_step_complete_async(WorkflowSteps.USE_CASE_GENERATION)

        # Phase 3: Generate templates (sequential for now, could be parallelized later)
        self.log("Phase 3: Template generation")
        await self._execute_step_async(WorkflowSteps.TEMPLATE_GENERATION, state)
        await state.mark_step_complete_async(WorkflowSteps.TEMPLATE_GENERATION)

        # Phase 4: Execute all templates in parallel (handled by ExecutionAgent's async method)
        self.log("Phase 4: Parallel execution of all templates")
        await self._execute_step_async(WorkflowSteps.EXECUTION, state)
        await state.mark_step_complete_async(WorkflowSteps.EXECUTION)

        # Phase 5: Generate all reports in parallel (handled by ReportingAgent's async method)
        self.log("Phase 5: Parallel report generation")
        await self._execute_step_async(WorkflowSteps.REPORTING, state)
        await state.mark_step_complete_async(WorkflowSteps.REPORTING)

    async def _execute_step_async(self, step: str, state: AgentState):
        """Execute a single workflow step asynchronously."""
        # Map steps to agents
        step_to_agent = {
            WorkflowSteps.SCHEMA_ANALYSIS: AgentNames.SCHEMA_ANALYST,
            WorkflowSteps.REQUIREMENTS_EXTRACTION: AgentNames.REQUIREMENTS_ANALYST,
            WorkflowSteps.USE_CASE_GENERATION: AgentNames.USE_CASE_EXPERT,
            WorkflowSteps.TEMPLATE_GENERATION: AgentNames.TEMPLATE_ENGINEER,
            WorkflowSteps.EXECUTION: AgentNames.EXECUTION_SPECIALIST,
            WorkflowSteps.REPORTING: AgentNames.REPORTING_SPECIALIST,
        }

        agent_name = step_to_agent.get(step)
        if not agent_name or agent_name not in self.agents:
            self.log(f"Unknown step or agent: {step}", "error")
            raise ValueError(f"Unknown step: {step}")

        state.current_step = step

        # Create task message for agent
        task_message = self.create_message(
            to_agent=agent_name,
            message_type="task",
            content={
                "step": step,
                "instructions": f"Execute {step}",
                "documents": state.input_documents,  # Pass documents for requirements agent
            },
        )

        await state.add_message_async(task_message)

        # Execute agent asynchronously
        agent = self.agents[agent_name]

        # Use async method if available
        if hasattr(agent, "process_async"):
            response = await agent.process_async(task_message, state)
        else:
            # Fallback to sync method in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, agent.process, task_message, state
            )

        await state.add_message_async(response)

        # Check for errors
        if response.message_type == "error":
            error_msg = response.content.get("error", "Unknown error")
            self.log(f"Error in {step}: {error_msg}", "error")
            raise RuntimeError(f"Step {step} failed: {error_msg}")

        self.log(f"✓ Completed: {step}")
