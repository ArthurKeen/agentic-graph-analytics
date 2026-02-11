"""
Main Analysis Catalog class.

Provides high-level API for tracking and querying analysis executions.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .storage.base import StorageBackend
from .models import (
    AnalysisExecution,
    AnalysisEpoch,
    ExtractedRequirements,
    GeneratedUseCase,
    AnalysisTemplate,
    ExecutionFilter,
    EpochFilter,
    ExecutionLineage,
    RequirementTrace,
    CatalogStatistics,
    EpochStatus,
    generate_epoch_id,
    current_timestamp,
)
from .exceptions import ValidationError, NotFoundError

logger = logging.getLogger(__name__)


class AnalysisCatalog:
    """
    Analysis Catalog - Track and manage analysis executions.

    This is the main entry point for catalog operations. It provides
    a high-level API on top of the storage backend.

    Example:
        >>> from graph_analytics_ai.catalog import AnalysisCatalog
        >>> from graph_analytics_ai.catalog.storage import ArangoDBStorage
        >>>
        >>> storage = ArangoDBStorage(db)
        >>> catalog = AnalysisCatalog(storage)
        >>>
        >>> # Create epoch
        >>> epoch = catalog.create_epoch("2026-01-analysis")
        >>>
        >>> # Track execution (typically done by workflow)
        >>> execution_id = catalog.track_execution(execution)
        >>>
        >>> # Query executions
        >>> executions = catalog.query_executions(
        ...     filter=ExecutionFilter(algorithm="pagerank")
        ... )
    """

    def __init__(self, storage: StorageBackend):
        """
        Initialize catalog.

        Args:
            storage: Storage backend (e.g., ArangoDBStorage)
        """
        self.storage = storage
        logger.info("AnalysisCatalog initialized")

    # --- Execution Tracking ---

    def track_execution(self, execution: AnalysisExecution) -> str:
        """
        Track an analysis execution.

        Args:
            execution: Execution record to track

        Returns:
            execution_id

        Raises:
            ValidationError: If execution data is invalid
            StorageError: If storage operation fails
        """
        self._validate_execution(execution)
        return self.storage.insert_execution(execution)

    async def track_execution_async(self, execution: AnalysisExecution) -> str:
        """Async version of track_execution."""
        self._validate_execution(execution)
        return await self.storage.insert_execution_async(execution)

    def get_execution(self, execution_id: str) -> AnalysisExecution:
        """
        Get execution by ID.

        Args:
            execution_id: Execution ID

        Returns:
            AnalysisExecution

        Raises:
            NotFoundError: If execution not found
        """
        return self.storage.get_execution(execution_id)

    def query_executions(
        self,
        filter: Optional[ExecutionFilter] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AnalysisExecution]:
        """
        Query executions with optional filters.

        Args:
            filter: Filter criteria
            limit: Max results to return (default: 100)
            offset: Offset for pagination (default: 0)

        Returns:
            List of matching executions

        Example:
            >>> # Get all PageRank executions from January
            >>> executions = catalog.query_executions(
            ...     filter=ExecutionFilter(
            ...         algorithm="pagerank",
            ...         start_date=datetime(2026, 1, 1),
            ...         end_date=datetime(2026, 2, 1)
            ...     )
            ... )
        """
        return self.storage.query_executions(filter, limit, offset)

    def delete_execution(self, execution_id: str) -> None:
        """
        Delete execution by ID.

        Args:
            execution_id: Execution ID to delete
        """
        self.storage.delete_execution(execution_id)
        logger.info(f"Deleted execution: {execution_id}")

    # --- Epoch Management ---

    def create_epoch(
        self,
        name: str,
        description: str = "",
        timestamp: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AnalysisEpoch:
        """
        Create a new analysis epoch.

        Epochs group related analyses for time-series analysis.

        Args:
            name: Unique epoch name (e.g., "2026-01-baseline")
            description: Description of this epoch
            timestamp: Epoch timestamp (defaults to now)
            tags: Tags for categorization (e.g., ["production", "monthly"])
            metadata: Additional metadata

        Returns:
            Created AnalysisEpoch

        Raises:
            DuplicateError: If epoch name already exists

        Example:
            >>> epoch = catalog.create_epoch(
            ...     name="2026-01-baseline",
            ...     description="January baseline analysis",
            ...     tags=["production", "monthly"]
            ... )
        """
        if not name or not name.strip():
            raise ValidationError("Epoch name cannot be empty")

        # Check if name already exists
        existing = self.storage.get_epoch_by_name(name)
        if existing:
            raise ValidationError(f"Epoch with name '{name}' already exists")

        epoch = AnalysisEpoch(
            epoch_id=generate_epoch_id(),
            name=name,
            description=description,
            timestamp=timestamp or current_timestamp(),
            created_at=current_timestamp(),
            status=EpochStatus.ACTIVE,
            tags=tags or [],
            metadata=metadata or {},
        )

        self.storage.insert_epoch(epoch)
        logger.info(f"Created epoch: {name} ({epoch.epoch_id})")
        return epoch

    async def create_epoch_async(
        self,
        name: str,
        description: str = "",
        timestamp: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AnalysisEpoch:
        """Async version of create_epoch."""
        if not name or not name.strip():
            raise ValidationError("Epoch name cannot be empty")

        existing = self.storage.get_epoch_by_name(name)
        if existing:
            raise ValidationError(f"Epoch with name '{name}' already exists")

        epoch = AnalysisEpoch(
            epoch_id=generate_epoch_id(),
            name=name,
            description=description,
            timestamp=timestamp or current_timestamp(),
            created_at=current_timestamp(),
            status=EpochStatus.ACTIVE,
            tags=tags or [],
            metadata=metadata or {},
        )

        await self.storage.insert_epoch_async(epoch)
        logger.info(f"Created epoch: {name} ({epoch.epoch_id})")
        return epoch

    def get_epoch(self, epoch_id: str) -> AnalysisEpoch:
        """Get epoch by ID."""
        return self.storage.get_epoch(epoch_id)

    def get_epoch_by_name(self, name: str) -> Optional[AnalysisEpoch]:
        """Get epoch by unique name."""
        return self.storage.get_epoch_by_name(name)

    def query_epochs(
        self,
        filter: Optional[EpochFilter] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AnalysisEpoch]:
        """Query epochs with optional filters."""
        return self.storage.query_epochs(filter, limit, offset)

    def delete_epoch(self, epoch_id: str, cascade: bool = False) -> None:
        """
        Delete epoch by ID.

        Args:
            epoch_id: Epoch ID to delete
            cascade: If True, also delete all executions in this epoch
        """
        self.storage.delete_epoch(epoch_id, cascade)
        logger.info(f"Deleted epoch: {epoch_id} (cascade={cascade})")

    # --- Lineage Tracking ---

    def track_requirements(self, requirements: ExtractedRequirements) -> str:
        """
        Track extracted requirements.

        Used by agentic workflows to track lineage.
        Accepts both catalog.models.ExtractedRequirements and
        ai.documents.models.ExtractedRequirements (converted automatically).

        Args:
            requirements: Extracted requirements

        Returns:
            requirements_id
        """
        from .adapters import adapt_requirements, _is_workflow_requirements

        if _is_workflow_requirements(requirements):
            requirements = adapt_requirements(requirements)
        return self.storage.insert_requirements(requirements)

    async def track_requirements_async(
        self, requirements: ExtractedRequirements
    ) -> str:
        """Async version of track_requirements."""
        from .adapters import adapt_requirements, _is_workflow_requirements

        if _is_workflow_requirements(requirements):
            requirements = adapt_requirements(requirements)
        return await self.storage.insert_requirements_async(requirements)

    def track_use_case(self, use_case: GeneratedUseCase) -> str:
        """
        Track generated use case.

        Accepts both catalog.models.GeneratedUseCase and
        ai.generation.models.UseCase (converted automatically).

        Args:
            use_case: Generated use case

        Returns:
            use_case_id
        """
        from .adapters import adapt_use_case, _is_workflow_use_case

        if _is_workflow_use_case(use_case):
            use_case = adapt_use_case(use_case)
        return self.storage.insert_use_case(use_case)

    async def track_use_case_async(self, use_case: GeneratedUseCase) -> str:
        """Async version of track_use_case."""
        from .adapters import adapt_use_case, _is_workflow_use_case

        if _is_workflow_use_case(use_case):
            use_case = adapt_use_case(use_case)
        return await self.storage.insert_use_case_async(use_case)

    def track_template(self, template: AnalysisTemplate) -> str:
        """
        Track analysis template.

        Accepts both catalog.models.AnalysisTemplate and
        ai.templates.models.AnalysisTemplate (converted automatically).

        Args:
            template: Analysis template

        Returns:
            template_id
        """
        from .adapters import adapt_template, _is_workflow_template

        if _is_workflow_template(template):
            template = adapt_template(
                template,
                use_case_id=getattr(template, "use_case_id", None),
            )
        return self.storage.insert_template(template)

    async def track_template_async(self, template: AnalysisTemplate) -> str:
        """Async version of track_template."""
        from .adapters import adapt_template, _is_workflow_template

        if _is_workflow_template(template):
            template = adapt_template(
                template,
                use_case_id=getattr(template, "use_case_id", None),
            )
        return await self.storage.insert_template_async(template)

    def get_execution_lineage(self, execution_id: str) -> ExecutionLineage:
        """
        Get complete lineage for an execution.

        Traces from execution back to requirements.

        Args:
            execution_id: Execution ID

        Returns:
            ExecutionLineage with all linked entities

        Example:
            >>> lineage = catalog.get_execution_lineage(exec_id)
            >>> print(lineage.requirements.summary)
            >>> print(lineage.use_case.title)
            >>> print(lineage.template.name)
        """
        execution = self.storage.get_execution(execution_id)

        # Fetch linked entities
        template = None
        use_case = None
        requirements = None
        epoch = None

        try:
            if execution.template_id:
                template = self.storage.get_template(execution.template_id)
        except NotFoundError:
            pass

        try:
            if execution.use_case_id:
                use_case = self.storage.get_use_case(execution.use_case_id)
        except NotFoundError:
            pass

        try:
            if execution.requirements_id:
                requirements = self.storage.get_requirements(execution.requirements_id)
        except NotFoundError:
            pass

        try:
            if execution.epoch_id:
                epoch = self.storage.get_epoch(execution.epoch_id)
        except NotFoundError:
            pass

        return ExecutionLineage(
            execution=execution,
            template=template,
            use_case=use_case,
            requirements=requirements,
            epoch=epoch,
        )

    def trace_requirement(self, requirement_id: str) -> RequirementTrace:
        """
        Trace a requirement through the pipeline.

        Shows all use cases, templates, and executions derived
        from a specific requirement.

        Args:
            requirement_id: Requirements ID

        Returns:
            RequirementTrace showing all derived entities
        """
        requirements = self.storage.get_requirements(requirement_id)
        use_cases = self.storage.query_use_cases_by_requirements(requirement_id)

        templates = []
        executions = []

        for use_case in use_cases:
            case_templates = self.storage.query_templates_by_use_case(
                use_case.use_case_id
            )
            templates.extend(case_templates)

        for template in templates:
            template_execs = self.storage.query_executions(
                filter=ExecutionFilter(requirements_id=requirement_id),
                limit=1000,
            )
            executions.extend(template_execs)

        return RequirementTrace(
            requirement_id=requirement_id,
            requirements=requirements,
            use_cases=use_cases,
            templates=templates,
            executions=executions,
        )

    # --- Management Operations ---

    def reset(self, confirm: bool = False) -> None:
        """
        Delete all catalog data.

        WARNING: This is destructive and cannot be undone!

        Args:
            confirm: Must be True to actually reset
        """
        self.storage.reset(confirm=confirm)

    def export_catalog(self, output_path: str) -> None:
        """
        Export entire catalog to JSON file.

        Args:
            output_path: Path to output file
        """
        self.storage.export_catalog(output_path)
        logger.info(f"Exported catalog to: {output_path}")

    def import_catalog(self, input_path: str) -> None:
        """
        Import catalog from JSON file.

        Args:
            input_path: Path to input file
        """
        self.storage.import_catalog(input_path)
        logger.info(f"Imported catalog from: {input_path}")

    def get_statistics(self) -> CatalogStatistics:
        """
        Get catalog statistics.

        Returns:
            CatalogStatistics with counts and breakdowns
        """
        stats_dict = self.storage.get_statistics()

        return CatalogStatistics(
            total_executions=stats_dict.get("total_executions", 0),
            total_epochs=stats_dict.get("total_epochs", 0),
            earliest_execution=None,  # TODO: Implement
            latest_execution=None,  # TODO: Implement
            algorithms_used=list(
                stats_dict.get("execution_count_by_algorithm", {}).keys()
            ),
            execution_count_by_algorithm=stats_dict.get(
                "execution_count_by_algorithm", {}
            ),
            execution_count_by_status=stats_dict.get("execution_count_by_status", {}),
            total_execution_time_hours=0.0,  # TODO: Implement
            total_cost_usd=0.0,  # TODO: Implement
        )

    # --- Validation ---

    def _validate_execution(self, execution: AnalysisExecution) -> None:
        """Validate execution before storage."""
        if not execution.execution_id:
            raise ValidationError("execution_id is required")
        if not execution.algorithm:
            raise ValidationError("algorithm is required")
        if not execution.template_id:
            raise ValidationError("template_id is required")
        if not execution.results_location:
            raise ValidationError("results_location is required")

    def close(self) -> None:
        """Close catalog and cleanup resources."""
        self.storage.close()
        logger.info("AnalysisCatalog closed")
