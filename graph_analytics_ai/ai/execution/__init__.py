"""
GAE Analysis Execution Module

Executes GAE analysis templates on ArangoDB clusters (AMP or self-managed).
Provides job monitoring, result collection, error handling, and execution metrics.
"""

from .executor import AnalysisExecutor, ExecutionResult
from .models import ExecutionStatus, JobStatus, AnalysisJob, ExecutionConfig
from .metrics import (
    ExecutionSummary,
    TimingBreakdown,
    CostBreakdown,
    AlgorithmExecutionStats,
)

__all__ = [
    "AnalysisExecutor",
    "ExecutionResult",
    "ExecutionStatus",
    "JobStatus",
    "AnalysisJob",
    "ExecutionConfig",
    "ExecutionSummary",
    "TimingBreakdown",
    "CostBreakdown",
    "AlgorithmExecutionStats",
]
