"""
GAE Analysis Execution Module

Executes GAE analysis templates on ArangoDB clusters (AMP or self-managed).
Provides job monitoring, result collection, and error handling.
"""

from .executor import AnalysisExecutor, ExecutionResult
from .models import (
    ExecutionStatus,
    JobStatus,
    AnalysisJob,
    ExecutionConfig
)

__all__ = [
    "AnalysisExecutor",
    "ExecutionResult",
    "ExecutionStatus",
    "JobStatus",
    "AnalysisJob",
    "ExecutionConfig",
]

