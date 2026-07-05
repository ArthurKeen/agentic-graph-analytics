"""
Integration tests for ArangoDB storage backend.

These tests require a running ArangoDB instance.
They can be run against a test database.
"""

import os
from datetime import datetime, timezone

import pytest
from arango import ArangoClient

from graph_analytics_ai.catalog.storage import ArangoDBStorage
from graph_analytics_ai.catalog.models import (
    AnalysisExecution,
    AnalysisEpoch,
    ExtractedRequirements,
    GeneratedUseCase,
    AnalysisTemplate,
    GraphConfig,
    PerformanceMetrics,
    ExecutionStatus,
    EpochStatus,
    ExecutionFilter,
    generate_execution_id,
    generate_epoch_id,
)
from graph_analytics_ai.catalog.exceptions import (
    NotFoundError,
    ValidationError,
    DuplicateError,
)

# Skip these tests if no ArangoDB available
pytestmark = pytest.mark.skipif(
    not os.getenv("ARANGO_TEST_URL"), reason="ArangoDB test instance not configured"
)


@pytest.fixture(scope="module")
def arango_db():
    """Create test database connection."""
    # Get test credentials from environment
    url = os.getenv("ARANGO_TEST_URL", "http://localhost:8529")
    username = os.getenv("ARANGO_TEST_USERNAME", "root")
    password = os.getenv("ARANGO_TEST_PASSWORD", "test")
    db_name = os.getenv("ARANGO_TEST_DB", "_system")

    client = ArangoClient(hosts=url)
    db = client.db(db_name, username=username, password=password)

    yield db


@pytest.fixture
def storage(arango_db):
    """Create storage backend for testing."""
    storage = ArangoDBStorage(arango_db, auto_initialize=True)

    # Clear collections before each test
    storage.reset(confirm=True)

    yield storage

    # Cleanup after test
    storage.reset(confirm=True)
    storage.close()


