"""Tests for execution models."""

from graph_analytics_ai.ai.execution.models import ExecutionStatus, JobStatus


class TestExecutionStatus:
    """Tests for ExecutionStatus enum."""

    def test_execution_statuses_exist(self):
        """Test that all expected execution statuses exist."""
        assert ExecutionStatus.PENDING.value == "pending"
        assert ExecutionStatus.SUBMITTED.value == "submitted"
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.COMPLETED.value == "completed"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.CANCELLED.value == "cancelled"


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_job_statuses_exist(self):
        """Test that all expected job statuses exist."""
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.DONE.value == "done"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"


class TestExecutionModels:
    """Basic tests for execution models."""

    def test_import_analysis_job(self):
        """Test that AnalysisJob can be imported."""
        from graph_analytics_ai.ai.execution.models import AnalysisJob

        assert AnalysisJob is not None

    def test_import_execution_result(self):
        """Test that ExecutionResult can be imported."""
        from graph_analytics_ai.ai.execution.models import ExecutionResult

        assert ExecutionResult is not None

    def test_import_execution_config(self):
        """Test that ExecutionConfig can be imported."""
        from graph_analytics_ai.ai.execution.models import ExecutionConfig

        assert ExecutionConfig is not None
