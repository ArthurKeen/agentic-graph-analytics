"""
Workflow state management and checkpointing.

Provides state tracking, serialization, and recovery capabilities for workflows.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any


class WorkflowStatus(Enum):
    """Status of the workflow."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class WorkflowStep(Enum):
    """Individual workflow steps."""

    PARSE_DOCUMENTS = "parse_documents"
    EXTRACT_REQUIREMENTS = "extract_requirements"
    EXTRACT_SCHEMA = "extract_schema"
    ANALYZE_SCHEMA = "analyze_schema"
    GENERATE_PRD = "generate_prd"
    GENERATE_USE_CASES = "generate_use_cases"
    SAVE_OUTPUTS = "save_outputs"


@dataclass
class StepResult:
    """Result of a workflow step."""

    step: WorkflowStep
    status: WorkflowStatus
    started_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    output_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    """
    Represents the complete state of a workflow execution.

    Can be serialized to JSON for checkpointing and recovery.
    """

    workflow_id: str
    """Unique identifier for this workflow run."""

    status: WorkflowStatus
    """Current status of the workflow."""

    created_at: str
    """When the workflow was created (ISO format)."""

    updated_at: str
    """When the workflow was last updated (ISO format)."""

    current_step: Optional[WorkflowStep] = None
    """Current step being executed."""

    completed_steps: List[WorkflowStep] = field(default_factory=list)
    """Steps that have been completed."""

    step_results: Dict[str, StepResult] = field(default_factory=dict)
    """Results for each completed step."""

    error_message: Optional[str] = None
    """Error message if workflow failed."""

    inputs: Dict[str, Any] = field(default_factory=dict)
    """Original workflow inputs."""

    outputs: Dict[str, Any] = field(default_factory=dict)
    """Workflow outputs and artifacts."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""

    def mark_step_started(self, step: WorkflowStep) -> None:
        """Mark a step as started."""
        self.current_step = step
        self.status = WorkflowStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow().isoformat()

        self.step_results[step.value] = StepResult(
            step=step,
            status=WorkflowStatus.IN_PROGRESS,
            started_at=datetime.utcnow().isoformat(),
        )

    def mark_step_completed(
        self, step: WorkflowStep, output_data: Dict[str, Any] = None
    ) -> None:
        """Mark a step as completed."""
        if step.value not in self.step_results:
            raise ValueError(f"Step {step.value} was not started")

        self.step_results[step.value].status = WorkflowStatus.COMPLETED
        self.step_results[step.value].completed_at = datetime.utcnow().isoformat()
        if output_data:
            self.step_results[step.value].output_data = output_data

        if step not in self.completed_steps:
            self.completed_steps.append(step)

        self.current_step = None
        self.updated_at = datetime.utcnow().isoformat()

    def mark_step_failed(self, step: WorkflowStep, error_message: str) -> None:
        """Mark a step as failed."""
        if step.value not in self.step_results:
            self.step_results[step.value] = StepResult(
                step=step,
                status=WorkflowStatus.FAILED,
                started_at=datetime.utcnow().isoformat(),
            )

        self.step_results[step.value].status = WorkflowStatus.FAILED
        self.step_results[step.value].completed_at = datetime.utcnow().isoformat()
        self.step_results[step.value].error_message = error_message

        self.status = WorkflowStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.utcnow().isoformat()

    def mark_completed(self) -> None:
        """Mark the entire workflow as completed."""
        self.status = WorkflowStatus.COMPLETED
        self.current_step = None
        self.updated_at = datetime.utcnow().isoformat()

    def mark_failed(self, error_message: str) -> None:
        """Mark the entire workflow as failed."""
        self.status = WorkflowStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.utcnow().isoformat()

    def is_step_completed(self, step: WorkflowStep) -> bool:
        """Check if a step has been completed."""
        return step in self.completed_steps

    def can_resume(self) -> bool:
        """Check if workflow can be resumed."""
        return self.status in (
            WorkflowStatus.IN_PROGRESS,
            WorkflowStatus.PAUSED,
            WorkflowStatus.FAILED,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert enums to strings
        data["status"] = self.status.value
        if self.current_step:
            data["current_step"] = self.current_step.value
        data["completed_steps"] = [step.value for step in self.completed_steps]

        # Convert step results
        step_results_dict = {}
        for key, result in self.step_results.items():
            step_results_dict[key] = {
                "step": result.step.value,
                "status": result.status.value,
                "started_at": result.started_at,
                "completed_at": result.completed_at,
                "error_message": result.error_message,
                "output_data": result.output_data,
            }
        data["step_results"] = step_results_dict

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowState":
        """Create WorkflowState from dictionary."""
        # Convert status
        data["status"] = WorkflowStatus(data["status"])

        # Convert current_step
        if data.get("current_step"):
            data["current_step"] = WorkflowStep(data["current_step"])

        # Convert completed_steps
        data["completed_steps"] = [
            WorkflowStep(step) for step in data.get("completed_steps", [])
        ]

        # Convert step_results
        step_results = {}
        for key, result_data in data.get("step_results", {}).items():
            step_results[key] = StepResult(
                step=WorkflowStep(result_data["step"]),
                status=WorkflowStatus(result_data["status"]),
                started_at=result_data["started_at"],
                completed_at=result_data.get("completed_at"),
                error_message=result_data.get("error_message"),
                output_data=result_data.get("output_data", {}),
            )
        data["step_results"] = step_results

        return cls(**data)

    def save_checkpoint(self, checkpoint_path: Path) -> None:
        """Save state to a checkpoint file."""
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        with open(checkpoint_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_checkpoint(cls, checkpoint_path: Path) -> "WorkflowState":
        """Load state from a checkpoint file."""
        with open(checkpoint_path, "r") as f:
            data = json.load(f)

        return cls.from_dict(data)
