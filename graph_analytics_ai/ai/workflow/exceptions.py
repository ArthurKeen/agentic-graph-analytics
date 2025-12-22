"""
Workflow-specific exceptions.
"""


class WorkflowError(Exception):
    """Base exception for all workflow errors."""

    pass


class WorkflowStepError(WorkflowError):
    """Raised when a workflow step fails."""

    def __init__(self, step_name: str, message: str, original_error: Exception = None):
        self.step_name = step_name
        self.original_error = original_error
        super().__init__(f"Step '{step_name}' failed: {message}")


class WorkflowStateError(WorkflowError):
    """Raised when workflow state is invalid or corrupted."""

    pass


class WorkflowCheckpointError(WorkflowError):
    """Raised when checkpoint save/load fails."""

    pass
