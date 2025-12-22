"""
Tests for workflow state management.
"""

import json
from datetime import datetime


from graph_analytics_ai.ai.workflow.state import (
    WorkflowState,
    WorkflowStatus,
    WorkflowStep,
    StepResult,
)


class TestWorkflowState:
    """Test workflow state management."""

    def test_create_state(self):
        """Test creating a new workflow state."""
        state = WorkflowState(
            workflow_id="test-123",
            status=WorkflowStatus.NOT_STARTED,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        assert state.workflow_id == "test-123"
        assert state.status == WorkflowStatus.NOT_STARTED
        assert state.current_step is None
        assert len(state.completed_steps) == 0

    def test_mark_step_started(self):
        """Test marking a step as started."""
        state = WorkflowState(
            workflow_id="test-123",
            status=WorkflowStatus.NOT_STARTED,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        state.mark_step_started(WorkflowStep.PARSE_DOCUMENTS)

        assert state.status == WorkflowStatus.IN_PROGRESS
        assert state.current_step == WorkflowStep.PARSE_DOCUMENTS
        assert WorkflowStep.PARSE_DOCUMENTS.value in state.step_results
        assert (
            state.step_results[WorkflowStep.PARSE_DOCUMENTS.value].status
            == WorkflowStatus.IN_PROGRESS
        )

    def test_mark_step_completed(self):
        """Test marking a step as completed."""
        state = WorkflowState(
            workflow_id="test-123",
            status=WorkflowStatus.NOT_STARTED,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        state.mark_step_started(WorkflowStep.PARSE_DOCUMENTS)
        state.mark_step_completed(WorkflowStep.PARSE_DOCUMENTS, {"count": 5})

        assert state.current_step is None
        assert WorkflowStep.PARSE_DOCUMENTS in state.completed_steps
        assert (
            state.step_results[WorkflowStep.PARSE_DOCUMENTS.value].status
            == WorkflowStatus.COMPLETED
        )
        assert state.step_results[WorkflowStep.PARSE_DOCUMENTS.value].output_data == {
            "count": 5
        }

    def test_mark_step_failed(self):
        """Test marking a step as failed."""
        state = WorkflowState(
            workflow_id="test-123",
            status=WorkflowStatus.NOT_STARTED,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        state.mark_step_started(WorkflowStep.PARSE_DOCUMENTS)
        state.mark_step_failed(WorkflowStep.PARSE_DOCUMENTS, "File not found")

        assert state.status == WorkflowStatus.FAILED
        assert state.error_message == "File not found"
        assert (
            state.step_results[WorkflowStep.PARSE_DOCUMENTS.value].status
            == WorkflowStatus.FAILED
        )
        assert (
            state.step_results[WorkflowStep.PARSE_DOCUMENTS.value].error_message
            == "File not found"
        )

    def test_mark_completed(self):
        """Test marking workflow as completed."""
        state = WorkflowState(
            workflow_id="test-123",
            status=WorkflowStatus.IN_PROGRESS,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        state.mark_completed()

        assert state.status == WorkflowStatus.COMPLETED
        assert state.current_step is None

    def test_is_step_completed(self):
        """Test checking if step is completed."""
        state = WorkflowState(
            workflow_id="test-123",
            status=WorkflowStatus.NOT_STARTED,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        assert not state.is_step_completed(WorkflowStep.PARSE_DOCUMENTS)

        state.mark_step_started(WorkflowStep.PARSE_DOCUMENTS)
        state.mark_step_completed(WorkflowStep.PARSE_DOCUMENTS)

        assert state.is_step_completed(WorkflowStep.PARSE_DOCUMENTS)

    def test_can_resume(self):
        """Test checking if workflow can be resumed."""
        state = WorkflowState(
            workflow_id="test-123",
            status=WorkflowStatus.NOT_STARTED,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        assert not state.can_resume()

        state.status = WorkflowStatus.IN_PROGRESS
        assert state.can_resume()

        state.status = WorkflowStatus.PAUSED
        assert state.can_resume()

        state.status = WorkflowStatus.FAILED
        assert state.can_resume()

        state.status = WorkflowStatus.COMPLETED
        assert not state.can_resume()

    def test_to_dict(self):
        """Test converting state to dictionary."""
        state = WorkflowState(
            workflow_id="test-123",
            status=WorkflowStatus.IN_PROGRESS,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )

        state.mark_step_started(WorkflowStep.PARSE_DOCUMENTS)
        state.mark_step_completed(WorkflowStep.PARSE_DOCUMENTS)

        data = state.to_dict()

        assert data["workflow_id"] == "test-123"
        assert data["status"] == "in_progress"
        assert WorkflowStep.PARSE_DOCUMENTS.value in [
            s for s in data["completed_steps"]
        ]
        assert WorkflowStep.PARSE_DOCUMENTS.value in data["step_results"]

    def test_from_dict(self):
        """Test creating state from dictionary."""
        data = {
            "workflow_id": "test-123",
            "status": "in_progress",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "current_step": "parse_documents",
            "completed_steps": [],
            "step_results": {
                "parse_documents": {
                    "step": "parse_documents",
                    "status": "in_progress",
                    "started_at": "2025-01-01T00:00:00",
                    "completed_at": None,
                    "error_message": None,
                    "output_data": {},
                }
            },
            "error_message": None,
            "inputs": {},
            "outputs": {},
            "metadata": {},
        }

        state = WorkflowState.from_dict(data)

        assert state.workflow_id == "test-123"
        assert state.status == WorkflowStatus.IN_PROGRESS
        assert state.current_step == WorkflowStep.PARSE_DOCUMENTS
        assert WorkflowStep.PARSE_DOCUMENTS.value in state.step_results

    def test_save_checkpoint(self, tmp_path):
        """Test saving state to checkpoint file."""
        state = WorkflowState(
            workflow_id="test-123",
            status=WorkflowStatus.IN_PROGRESS,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        checkpoint_path = tmp_path / "checkpoint.json"
        state.save_checkpoint(checkpoint_path)

        assert checkpoint_path.exists()

        # Verify JSON is valid
        with open(checkpoint_path) as f:
            data = json.load(f)
            assert data["workflow_id"] == "test-123"

    def test_load_checkpoint(self, tmp_path):
        """Test loading state from checkpoint file."""
        state = WorkflowState(
            workflow_id="test-123",
            status=WorkflowStatus.IN_PROGRESS,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        state.mark_step_started(WorkflowStep.PARSE_DOCUMENTS)
        state.mark_step_completed(WorkflowStep.PARSE_DOCUMENTS)

        checkpoint_path = tmp_path / "checkpoint.json"
        state.save_checkpoint(checkpoint_path)

        loaded_state = WorkflowState.load_checkpoint(checkpoint_path)

        assert loaded_state.workflow_id == state.workflow_id
        assert loaded_state.status == state.status
        assert len(loaded_state.completed_steps) == len(state.completed_steps)
        assert loaded_state.is_step_completed(WorkflowStep.PARSE_DOCUMENTS)


class TestStepResult:
    """Test step result data structure."""

    def test_create_step_result(self):
        """Test creating a step result."""
        result = StepResult(
            step=WorkflowStep.PARSE_DOCUMENTS,
            status=WorkflowStatus.COMPLETED,
            started_at="2025-01-01T00:00:00",
            completed_at="2025-01-01T00:01:00",
        )

        assert result.step == WorkflowStep.PARSE_DOCUMENTS
        assert result.status == WorkflowStatus.COMPLETED
        assert result.error_message is None
