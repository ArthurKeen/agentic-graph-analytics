"""
Main workflow orchestrator for AI-assisted graph analytics.

Coordinates the execution of all workflow steps with state management,
error handling, and checkpointing.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..llm.base import LLMProvider
from ..llm.factory import create_llm_provider
from ..execution.metrics import ExecutionSummary
from ..reporting.config import WorkflowReportConfig
from ..reporting.formatter import ExecutionReportFormatter

from .state import WorkflowState, WorkflowStatus, WorkflowStep
from .steps import WorkflowSteps
from .exceptions import WorkflowStepError, WorkflowCheckpointError


@dataclass
class WorkflowResult:
    """
    Result of a complete workflow execution.

    Contains paths to all generated artifacts and summary information.
    """

    workflow_id: str
    """Unique identifier for the workflow run."""

    status: WorkflowStatus
    """Final status of the workflow."""

    output_dir: str
    """Directory containing all output files."""

    prd_path: Optional[str] = None
    """Path to generated PRD."""

    use_cases_path: Optional[str] = None
    """Path to generated use cases."""

    schema_path: Optional[str] = None
    """Path to schema analysis."""

    requirements_path: Optional[str] = None
    """Path to requirements summary."""

    execution_report_path: Optional[str] = None
    """Path to execution report (if execution was performed)."""

    execution_summary: Optional[ExecutionSummary] = None
    """Execution summary with metrics (if execution was performed)."""

    error_message: Optional[str] = None
    """Error message if workflow failed."""

    completed_steps: List[str] = field(default_factory=list)
    """List of completed step names."""

    total_duration_seconds: Optional[float] = None
    """Total execution time in seconds."""


class WorkflowOrchestrator:
    """
    Orchestrates the complete AI-assisted graph analytics workflow.

    Manages:
    - Step execution in proper order
    - State management and checkpointing
    - Error handling and recovery
    - Resume from failures

    Example:
        >>> from graph_analytics_ai.ai.workflow import WorkflowOrchestrator
        >>>
        >>> orchestrator = WorkflowOrchestrator(output_dir="./outputs")
        >>> result = orchestrator.run_complete_workflow(
        ...     business_requirements=["requirements.pdf"],
        ...     database_endpoint="http://localhost:8529",
        ...     database_name="my_graph",
        ...     database_password="password"
        ... )
        >>>
        >>> print(f"PRD: {result.prd_path}")
        >>> print(f"Use Cases: {result.use_cases_path}")
    """

    def __init__(
        self,
        output_dir: str = "./workflow_output",
        llm_provider: Optional[LLMProvider] = None,
        enable_checkpoints: bool = True,
        max_retries: int = 3,
        report_config: Optional[WorkflowReportConfig] = None,
    ):
        """
        Initialize workflow orchestrator.

        Args:
            output_dir: Directory for output files and checkpoints.
            llm_provider: LLM provider (creates default if not provided).
            enable_checkpoints: Whether to save state checkpoints.
            max_retries: Maximum number of retries for failed steps.
            report_config: Configuration for report generation (uses defaults if not provided).
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.llm_provider = llm_provider or create_llm_provider()
        self.enable_checkpoints = enable_checkpoints
        self.max_retries = max_retries
        self.report_config = report_config or WorkflowReportConfig()

        self.steps_executor = WorkflowSteps(self.llm_provider)
        self.state: Optional[WorkflowState] = None

    def run_complete_workflow(
        self,
        business_requirements: List[str],
        database_endpoint: str,
        database_name: str,
        database_username: str = "root",
        database_password: str = "",
        product_name: str = "Graph Analytics AI Project",
        resume_from_checkpoint: bool = False,
    ) -> WorkflowResult:
        """
        Run the complete end-to-end workflow.

        Steps:
        1. Parse business requirement documents
        2. Extract requirements using LLM
        3. Extract graph schema from database
        4. Analyze schema using LLM
        5. Generate PRD
        6. Generate use cases
        7. Save all outputs

        Args:
            business_requirements: Paths to requirement documents.
            database_endpoint: ArangoDB endpoint URL.
            database_name: Name of the database to analyze.
            database_username: Database username.
            database_password: Database password.
            product_name: Name for the product/project.
            resume_from_checkpoint: Whether to resume from last checkpoint.

        Returns:
            WorkflowResult with paths to all generated artifacts.

        Raises:
            WorkflowError: If workflow fails after all retries.
        """
        # Initialize or resume state
        if resume_from_checkpoint:
            self.state = self._load_checkpoint()
        else:
            self.state = self._create_new_state(
                business_requirements=business_requirements,
                database_endpoint=database_endpoint,
                database_name=database_name,
                database_username=database_username,
                product_name=product_name,
            )

        start_time = datetime.utcnow()

        try:
            # Step 1: Parse Documents
            documents = self._execute_step(
                WorkflowStep.PARSE_DOCUMENTS,
                lambda: self.steps_executor.parse_documents(business_requirements),
                "documents",
            )

            # Step 2: Extract Requirements
            extracted_requirements = self._execute_step(
                WorkflowStep.EXTRACT_REQUIREMENTS,
                lambda: self.steps_executor.extract_requirements(documents),
                "extracted_requirements",
            )

            # Step 3: Extract Schema
            schema = self._execute_step(
                WorkflowStep.EXTRACT_SCHEMA,
                lambda: self.steps_executor.extract_schema(
                    database_endpoint=database_endpoint,
                    database_name=database_name,
                    username=database_username,
                    password=database_password,
                ),
                "schema",
            )

            # Step 4: Analyze Schema
            schema_analysis = self._execute_step(
                WorkflowStep.ANALYZE_SCHEMA,
                lambda: self.steps_executor.analyze_schema(schema),
                "schema_analysis",
            )

            # Step 5: Generate PRD
            prd_content = self._execute_step(
                WorkflowStep.GENERATE_PRD,
                lambda: self.steps_executor.generate_prd(
                    extracted_requirements=extracted_requirements,
                    schema=schema,
                    schema_analysis=schema_analysis,
                    product_name=product_name,
                ),
                "prd_content",
            )

            # Step 6: Generate Use Cases
            use_cases = self._execute_step(
                WorkflowStep.GENERATE_USE_CASES,
                lambda: self.steps_executor.generate_use_cases(
                    extracted_requirements=extracted_requirements,
                    schema_analysis=schema_analysis,
                ),
                "use_cases",
            )

            # Step 7: Save Outputs
            saved_files = self._execute_step(
                WorkflowStep.SAVE_OUTPUTS,
                lambda: self.steps_executor.save_outputs(
                    output_dir=self.output_dir,
                    prd_content=prd_content,
                    use_cases=use_cases,
                    schema=schema,
                    schema_analysis=schema_analysis,
                    extracted_requirements=extracted_requirements,
                ),
                "saved_files",
            )

            # Mark workflow as completed
            self.state.mark_completed()
            self._save_checkpoint()

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            return WorkflowResult(
                workflow_id=self.state.workflow_id,
                status=WorkflowStatus.COMPLETED,
                output_dir=str(self.output_dir),
                prd_path=saved_files.get("prd"),
                use_cases_path=saved_files.get("use_cases"),
                schema_path=saved_files.get("schema"),
                requirements_path=saved_files.get("requirements"),
                completed_steps=[step.value for step in self.state.completed_steps],
                total_duration_seconds=duration,
            )

        except Exception as e:
            self.state.mark_failed(str(e))
            self._save_checkpoint()

            return WorkflowResult(
                workflow_id=self.state.workflow_id,
                status=WorkflowStatus.FAILED,
                output_dir=str(self.output_dir),
                error_message=str(e),
                completed_steps=[step.value for step in self.state.completed_steps],
            )

    def run_partial_workflow(
        self, steps_to_run: List[WorkflowStep], **kwargs
    ) -> WorkflowResult:
        """
        Run a subset of workflow steps.

        Useful for testing or running only specific parts of the workflow.

        Args:
            steps_to_run: List of steps to execute.
            **kwargs: Step-specific arguments.

        Returns:
            WorkflowResult with partial results.
        """
        # This is a placeholder for partial workflow support
        # Can be implemented based on specific use cases
        raise NotImplementedError("Partial workflow execution coming soon")

    def _execute_step(
        self,
        step: WorkflowStep,
        step_func: callable,
        output_key: str,
        retry_count: int = 0,
    ) -> Any:
        """
        Execute a workflow step with error handling and retry logic.

        Args:
            step: The workflow step to execute.
            step_func: Function to execute the step.
            output_key: Key to store output in state.
            retry_count: Current retry attempt.

        Returns:
            The step output.

        Raises:
            WorkflowStepError: If step fails after all retries.
        """
        # Skip if already completed
        if self.state.is_step_completed(step):
            return self.state.outputs.get(output_key)

        # Mark step as started
        self.state.mark_step_started(step)
        self._save_checkpoint()

        try:
            # Execute the step
            result = step_func()

            # Store result
            self.state.outputs[output_key] = result
            self.state.mark_step_completed(step, {output_key: str(type(result))})
            self._save_checkpoint()

            return result

        except Exception as e:
            error_msg = f"{step.value} failed: {str(e)}"

            # Retry logic
            if retry_count < self.max_retries:
                print(
                    f"Retrying {step.value} (attempt {retry_count + 1}/{self.max_retries})"
                )
                return self._execute_step(step, step_func, output_key, retry_count + 1)

            # Mark step as failed
            self.state.mark_step_failed(step, error_msg)
            self._save_checkpoint()

            raise WorkflowStepError(step.value, str(e), e)

    def _create_new_state(self, **inputs) -> WorkflowState:
        """Create a new workflow state."""
        workflow_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        return WorkflowState(
            workflow_id=workflow_id,
            status=WorkflowStatus.NOT_STARTED,
            created_at=now,
            updated_at=now,
            inputs=inputs,
        )

    def _save_checkpoint(self) -> None:
        """Save current state to checkpoint."""
        if not self.enable_checkpoints or not self.state:
            return

        try:
            checkpoint_path = (
                self.output_dir / f"checkpoint_{self.state.workflow_id}.json"
            )
            self.state.save_checkpoint(checkpoint_path)
        except Exception as e:
            # Don't fail workflow if checkpoint fails, just log
            print(f"Warning: Failed to save checkpoint: {e}")

    def _load_checkpoint(self) -> WorkflowState:
        """Load most recent checkpoint."""
        checkpoint_files = list(self.output_dir.glob("checkpoint_*.json"))

        if not checkpoint_files:
            raise WorkflowCheckpointError("No checkpoint files found")

        # Get most recent checkpoint
        latest_checkpoint = max(checkpoint_files, key=lambda p: p.stat().st_mtime)

        try:
            return WorkflowState.load_checkpoint(latest_checkpoint)
        except Exception as e:
            raise WorkflowCheckpointError(f"Failed to load checkpoint: {e}")

    def _generate_execution_report(
        self, execution_summary: ExecutionSummary
    ) -> Optional[str]:
        """
        Generate execution report from summary.

        Args:
            execution_summary: Summary of execution metrics

        Returns:
            Path to generated report file, or None if reporting disabled
        """
        if not self.report_config.enable_execution_reporting:
            return None

        try:
            # Create reports subdirectory
            reports_dir = self.output_dir / self.report_config.report_directory
            reports_dir.mkdir(parents=True, exist_ok=True)

            # Generate report
            formatter = ExecutionReportFormatter(self.report_config.execution_report)
            report_path = reports_dir / "execution_report.md"
            formatter.save_report(execution_summary, report_path)

            return str(report_path)
        except Exception as e:
            # Log error but don't fail workflow
            print(f"Warning: Failed to generate execution report: {e}")
            return None

    def get_state(self) -> Optional[WorkflowState]:
        """Get current workflow state."""
        return self.state

    def get_progress(self) -> Dict[str, Any]:
        """
        Get workflow progress information.

        Returns:
            Dictionary with progress details.
        """
        if not self.state:
            return {"status": "not_started", "progress": 0.0}

        total_steps = len(WorkflowStep)
        completed_steps = len(self.state.completed_steps)
        progress = completed_steps / total_steps if total_steps > 0 else 0.0

        return {
            "workflow_id": self.state.workflow_id,
            "status": self.state.status.value,
            "progress": progress,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "current_step": (
                self.state.current_step.value if self.state.current_step else None
            ),
            "error_message": self.state.error_message,
        }
