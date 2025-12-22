"""
Workflow orchestration for AI-assisted graph analytics.

This module provides end-to-end workflow automation that connects all AI components:
- Schema extraction and analysis
- Document parsing and requirements extraction
- PRD generation
- Use case generation
- State management and checkpointing
- Error handling and recovery

Example:
    >>> from graph_analytics_ai.ai.workflow import WorkflowOrchestrator
    >>>
    >>> orchestrator = WorkflowOrchestrator(output_dir="./workflow_output")
    >>> result = orchestrator.run_complete_workflow(
    ...     business_requirements=["requirements.pdf"],
    ...     database_endpoint="http://localhost:8529",
    ...     database_name="my_graph"
    ... )
    >>> print(result.prd_path)
    >>> print(result.use_cases_path)
"""

from .orchestrator import WorkflowOrchestrator, WorkflowResult
from .state import WorkflowState, WorkflowStep, WorkflowStatus
from .steps import WorkflowSteps
from .exceptions import (
    WorkflowError,
    WorkflowStepError,
    WorkflowStateError,
    WorkflowCheckpointError,
)

__all__ = [
    "WorkflowOrchestrator",
    "WorkflowResult",
    "WorkflowState",
    "WorkflowStep",
    "WorkflowStatus",
    "WorkflowSteps",
    "WorkflowError",
    "WorkflowStepError",
    "WorkflowStateError",
    "WorkflowCheckpointError",
]
