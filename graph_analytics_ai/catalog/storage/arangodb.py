"""
ArangoDB storage backend implementation.

Provides persistent storage for the Analysis Catalog using ArangoDB.
"""

import asyncio
import json
import logging
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional, Any

from arango.database import StandardDatabase
from arango.exceptions import DocumentInsertError, DocumentGetError, DocumentUpdateError

from .base import StorageBackend
from ..models import (
    AnalysisExecution,
    AnalysisEpoch,
    ExtractedRequirements,
    GeneratedUseCase,
    AnalysisTemplate,
    ExecutionFilter,
    EpochFilter,
)
from ..exceptions import (
    StorageError,
    NotFoundError,
    DuplicateError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class ArangoDBStorage(StorageBackend):
    """
    ArangoDB implementation of catalog storage.

    Stores catalog data in the same ArangoDB instance as the graph data,
    using separate collections with '_analysis_' prefix.

    Collections:
        _analysis_executions: Execution records
        _analysis_epochs: Epoch records
        _analysis_requirements: Requirements records
        _analysis_use_cases: Use case records
        _analysis_templates: Template records
    """

    # Collection names (without leading underscore to avoid system collection conflict)
    EXECUTIONS_COLLECTION = "analysis_executions"
    EPOCHS_COLLECTION = "analysis_epochs"
    REQUIREMENTS_COLLECTION = "analysis_requirements"
    USE_CASES_COLLECTION = "analysis_use_cases"
    TEMPLATES_COLLECTION = "analysis_templates"

    def __init__(
        self,
        db: StandardDatabase,
        auto_initialize: bool = True,
    ):
        """
        Initialize ArangoDB storage.

        Args:
            db: ArangoDB database instance
            auto_initialize: If True, create collections on init
        """
        self.db = db
        self._lock = Lock()  # Thread-safety for concurrent operations
        self._async_lock = asyncio.Lock()  # Async lock

        if auto_initialize:
            self.initialize_collections()

    def initialize_collections(self) -> None:
        """
        Create all required collections and indexes.

        This is safe to call multiple times (idempotent).
        """
        try:
            logger.info("Initializing catalog collections...")

            # Create collections if they don't exist
            collections = [
                self.EXECUTIONS_COLLECTION,
                self.EPOCHS_COLLECTION,
                self.REQUIREMENTS_COLLECTION,
                self.USE_CASES_COLLECTION,
                self.TEMPLATES_COLLECTION,
            ]

            for collection_name in collections:
                if not self.db.has_collection(collection_name):
                    self.db.create_collection(collection_name)
                    logger.info(f"Created collection: {collection_name}")
                else:
                    logger.debug(f"Collection exists: {collection_name}")

            # Create indexes for efficient queries
            self._create_indexes()

            logger.info("Catalog collections initialized successfully")

        except Exception as e:
            raise StorageError(f"Failed to initialize collections: {e}") from e

    def _create_indexes(self) -> None:
        """Create indexes for efficient queries."""
        try:
            executions = self.db.collection(self.EXECUTIONS_COLLECTION)

            # Timestamp for time-series queries
            executions.add_skiplist_index(fields=["timestamp"], unique=False)

            # Algorithm and epoch for filtering
            executions.add_hash_index(fields=["algorithm"], unique=False)
            executions.add_hash_index(fields=["epoch_id"], unique=False)
            executions.add_hash_index(fields=["status"], unique=False)

            # Lineage foreign keys
            executions.add_hash_index(fields=["requirements_id"], unique=False)
            executions.add_hash_index(fields=["use_case_id"], unique=False)
            executions.add_hash_index(fields=["template_id"], unique=False)

            # Composite index for common query patterns
            executions.add_skiplist_index(
                fields=["algorithm", "timestamp"], unique=False
            )

            # Epochs
            epochs = self.db.collection(self.EPOCHS_COLLECTION)
            epochs.add_hash_index(fields=["name"], unique=True)  # Unique names
            epochs.add_skiplist_index(fields=["timestamp"], unique=False)
            epochs.add_hash_index(fields=["status"], unique=False)

            # Requirements
            requirements = self.db.collection(self.REQUIREMENTS_COLLECTION)
            requirements.add_hash_index(fields=["epoch_id"], unique=False)

            # Use Cases
            use_cases = self.db.collection(self.USE_CASES_COLLECTION)
            use_cases.add_hash_index(fields=["requirements_id"], unique=False)
            use_cases.add_hash_index(fields=["epoch_id"], unique=False)

            # Templates
            templates = self.db.collection(self.TEMPLATES_COLLECTION)
            templates.add_hash_index(fields=["use_case_id"], unique=False)
            templates.add_hash_index(fields=["requirements_id"], unique=False)
            templates.add_hash_index(fields=["epoch_id"], unique=False)

            logger.info("Created indexes for catalog collections")

        except Exception as e:
            logger.warning(f"Failed to create some indexes: {e}")
            # Don't fail initialization if index creation fails

    # --- Execution Operations ---

    def insert_execution(self, execution: AnalysisExecution) -> str:
        """Insert execution record."""
        with self._lock:
            try:
                collection = self.db.collection(self.EXECUTIONS_COLLECTION)
                doc = execution.to_dict()
                collection.insert(doc)
                logger.debug(f"Inserted execution: {execution.execution_id}")
                return execution.execution_id
            except DocumentInsertError as e:
                if "unique constraint violated" in str(e).lower():
                    raise DuplicateError(
                        f"Execution {execution.execution_id} already exists"
                    ) from e
                raise StorageError(f"Failed to insert execution: {e}") from e
            except Exception as e:
                raise StorageError(f"Failed to insert execution: {e}") from e

    async def insert_execution_async(self, execution: AnalysisExecution) -> str:
        """Async version of insert_execution."""
        async with self._async_lock:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.insert_execution, execution)

    def get_execution(self, execution_id: str) -> AnalysisExecution:
        """Get execution by ID."""
        try:
            collection = self.db.collection(self.EXECUTIONS_COLLECTION)
            doc = collection.get(execution_id)
            if not doc:
                raise NotFoundError(f"Execution not found: {execution_id}")
            return AnalysisExecution.from_dict(doc)
        except DocumentGetError as e:
            raise NotFoundError(f"Execution not found: {execution_id}") from e
        except NotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to get execution: {e}") from e

    def query_executions(
        self,
        filter: Optional[ExecutionFilter] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AnalysisExecution]:
        """Query executions with filters."""
        try:
            # Build AQL query
            query_parts = [f"FOR doc IN {self.EXECUTIONS_COLLECTION}"]
            bind_vars = {"limit": limit, "offset": offset}

            if filter:
                conditions = []

                if filter.epoch_id:
                    conditions.append("doc.epoch_id == @epoch_id")
                    bind_vars["epoch_id"] = filter.epoch_id

                if filter.algorithm:
                    conditions.append("doc.algorithm == @algorithm")
                    bind_vars["algorithm"] = filter.algorithm

                if filter.status:
                    conditions.append("doc.status == @status")
                    bind_vars["status"] = filter.status.value

                if filter.start_date:
                    conditions.append("doc.timestamp >= @start_date")
                    bind_vars["start_date"] = filter.start_date.isoformat()

                if filter.end_date:
                    conditions.append("doc.timestamp <= @end_date")
                    bind_vars["end_date"] = filter.end_date.isoformat()

                if filter.graph_name:
                    conditions.append("doc.graph_config.graph_name == @graph_name")
                    bind_vars["graph_name"] = filter.graph_name

                if filter.requirements_id:
                    conditions.append("doc.requirements_id == @requirements_id")
                    bind_vars["requirements_id"] = filter.requirements_id

                if filter.use_case_id:
                    conditions.append("doc.use_case_id == @use_case_id")
                    bind_vars["use_case_id"] = filter.use_case_id

                if filter.workflow_mode:
                    conditions.append("doc.workflow_mode == @workflow_mode")
                    bind_vars["workflow_mode"] = filter.workflow_mode

                if filter.min_result_count is not None:
                    conditions.append("doc.result_count >= @min_result_count")
                    bind_vars["min_result_count"] = filter.min_result_count

                if filter.max_execution_time is not None:
                    conditions.append(
                        "doc.performance_metrics.execution_time_seconds <= @max_execution_time"
                    )
                    bind_vars["max_execution_time"] = filter.max_execution_time

                if conditions:
                    query_parts.append("FILTER " + " AND ".join(conditions))

            # Sort by timestamp descending (most recent first)
            query_parts.append("SORT doc.timestamp DESC")

            # Pagination
            query_parts.append("LIMIT @offset, @limit")
            query_parts.append("RETURN doc")

            query = " ".join(query_parts)
            cursor = self.db.aql.execute(query, bind_vars=bind_vars)

            return [AnalysisExecution.from_dict(doc) for doc in cursor]

        except Exception as e:
            raise StorageError(f"Failed to query executions: {e}") from e

    def update_execution(self, execution: AnalysisExecution) -> None:
        """Update execution."""
        with self._lock:
            try:
                collection = self.db.collection(self.EXECUTIONS_COLLECTION)
                doc = execution.to_dict()
                collection.update(doc)
                logger.debug(f"Updated execution: {execution.execution_id}")
            except DocumentUpdateError as e:
                raise NotFoundError(
                    f"Execution not found: {execution.execution_id}"
                ) from e
            except Exception as e:
                raise StorageError(f"Failed to update execution: {e}") from e

    def delete_execution(self, execution_id: str) -> None:
        """Delete execution."""
        with self._lock:
            try:
                collection = self.db.collection(self.EXECUTIONS_COLLECTION)
                collection.delete(execution_id)
                logger.debug(f"Deleted execution: {execution_id}")
            except Exception as e:
                raise StorageError(f"Failed to delete execution: {e}") from e

    # --- Epoch Operations ---

    def insert_epoch(self, epoch: AnalysisEpoch) -> str:
        """Insert epoch record."""
        with self._lock:
            try:
                collection = self.db.collection(self.EPOCHS_COLLECTION)
                doc = epoch.to_dict()
                collection.insert(doc)
                logger.debug(f"Inserted epoch: {epoch.epoch_id}")
                return epoch.epoch_id
            except DocumentInsertError as e:
                if "unique constraint violated" in str(e).lower():
                    raise DuplicateError(
                        f"Epoch with name '{epoch.name}' already exists"
                    ) from e
                raise StorageError(f"Failed to insert epoch: {e}") from e
            except Exception as e:
                raise StorageError(f"Failed to insert epoch: {e}") from e

    async def insert_epoch_async(self, epoch: AnalysisEpoch) -> str:
        """Async version of insert_epoch."""
        async with self._async_lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.insert_epoch, epoch)

    def get_epoch(self, epoch_id: str) -> AnalysisEpoch:
        """Get epoch by ID."""
        try:
            collection = self.db.collection(self.EPOCHS_COLLECTION)
            doc = collection.get(epoch_id)
            if not doc:
                raise NotFoundError(f"Epoch not found: {epoch_id}")
            return AnalysisEpoch.from_dict(doc)
        except DocumentGetError as e:
            raise NotFoundError(f"Epoch not found: {epoch_id}") from e
        except NotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to get epoch: {e}") from e

    def get_epoch_by_name(self, name: str) -> Optional[AnalysisEpoch]:
        """Get epoch by unique name."""
        try:
            query = f"""
            FOR doc IN {self.EPOCHS_COLLECTION}
                FILTER doc.name == @name
                LIMIT 1
                RETURN doc
            """
            cursor = self.db.aql.execute(query, bind_vars={"name": name})
            docs = list(cursor)
            if docs:
                return AnalysisEpoch.from_dict(docs[0])
            return None
        except Exception as e:
            raise StorageError(f"Failed to get epoch by name: {e}") from e

    def query_epochs(
        self, filter: Optional[EpochFilter] = None, limit: int = 100, offset: int = 0
    ) -> List[AnalysisEpoch]:
        """Query epochs with filters."""
        try:
            query_parts = [f"FOR doc IN {self.EPOCHS_COLLECTION}"]
            bind_vars = {"limit": limit, "offset": offset}

            if filter:
                conditions = []

                if filter.start_date:
                    conditions.append("doc.timestamp >= @start_date")
                    bind_vars["start_date"] = filter.start_date.isoformat()

                if filter.end_date:
                    conditions.append("doc.timestamp <= @end_date")
                    bind_vars["end_date"] = filter.end_date.isoformat()

                if filter.status:
                    conditions.append("doc.status == @status")
                    bind_vars["status"] = filter.status.value

                if filter.name_pattern:
                    conditions.append("LIKE(doc.name, @name_pattern, true)")
                    bind_vars["name_pattern"] = filter.name_pattern

                if filter.tags:
                    # Match epochs that have ALL specified tags
                    for i, tag in enumerate(filter.tags):
                        conditions.append(f"@tag{i} IN doc.tags")
                        bind_vars[f"tag{i}"] = tag

                if conditions:
                    query_parts.append("FILTER " + " AND ".join(conditions))

            query_parts.append("SORT doc.timestamp DESC")
            query_parts.append("LIMIT @offset, @limit")
            query_parts.append("RETURN doc")

            query = " ".join(query_parts)
            cursor = self.db.aql.execute(query, bind_vars=bind_vars)

            return [AnalysisEpoch.from_dict(doc) for doc in cursor]

        except Exception as e:
            raise StorageError(f"Failed to query epochs: {e}") from e

    def update_epoch(self, epoch: AnalysisEpoch) -> None:
        """Update epoch."""
        with self._lock:
            try:
                collection = self.db.collection(self.EPOCHS_COLLECTION)
                doc = epoch.to_dict()
                collection.update(doc)
                logger.debug(f"Updated epoch: {epoch.epoch_id}")
            except DocumentUpdateError as e:
                raise NotFoundError(f"Epoch not found: {epoch.epoch_id}") from e
            except Exception as e:
                raise StorageError(f"Failed to update epoch: {e}") from e

    def delete_epoch(self, epoch_id: str, cascade: bool = False) -> None:
        """Delete epoch, optionally cascading to executions."""
        with self._lock:
            try:
                if cascade:
                    # Delete all executions in this epoch
                    query = f"""
                    FOR doc IN {self.EXECUTIONS_COLLECTION}
                        FILTER doc.epoch_id == @epoch_id
                        REMOVE doc IN {self.EXECUTIONS_COLLECTION}
                    """
                    self.db.aql.execute(query, bind_vars={"epoch_id": epoch_id})
                    logger.debug(f"Deleted executions for epoch: {epoch_id}")

                # Delete epoch
                collection = self.db.collection(self.EPOCHS_COLLECTION)
                collection.delete(epoch_id)
                logger.debug(f"Deleted epoch: {epoch_id}")

            except Exception as e:
                raise StorageError(f"Failed to delete epoch: {e}") from e

    # --- Requirements Operations ---

    def insert_requirements(self, requirements: ExtractedRequirements) -> str:
        """Insert requirements record."""
        with self._lock:
            try:
                collection = self.db.collection(self.REQUIREMENTS_COLLECTION)
                doc = requirements.to_dict()
                collection.insert(doc)
                logger.debug(f"Inserted requirements: {requirements.requirements_id}")
                return requirements.requirements_id
            except Exception as e:
                raise StorageError(f"Failed to insert requirements: {e}") from e

    async def insert_requirements_async(
        self, requirements: ExtractedRequirements
    ) -> str:
        """Async version of insert_requirements."""
        async with self._async_lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self.insert_requirements, requirements
            )

    def get_requirements(self, requirements_id: str) -> ExtractedRequirements:
        """Get requirements by ID."""
        try:
            collection = self.db.collection(self.REQUIREMENTS_COLLECTION)
            doc = collection.get(requirements_id)
            if not doc:
                raise NotFoundError(f"Requirements not found: {requirements_id}")
            return ExtractedRequirements.from_dict(doc)
        except DocumentGetError as e:
            raise NotFoundError(f"Requirements not found: {requirements_id}") from e
        except NotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to get requirements: {e}") from e

    # --- Use Case Operations ---

    def insert_use_case(self, use_case: GeneratedUseCase) -> str:
        """Insert use case record."""
        with self._lock:
            try:
                collection = self.db.collection(self.USE_CASES_COLLECTION)
                doc = use_case.to_dict()
                collection.insert(doc)
                logger.debug(f"Inserted use case: {use_case.use_case_id}")
                return use_case.use_case_id
            except Exception as e:
                raise StorageError(f"Failed to insert use case: {e}") from e

    async def insert_use_case_async(self, use_case: GeneratedUseCase) -> str:
        """Async version of insert_use_case."""
        async with self._async_lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.insert_use_case, use_case)

    def get_use_case(self, use_case_id: str) -> GeneratedUseCase:
        """Get use case by ID."""
        try:
            collection = self.db.collection(self.USE_CASES_COLLECTION)
            doc = collection.get(use_case_id)
            if not doc:
                raise NotFoundError(f"Use case not found: {use_case_id}")
            return GeneratedUseCase.from_dict(doc)
        except DocumentGetError as e:
            raise NotFoundError(f"Use case not found: {use_case_id}") from e
        except NotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to get use case: {e}") from e

    def query_use_cases_by_requirements(
        self, requirements_id: str
    ) -> List[GeneratedUseCase]:
        """Get all use cases from requirements."""
        try:
            query = f"""
            FOR doc IN {self.USE_CASES_COLLECTION}
                FILTER doc.requirements_id == @requirements_id
                RETURN doc
            """
            cursor = self.db.aql.execute(
                query, bind_vars={"requirements_id": requirements_id}
            )
            return [GeneratedUseCase.from_dict(doc) for doc in cursor]
        except Exception as e:
            raise StorageError(f"Failed to query use cases: {e}") from e

    # --- Template Operations ---

    def insert_template(self, template: AnalysisTemplate) -> str:
        """Insert template record."""
        with self._lock:
            try:
                collection = self.db.collection(self.TEMPLATES_COLLECTION)
                doc = template.to_dict()
                collection.insert(doc)
                logger.debug(f"Inserted template: {template.template_id}")
                return template.template_id
            except Exception as e:
                raise StorageError(f"Failed to insert template: {e}") from e

    async def insert_template_async(self, template: AnalysisTemplate) -> str:
        """Async version of insert_template."""
        async with self._async_lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.insert_template, template)

    def get_template(self, template_id: str) -> AnalysisTemplate:
        """Get template by ID."""
        try:
            collection = self.db.collection(self.TEMPLATES_COLLECTION)
            doc = collection.get(template_id)
            if not doc:
                raise NotFoundError(f"Template not found: {template_id}")
            return AnalysisTemplate.from_dict(doc)
        except DocumentGetError as e:
            raise NotFoundError(f"Template not found: {template_id}") from e
        except NotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to get template: {e}") from e

    def query_templates_by_use_case(self, use_case_id: str) -> List[AnalysisTemplate]:
        """Get all templates from use case."""
        try:
            query = f"""
            FOR doc IN {self.TEMPLATES_COLLECTION}
                FILTER doc.use_case_id == @use_case_id
                RETURN doc
            """
            cursor = self.db.aql.execute(query, bind_vars={"use_case_id": use_case_id})
            return [AnalysisTemplate.from_dict(doc) for doc in cursor]
        except Exception as e:
            raise StorageError(f"Failed to query templates: {e}") from e

    # --- Management Operations ---

    def reset(self, confirm: bool = False) -> None:
        """Delete all catalog data."""
        if not confirm:
            raise ValidationError("Must pass confirm=True to reset catalog")

        with self._lock:
            try:
                collections = [
                    self.EXECUTIONS_COLLECTION,
                    self.EPOCHS_COLLECTION,
                    self.REQUIREMENTS_COLLECTION,
                    self.USE_CASES_COLLECTION,
                    self.TEMPLATES_COLLECTION,
                ]

                for collection_name in collections:
                    if self.db.has_collection(collection_name):
                        collection = self.db.collection(collection_name)
                        collection.truncate()

                logger.warning("Catalog reset: all data deleted")

            except Exception as e:
                raise StorageError(f"Failed to reset catalog: {e}") from e

    def get_statistics(self) -> Dict[str, Any]:
        """Get catalog statistics."""
        try:
            stats = {}

            # Count executions
            executions = self.db.collection(self.EXECUTIONS_COLLECTION)
            stats["total_executions"] = executions.count()

            # Count epochs
            epochs = self.db.collection(self.EPOCHS_COLLECTION)
            stats["total_epochs"] = epochs.count()

            # Get algorithm breakdown
            query = f"""
            FOR doc IN {self.EXECUTIONS_COLLECTION}
                COLLECT algorithm = doc.algorithm WITH COUNT INTO count
                RETURN {{algorithm, count}}
            """
            cursor = self.db.aql.execute(query)
            stats["execution_count_by_algorithm"] = {
                item["algorithm"]: item["count"] for item in cursor
            }

            # Get status breakdown
            query = f"""
            FOR doc IN {self.EXECUTIONS_COLLECTION}
                COLLECT status = doc.status WITH COUNT INTO count
                RETURN {{status, count}}
            """
            cursor = self.db.aql.execute(query)
            stats["execution_count_by_status"] = {
                item["status"]: item["count"] for item in cursor
            }

            return stats

        except Exception as e:
            raise StorageError(f"Failed to get statistics: {e}") from e

    def export_catalog(self, output_path: str) -> None:
        """Export catalog to JSON file."""
        try:
            data = {
                "exported_at": datetime.now().isoformat(),
                "executions": [],
                "epochs": [],
                "requirements": [],
                "use_cases": [],
                "templates": [],
            }

            # Export all collections
            collections_map = {
                "executions": self.EXECUTIONS_COLLECTION,
                "epochs": self.EPOCHS_COLLECTION,
                "requirements": self.REQUIREMENTS_COLLECTION,
                "use_cases": self.USE_CASES_COLLECTION,
                "templates": self.TEMPLATES_COLLECTION,
            }

            for key, collection_name in collections_map.items():
                query = f"FOR doc IN {collection_name} RETURN doc"
                cursor = self.db.aql.execute(query)
                data[key] = list(cursor)

            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Catalog exported to: {output_path}")

        except Exception as e:
            raise StorageError(f"Failed to export catalog: {e}") from e

    def import_catalog(self, input_path: str) -> None:
        """Import catalog from JSON file."""
        with self._lock:
            try:
                with open(input_path, "r") as f:
                    data = json.load(f)

                collections_map = {
                    "executions": self.EXECUTIONS_COLLECTION,
                    "epochs": self.EPOCHS_COLLECTION,
                    "requirements": self.REQUIREMENTS_COLLECTION,
                    "use_cases": self.USE_CASES_COLLECTION,
                    "templates": self.TEMPLATES_COLLECTION,
                }

                for key, collection_name in collections_map.items():
                    if key in data and data[key]:
                        collection = self.db.collection(collection_name)
                        collection.import_bulk(data[key])
                        logger.info(f"Imported {len(data[key])} {key}")

                logger.info(f"Catalog imported from: {input_path}")

            except Exception as e:
                raise StorageError(f"Failed to import catalog: {e}") from e

    def close(self) -> None:
        """Close database connection."""
        # ArangoDB connections are managed by the client
        # No explicit close needed
        logger.debug("ArangoDBStorage closed")