class TestArangoDBStorage:
    """Test ArangoDB storage backend."""

    def test_initialize_collections(self, arango_db):
        """Test collection initialization."""
        storage = ArangoDBStorage(arango_db, auto_initialize=False)

        # Initialize
        storage.initialize_collections()

        # Verify collections exist
        assert arango_db.has_collection(storage.EXECUTIONS_COLLECTION)
        assert arango_db.has_collection(storage.EPOCHS_COLLECTION)
        assert arango_db.has_collection(storage.REQUIREMENTS_COLLECTION)

        # Safe to call multiple times
        storage.initialize_collections()

        storage.close()

    def test_insert_and_get_execution(self, storage):
        """Test inserting and retrieving execution."""
        execution = self._create_test_execution()

        # Insert
        execution_id = storage.insert_execution(execution)
        assert execution_id == execution.execution_id

        # Retrieve
        retrieved = storage.get_execution(execution_id)
        assert retrieved.execution_id == execution.execution_id
        assert retrieved.algorithm == execution.algorithm
        assert retrieved.status == ExecutionStatus.COMPLETED

    def test_get_nonexistent_execution(self, storage):
        """Test getting nonexistent execution raises error."""
        with pytest.raises(NotFoundError):
            storage.get_execution("nonexistent")

    def test_query_executions_no_filter(self, storage):
        """Test querying all executions."""
        # Insert multiple executions
        exec1 = self._create_test_execution(algorithm="pagerank")
        exec2 = self._create_test_execution(algorithm="wcc")

        storage.insert_execution(exec1)
        storage.insert_execution(exec2)

        # Query all
        executions = storage.query_executions()
        assert len(executions) == 2

    def test_query_executions_with_filter(self, storage):
        """Test querying with filters."""
        # Insert executions
        exec1 = self._create_test_execution(algorithm="pagerank")
        exec2 = self._create_test_execution(algorithm="wcc")

        storage.insert_execution(exec1)
        storage.insert_execution(exec2)

        # Filter by algorithm
        filter = ExecutionFilter(algorithm="pagerank")
        executions = storage.query_executions(filter)

        assert len(executions) == 1
        assert executions[0].algorithm == "pagerank"

    def test_query_executions_with_epoch_filter(self, storage):
        """Test filtering by epoch."""
        epoch = self._create_test_epoch()
        storage.insert_epoch(epoch)

        exec1 = self._create_test_execution(epoch_id=epoch.epoch_id)
        exec2 = self._create_test_execution(epoch_id=None)

        storage.insert_execution(exec1)
        storage.insert_execution(exec2)

        # Filter by epoch
        filter = ExecutionFilter(epoch_id=epoch.epoch_id)
        executions = storage.query_executions(filter)

        assert len(executions) == 1
        assert executions[0].epoch_id == epoch.epoch_id

    def test_update_execution(self, storage):
        """Test updating execution."""
        execution = self._create_test_execution()
        storage.insert_execution(execution)

        # Update
        execution.status = ExecutionStatus.FAILED
        execution.error_message = "Test error"
        storage.update_execution(execution)

        # Verify
        retrieved = storage.get_execution(execution.execution_id)
        assert retrieved.status == ExecutionStatus.FAILED
        assert retrieved.error_message == "Test error"

    def test_delete_execution(self, storage):
        """Test deleting execution."""
        execution = self._create_test_execution()
        storage.insert_execution(execution)

        # Delete
        storage.delete_execution(execution.execution_id)

        # Verify deleted
        with pytest.raises(NotFoundError):
            storage.get_execution(execution.execution_id)

    def test_insert_and_get_epoch(self, storage):
        """Test epoch operations."""
        epoch = self._create_test_epoch()

        # Insert
        epoch_id = storage.insert_epoch(epoch)
        assert epoch_id == epoch.epoch_id

        # Retrieve by ID
        retrieved = storage.get_epoch(epoch_id)
        assert retrieved.name == epoch.name

        # Retrieve by name
        by_name = storage.get_epoch_by_name(epoch.name)
        assert by_name.epoch_id == epoch.epoch_id

    def test_duplicate_epoch_name(self, storage):
        """Test that duplicate epoch names raise error."""
        epoch1 = self._create_test_epoch(name="test-epoch")
        epoch2 = self._create_test_epoch(name="test-epoch")

        storage.insert_epoch(epoch1)

        with pytest.raises(DuplicateError):
            storage.insert_epoch(epoch2)

    def test_delete_epoch_cascade(self, storage):
        """Test cascading delete of epoch."""
        epoch = self._create_test_epoch()
        storage.insert_epoch(epoch)

        exec1 = self._create_test_execution(epoch_id=epoch.epoch_id)
        exec2 = self._create_test_execution(epoch_id=epoch.epoch_id)

        storage.insert_execution(exec1)
        storage.insert_execution(exec2)

        # Delete with cascade
        storage.delete_epoch(epoch.epoch_id, cascade=True)

        # Verify epoch deleted
        with pytest.raises(NotFoundError):
            storage.get_epoch(epoch.epoch_id)

        # Verify executions deleted
        with pytest.raises(NotFoundError):
            storage.get_execution(exec1.execution_id)

    def test_lineage_tracking(self, storage):
        """Test complete lineage tracking."""
        # Create lineage chain
        requirements = self._create_test_requirements()
        storage.insert_requirements(requirements)

        use_case = self._create_test_use_case(
            requirements_id=requirements.requirements_id
        )
        storage.insert_use_case(use_case)

        template = self._create_test_template(
            use_case_id=use_case.use_case_id,
            requirements_id=requirements.requirements_id,
        )
        storage.insert_template(template)

        execution = self._create_test_execution(
            template_id=template.template_id,
            use_case_id=use_case.use_case_id,
            requirements_id=requirements.requirements_id,
        )
        storage.insert_execution(execution)

        # Verify lineage queries
        retrieved_requirements = storage.get_requirements(requirements.requirements_id)
        assert retrieved_requirements.requirements_id == requirements.requirements_id

        use_cases = storage.query_use_cases_by_requirements(
            requirements.requirements_id
        )
        assert len(use_cases) == 1

        templates = storage.query_templates_by_use_case(use_case.use_case_id)
        assert len(templates) == 1

    def test_reset_catalog(self, storage):
        """Test resetting catalog."""
        # Insert some data
        execution = self._create_test_execution()
        epoch = self._create_test_epoch()

        storage.insert_execution(execution)
        storage.insert_epoch(epoch)

        # Reset without confirm should fail
        with pytest.raises(ValidationError):
            storage.reset(confirm=False)

        # Reset with confirm
        storage.reset(confirm=True)

        # Verify data deleted
        with pytest.raises(NotFoundError):
            storage.get_execution(execution.execution_id)

        with pytest.raises(NotFoundError):
            storage.get_epoch(epoch.epoch_id)

    def test_get_statistics(self, storage):
        """Test statistics gathering."""
        # Insert test data
        exec1 = self._create_test_execution(algorithm="pagerank")
        exec2 = self._create_test_execution(algorithm="wcc")
        exec3 = self._create_test_execution(algorithm="pagerank")

        storage.insert_execution(exec1)
        storage.insert_execution(exec2)
        storage.insert_execution(exec3)

        epoch = self._create_test_epoch()
        storage.insert_epoch(epoch)

        # Get statistics
        stats = storage.get_statistics()

        assert stats["total_executions"] == 3
        assert stats["total_epochs"] == 1
        assert stats["execution_count_by_algorithm"]["pagerank"] == 2
        assert stats["execution_count_by_algorithm"]["wcc"] == 1

    # Helper methods

    def _create_test_execution(
        self,
        algorithm="pagerank",
        epoch_id=None,
        template_id="template-1",
        use_case_id=None,
        requirements_id=None,
    ) -> AnalysisExecution:
        """Create a test execution."""
        return AnalysisExecution(
            execution_id=generate_execution_id(),
            timestamp=datetime.now(timezone.utc),
            algorithm=algorithm,
            algorithm_version="1.0",
            parameters={"damping": 0.85},
            template_id=template_id,
            template_name=f"{algorithm} Template",
            graph_config=GraphConfig(
                graph_name="test_graph",
                graph_type="named_graph",
                vertex_collections=["users"],
                edge_collections=["follows"],
                vertex_count=100,
                edge_count=500,
            ),
            results_location=f"{algorithm}_results",
            result_count=100,
            performance_metrics=PerformanceMetrics(execution_time_seconds=10.0),
            status=ExecutionStatus.COMPLETED,
            epoch_id=epoch_id,
            use_case_id=use_case_id,
            requirements_id=requirements_id,
        )

    def _create_test_epoch(self, name=None) -> AnalysisEpoch:
        """Create a test epoch."""
        if name is None:
            name = f"test-epoch-{generate_epoch_id()[:8]}"

        return AnalysisEpoch(
            epoch_id=generate_epoch_id(),
            name=name,
            description="Test epoch",
            timestamp=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            status=EpochStatus.ACTIVE,
            tags=["test"],
            metadata={},
        )

    def _create_test_requirements(self) -> ExtractedRequirements:
        """Create test requirements."""
        return ExtractedRequirements(
            requirements_id=generate_execution_id(),
            timestamp=datetime.now(timezone.utc),
            source_documents=["test.md"],
            domain="test",
            summary="Test requirements",
            objectives=[],
            requirements=[],
            constraints=[],
        )

    def _create_test_use_case(self, requirements_id) -> GeneratedUseCase:
        """Create test use case."""
        return GeneratedUseCase(
            use_case_id=generate_execution_id(),
            requirements_id=requirements_id,
            timestamp=datetime.now(timezone.utc),
            title="Test Use Case",
            description="Test",
            algorithm="pagerank",
            business_value="Test",
            priority="high",
            addresses_objectives=[],
            addresses_requirements=[],
        )

    def _create_test_template(self, use_case_id, requirements_id) -> AnalysisTemplate:
        """Create test template."""
        return AnalysisTemplate(
            template_id=generate_execution_id(),
            use_case_id=use_case_id,
            requirements_id=requirements_id,
            timestamp=datetime.now(timezone.utc),
            name="Test Template",
            algorithm="pagerank",
            parameters={},
            graph_config=GraphConfig(
                graph_name="test",
                graph_type="named_graph",
                vertex_collections=["v"],
                edge_collections=["e"],
                vertex_count=10,
                edge_count=20,
            ),
        )
