"""
Models for GAE analysis execution.

Defines data structures for job execution, monitoring, and results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class ExecutionStatus(Enum):
    """Status of analysis execution."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStatus(Enum):
    """GAE job status from API."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AnalysisJob:
    """
    Represents a GAE analysis job.

    Tracks job submission, monitoring, and results.
    """

    job_id: str
    """Unique job identifier from GAE."""

    template_name: str
    """Name of the template that was executed."""

    algorithm: str
    """Algorithm that was run."""

    status: ExecutionStatus
    """Current execution status."""

    submitted_at: datetime
    """When the job was submitted."""

    started_at: Optional[datetime] = None
    """When the job started running."""

    completed_at: Optional[datetime] = None
    """When the job completed."""

    error_message: Optional[str] = None
    """Error message if failed."""

    result_collection: Optional[str] = None
    """Collection where results are stored."""

    result_count: Optional[int] = None
    """Number of result records."""

    execution_time_seconds: Optional[float] = None
    """Actual execution time."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional job metadata."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "template_name": self.template_name,
            "algorithm": self.algorithm,
            "status": self.status.value,
            "submitted_at": (
                self.submitted_at.isoformat() if self.submitted_at else None
            ),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "error_message": self.error_message,
            "result_collection": self.result_collection,
            "result_count": self.result_count,
            "execution_time_seconds": self.execution_time_seconds,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionConfig:
    """Configuration for analysis execution."""

    poll_interval_seconds: float = 2.0
    """How often to poll for job status."""

    max_wait_seconds: float = 300.0
    """Maximum time to wait for job completion."""

    auto_collect_results: bool = True
    """Whether to automatically collect results after completion."""

    max_results_to_fetch: int = 1000
    """Maximum number of result records to fetch."""

    retry_on_failure: bool = True
    """Whether to retry failed jobs."""

    max_retries: int = 2
    """Maximum number of retries for failed jobs."""

    store_job_history: bool = True
    """Whether to store job execution history."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "poll_interval_seconds": self.poll_interval_seconds,
            "max_wait_seconds": self.max_wait_seconds,
            "auto_collect_results": self.auto_collect_results,
            "max_results_to_fetch": self.max_results_to_fetch,
            "retry_on_failure": self.retry_on_failure,
            "max_retries": self.max_retries,
            "store_job_history": self.store_job_history,
        }


@dataclass
class ExecutionResult:
    """
    Result of template execution.

    Contains job information, results, and execution metrics.
    """

    job: AnalysisJob
    """The executed job."""

    success: bool
    """Whether execution was successful."""

    results: List[Dict[str, Any]] = field(default_factory=list)
    """Analysis results (if collected)."""

    error: Optional[str] = None
    """Error message if failed."""

    warnings: List[str] = field(default_factory=list)
    """Execution warnings."""

    metrics: Dict[str, Any] = field(default_factory=dict)
    """Execution metrics."""

    def __bool__(self) -> bool:
        """Allow truth testing."""
        return self.success

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job": self.job.to_dict(),
            "success": self.success,
            "results": self.results,
            "error": self.error,
            "warnings": self.warnings,
            "metrics": self.metrics,
        }

    def get_top_results(
        self, n: int = 10, sort_by: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top N results.

        Args:
            n: Number of results to return
            sort_by: Key to sort by (if None, returns first n)

        Returns:
            Top n results
        """
        if not self.results:
            return []

        if sort_by and self.results:
            # Sort by specified key (descending)
            try:
                sorted_results = sorted(
                    self.results, key=lambda x: x.get(sort_by, 0), reverse=True
                )
                return sorted_results[:n]
            except:
                # If sorting fails, just return first n
                return self.results[:n]

        return self.results[:n]
