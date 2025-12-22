"""
Execution metrics models for tracking performance, timing, and costs.

These models capture detailed metrics from GAE execution for reporting
and analysis purposes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass
class TimingBreakdown:
    """
    Breakdown of execution timing by phase.

    Captures time spent in each phase of GAE execution.
    """

    graph_load_seconds: float = 0.0
    """Time spent loading graph into GAE."""

    algorithm_execution_seconds: float = 0.0
    """Time spent executing algorithm."""

    results_store_seconds: float = 0.0
    """Time spent storing results back to database."""

    total_seconds: float = 0.0
    """Total execution time."""

    @property
    def load_percentage(self) -> float:
        """Percentage of time spent loading graph."""
        return (
            (self.graph_load_seconds / self.total_seconds * 100)
            if self.total_seconds > 0
            else 0.0
        )

    @property
    def execution_percentage(self) -> float:
        """Percentage of time spent in algorithm execution."""
        return (
            (self.algorithm_execution_seconds / self.total_seconds * 100)
            if self.total_seconds > 0
            else 0.0
        )

    @property
    def storage_percentage(self) -> float:
        """Percentage of time spent storing results."""
        return (
            (self.results_store_seconds / self.total_seconds * 100)
            if self.total_seconds > 0
            else 0.0
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "graph_load_seconds": self.graph_load_seconds,
            "algorithm_execution_seconds": self.algorithm_execution_seconds,
            "results_store_seconds": self.results_store_seconds,
            "total_seconds": self.total_seconds,
            "load_percentage": self.load_percentage,
            "execution_percentage": self.execution_percentage,
            "storage_percentage": self.storage_percentage,
        }


@dataclass
class CostBreakdown:
    """
    Breakdown of execution costs (AMP only).

    Tracks deployment, runtime, and total costs.
    """

    engine_deployment_cost_usd: float = 0.0
    """Cost of engine deployment."""

    runtime_cost_usd: float = 0.0
    """Cost of engine runtime."""

    storage_cost_usd: float = 0.0
    """Cost of data storage (if applicable)."""

    total_cost_usd: float = 0.0
    """Total estimated cost."""

    runtime_minutes: float = 0.0
    """Total runtime in minutes."""

    engine_size: Optional[str] = None
    """Engine size used."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "engine_deployment_cost_usd": self.engine_deployment_cost_usd,
            "runtime_cost_usd": self.runtime_cost_usd,
            "storage_cost_usd": self.storage_cost_usd,
            "total_cost_usd": self.total_cost_usd,
            "runtime_minutes": self.runtime_minutes,
            "engine_size": self.engine_size,
        }


@dataclass
class AlgorithmExecutionStats:
    """
    Statistics for a single algorithm execution.

    Captures metrics specific to one algorithm run.
    """

    algorithm: str
    """Algorithm name."""

    job_id: Optional[str] = None
    """GAE job ID."""

    execution_time_seconds: float = 0.0
    """Algorithm execution time."""

    vertex_count: int = 0
    """Number of vertices processed."""

    edge_count: int = 0
    """Number of edges processed."""

    results_count: int = 0
    """Number of results generated."""

    status: str = "completed"
    """Execution status."""

    error_message: Optional[str] = None
    """Error message if failed."""

    retry_count: int = 0
    """Number of retry attempts."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "algorithm": self.algorithm,
            "job_id": self.job_id,
            "execution_time_seconds": self.execution_time_seconds,
            "vertex_count": self.vertex_count,
            "edge_count": self.edge_count,
            "results_count": self.results_count,
            "status": self.status,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
        }


@dataclass
class ExecutionSummary:
    """
    Comprehensive summary of execution metrics.

    Aggregates all execution data for reporting and analysis.
    """

    workflow_id: str
    """Unique workflow identifier."""

    started_at: datetime
    """When execution started."""

    completed_at: Optional[datetime] = None
    """When execution completed."""

    templates_generated: int = 0
    """Number of templates generated."""

    templates_executed: int = 0
    """Number of templates actually executed."""

    templates_succeeded: int = 0
    """Number of successful executions."""

    templates_failed: int = 0
    """Number of failed executions."""

    total_execution_time_seconds: float = 0.0
    """Total execution time across all algorithms."""

    timing_breakdown: Optional[TimingBreakdown] = None
    """Detailed timing breakdown."""

    cost_breakdown: Optional[CostBreakdown] = None
    """Cost breakdown (AMP only)."""

    algorithm_stats: Dict[str, AlgorithmExecutionStats] = field(default_factory=dict)
    """Per-algorithm execution statistics."""

    total_vertices_processed: int = 0
    """Total vertices across all executions."""

    total_edges_processed: int = 0
    """Total edges across all executions."""

    total_results_generated: int = 0
    """Total results across all executions."""

    engine_size: Optional[str] = None
    """Engine size used."""

    deployment_mode: Optional[str] = None
    """Deployment mode (AMP or self-managed)."""

    errors: List[str] = field(default_factory=list)
    """List of errors encountered."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.templates_executed == 0:
            return 0.0
        return (self.templates_succeeded / self.templates_executed) * 100

    @property
    def total_duration_seconds(self) -> float:
        """Calculate total duration."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "templates_generated": self.templates_generated,
            "templates_executed": self.templates_executed,
            "templates_succeeded": self.templates_succeeded,
            "templates_failed": self.templates_failed,
            "success_rate": self.success_rate,
            "total_execution_time_seconds": self.total_execution_time_seconds,
            "total_duration_seconds": self.total_duration_seconds,
            "timing_breakdown": (
                self.timing_breakdown.to_dict() if self.timing_breakdown else None
            ),
            "cost_breakdown": (
                self.cost_breakdown.to_dict() if self.cost_breakdown else None
            ),
            "algorithm_stats": {
                k: v.to_dict() for k, v in self.algorithm_stats.items()
            },
            "total_vertices_processed": self.total_vertices_processed,
            "total_edges_processed": self.total_edges_processed,
            "total_results_generated": self.total_results_generated,
            "engine_size": self.engine_size,
            "deployment_mode": self.deployment_mode,
            "errors": self.errors,
            "metadata": self.metadata,
        }

    def add_algorithm_stats(self, stats: AlgorithmExecutionStats):
        """Add statistics for an algorithm execution."""
        self.algorithm_stats[stats.algorithm] = stats
        self.total_execution_time_seconds += stats.execution_time_seconds
        self.total_vertices_processed += stats.vertex_count
        self.total_edges_processed += stats.edge_count
        self.total_results_generated += stats.results_count

        if stats.status == "completed":
            self.templates_succeeded += 1
        else:
            self.templates_failed += 1
            if stats.error_message:
                self.errors.append(f"{stats.algorithm}: {stats.error_message}")
