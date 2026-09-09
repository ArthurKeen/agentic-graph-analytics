"""A failed GAE analysis must never be reported as a success.

Regression tests for a deceptive-success defect: engine cleanup ran
unconditionally after the retry loop and stamped ``CLEANING_UP`` over the
terminal ``FAILED`` status. Because ``_wait_for_completion`` treats
``CLEANING_UP`` as success ("finished, just releasing resources"), every hard
failure surfaced as ``success=True, error=None, result_count=0``. A FinReflectKG
demo run produced ten "No Results Generated" reports while printing
"Errors: 0", even though all ten analyses had failed at graph loading.
"""

from datetime import datetime

import pytest

from graph_analytics_ai.gae_orchestrator import (
    AnalysisConfig,
    AnalysisResult,
    AnalysisStatus,
    GAEOrchestrator,
)


def _failed_result() -> AnalysisResult:
    """An analysis that has already failed terminally."""
    config = AnalysisConfig(
        algorithm="pagerank",
        name="UC-S01: Central Financial Indicator Identification",
        vertex_collections=["Node"],
        edge_collections=["relations"],
    )
    return AnalysisResult(
        config=config,
        status=AnalysisStatus.FAILED,
        start_time=datetime.now(),
        error_message="Graph loading failed: job 2 not found after 15s.",
        engine_id="arangodb-gral-test1",
    )


class _StubGAE:
    """Minimal GAE stand-in; records the engine it was asked to delete."""

    def __init__(self):
        self.deleted = []

    def delete_engine(self, engine_id):
        self.deleted.append(engine_id)
        return {"status": "deleted"}


def test_cleanup_preserves_terminal_failure():
    """Cleanup must delete the engine WITHOUT clearing the FAILED status."""
    orchestrator = GAEOrchestrator.__new__(GAEOrchestrator)
    orchestrator.gae = _StubGAE()
    orchestrator._log = lambda *a, **k: None

    result = _failed_result()
    orchestrator._cleanup_engine(result)

    # Billing must still be stopped ...
    assert orchestrator.gae.deleted == ["arangodb-gral-test1"]
    # ... but the failure must survive.
    assert result.status is AnalysisStatus.FAILED
    assert result.error_message


def test_cleanup_still_marks_cleaning_up_on_success_path():
    """A non-failed analysis keeps the informational CLEANING_UP status."""
    orchestrator = GAEOrchestrator.__new__(GAEOrchestrator)
    orchestrator.gae = _StubGAE()
    orchestrator._log = lambda *a, **k: None

    result = _failed_result()
    result.status = AnalysisStatus.STORING_RESULTS
    result.error_message = None
    orchestrator._cleanup_engine(result)

    assert result.status is AnalysisStatus.CLEANING_UP


@pytest.mark.parametrize(
    "status",
    [AnalysisStatus.CLEANING_UP, AnalysisStatus.FAILED, AnalysisStatus.STORING_RESULTS],
)
def test_executor_treats_error_message_as_failure(status):
    """Any status carrying an error_message must not read as success.

    Defence in depth: even if some other code path clobbers the status again,
    an analysis holding an error_message must never be reported successful.
    """
    from graph_analytics_ai.ai.execution.executor import AnalysisExecutor

    executor = AnalysisExecutor.__new__(AnalysisExecutor)
    result = _failed_result()
    result.status = status
    executor._analysis_results = {"job-1": result}

    class _Job:
        job_id = "job-1"
        error_message = None
        execution_time_seconds = None

    job = _Job()
    assert executor._wait_for_completion(job) is False
    assert "not found" in job.error_message
