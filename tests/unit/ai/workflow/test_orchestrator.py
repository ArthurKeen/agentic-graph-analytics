"""
Tests for workflow orchestrator.
"""

from unittest.mock import Mock, patch

import pytest

from graph_analytics_ai.ai.workflow.orchestrator import (
    WorkflowOrchestrator,
    WorkflowResult,
)
from graph_analytics_ai.ai.workflow.state import WorkflowStatus, WorkflowStep
from graph_analytics_ai.ai.workflow.exceptions import WorkflowCheckpointError


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider."""
    provider = Mock()
    provider.generate = Mock(return_value=Mock(content="test response", cost_usd=0.01))
    return provider


@pytest.fixture
def mock_parsed_documents():
    """Create mock parsed documents."""
    doc = Mock()
    doc.content = "Test content"
    doc.word_count = 100
    return [doc]


@pytest.fixture
def mock_extracted_requirements():
    """Create mock extracted requirements."""
    req = Mock()
    req.domain = "E-commerce"
    req.total_requirements = 10
    req.critical_requirements = []
    req.all_requirements = []
    req.objectives = []
    req.stakeholders = []
    req.summary = "Test summary"
    req.documents = []
    return req


@pytest.fixture
def mock_schema():
    """Create mock graph schema."""
    schema = Mock()
    schema.vertex_collections = []
    schema.edge_collections = []
    schema.total_documents = 1000
    return schema


@pytest.fixture
def mock_schema_analysis():
    """Create mock schema analysis."""
    analysis = Mock()
    analysis.domain = "E-commerce"
    analysis.complexity_score = 5.0
    analysis.key_entities = ["User", "Product"]
    analysis.key_relationships = ["purchased", "viewed"]
    analysis.suggested_analyses = []
    return analysis


@pytest.fixture
def mock_use_cases():
    """Create mock use cases."""
    uc = Mock()
    uc.id = "UC-001"
    uc.title = "Test Use Case"
    uc.description = "Test description"
    uc.use_case_type = Mock(value="centrality")
    uc.priority = Mock(value="high")
    uc.related_requirements = []
    uc.graph_algorithms = ["PageRank"]
    uc.data_needs = ["User", "Product"]
    uc.expected_outputs = ["Rankings"]
    uc.success_metrics = ["Accuracy"]
    return [uc]


class TestWorkflowOrchestrator:
    """Test workflow orchestrator."""

    def test_initialization(self, tmp_path, mock_llm_provider):
        """Test orchestrator initialization."""
        orchestrator = WorkflowOrchestrator(
            output_dir=str(tmp_path),
            llm_provider=mock_llm_provider,
            enable_checkpoints=True,
            max_retries=3,
        )

        assert orchestrator.output_dir == tmp_path
        assert orchestrator.llm_provider == mock_llm_provider
        assert orchestrator.enable_checkpoints is True
        assert orchestrator.max_retries == 3
        assert orchestrator.state is None

    def test_initialization_creates_output_dir(self, tmp_path, mock_llm_provider):
        """Test that output directory is created."""
        output_dir = tmp_path / "test_output"

        WorkflowOrchestrator(output_dir=str(output_dir), llm_provider=mock_llm_provider)

        assert output_dir.exists()

    @patch("graph_analytics_ai.ai.workflow.orchestrator.WorkflowSteps")
    def test_run_complete_workflow_success(
        self,
        mock_steps_class,
        tmp_path,
        mock_llm_provider,
        mock_parsed_documents,
        mock_extracted_requirements,
        mock_schema,
        mock_schema_analysis,
        mock_use_cases,
    ):
        """Test successful complete workflow execution."""
        # Setup mocks
        mock_steps = Mock()
        mock_steps.parse_documents = Mock(return_value=mock_parsed_documents)
        mock_steps.extract_requirements = Mock(return_value=mock_extracted_requirements)
        mock_steps.extract_schema = Mock(return_value=mock_schema)
        mock_steps.analyze_schema = Mock(return_value=mock_schema_analysis)
        mock_steps.generate_prd = Mock(return_value="# PRD Content")
        mock_steps.generate_use_cases = Mock(return_value=mock_use_cases)
        mock_steps.save_outputs = Mock(
            return_value={
                "prd": str(tmp_path / "prd.md"),
                "use_cases": str(tmp_path / "use_cases.md"),
            }
        )
        mock_steps_class.return_value = mock_steps

        orchestrator = WorkflowOrchestrator(
            output_dir=str(tmp_path),
            llm_provider=mock_llm_provider,
            enable_checkpoints=False,
        )

        result = orchestrator.run_complete_workflow(
            business_requirements=["test.txt"],
            database_endpoint="http://localhost:8529",
            database_name="test_db",
            database_password="password",
        )

        assert result.status == WorkflowStatus.COMPLETED
        assert result.prd_path is not None
        assert result.use_cases_path is not None
        assert result.error_message is None
        assert len(result.completed_steps) == 7
        assert result.total_duration_seconds is not None

    @patch("graph_analytics_ai.ai.workflow.orchestrator.WorkflowSteps")
    def test_run_workflow_with_step_failure(
        self, mock_steps_class, tmp_path, mock_llm_provider, mock_parsed_documents
    ):
        """Test workflow with step failure."""
        mock_steps = Mock()
        mock_steps.parse_documents = Mock(return_value=mock_parsed_documents)
        mock_steps.extract_requirements = Mock(side_effect=Exception("LLM error"))
        mock_steps_class.return_value = mock_steps

        orchestrator = WorkflowOrchestrator(
            output_dir=str(tmp_path),
            llm_provider=mock_llm_provider,
            enable_checkpoints=False,
            max_retries=0,
        )

        result = orchestrator.run_complete_workflow(
            business_requirements=["test.txt"],
            database_endpoint="http://localhost:8529",
            database_name="test_db",
        )

        assert result.status == WorkflowStatus.FAILED
        assert result.error_message is not None
        assert "LLM error" in result.error_message

    @patch("graph_analytics_ai.ai.workflow.orchestrator.WorkflowSteps")
    def test_execute_step_with_retry(
        self, mock_steps_class, tmp_path, mock_llm_provider, mock_parsed_documents
    ):
        """Test step execution with retry logic."""
        mock_steps = Mock()
        # First two calls fail, third succeeds
        mock_steps.parse_documents = Mock(
            side_effect=[
                Exception("Error 1"),
                Exception("Error 2"),
                mock_parsed_documents,
            ]
        )
        mock_steps.extract_requirements = Mock(side_effect=Exception("Final error"))
        mock_steps_class.return_value = mock_steps

        orchestrator = WorkflowOrchestrator(
            output_dir=str(tmp_path),
            llm_provider=mock_llm_provider,
            enable_checkpoints=False,
            max_retries=2,
        )

        result = orchestrator.run_complete_workflow(
            business_requirements=["test.txt"],
            database_endpoint="http://localhost:8529",
            database_name="test_db",
        )

        # Should have succeeded on third try for parse_documents
        assert mock_steps.parse_documents.call_count == 3

        # Should fail on extract_requirements
        assert result.status == WorkflowStatus.FAILED

    def test_checkpoint_save_and_load(self, tmp_path, mock_llm_provider):
        """Test checkpoint saving and loading."""
        orchestrator = WorkflowOrchestrator(
            output_dir=str(tmp_path),
            llm_provider=mock_llm_provider,
            enable_checkpoints=True,
        )

        # Create a state and save checkpoint
        orchestrator.state = orchestrator._create_new_state(
            business_requirements=["test.txt"]
        )
        orchestrator.state.mark_step_started(WorkflowStep.PARSE_DOCUMENTS)
        orchestrator._save_checkpoint()

        # Verify checkpoint exists
        checkpoint_files = list(tmp_path.glob("checkpoint_*.json"))
        assert len(checkpoint_files) == 1

        # Load checkpoint
        loaded_state = orchestrator._load_checkpoint()
        assert loaded_state.workflow_id == orchestrator.state.workflow_id
        assert loaded_state.current_step == WorkflowStep.PARSE_DOCUMENTS

    def test_load_checkpoint_not_found(self, tmp_path, mock_llm_provider):
        """Test loading checkpoint when none exists."""
        orchestrator = WorkflowOrchestrator(
            output_dir=str(tmp_path), llm_provider=mock_llm_provider
        )

        with pytest.raises(WorkflowCheckpointError, match="No checkpoint files found"):
            orchestrator._load_checkpoint()

    def test_get_progress(self, tmp_path, mock_llm_provider):
        """Test getting workflow progress."""
        orchestrator = WorkflowOrchestrator(
            output_dir=str(tmp_path), llm_provider=mock_llm_provider
        )

        # Before starting
        progress = orchestrator.get_progress()
        assert progress["status"] == "not_started"
        assert progress["progress"] == 0.0

        # After starting and completing a step
        orchestrator.state = orchestrator._create_new_state()
        orchestrator.state.mark_step_started(WorkflowStep.PARSE_DOCUMENTS)
        orchestrator.state.mark_step_completed(WorkflowStep.PARSE_DOCUMENTS)

        progress = orchestrator.get_progress()
        assert (
            progress["status"] == "in_progress"
        )  # Status is in_progress after starting
        assert progress["completed_steps"] == 1
        assert progress["progress"] > 0.0
        assert progress["current_step"] is None

    def test_skip_completed_steps(self, tmp_path, mock_llm_provider):
        """Test that completed steps are skipped on resume."""
        orchestrator = WorkflowOrchestrator(
            output_dir=str(tmp_path), llm_provider=mock_llm_provider
        )

        # Create state with completed step
        orchestrator.state = orchestrator._create_new_state()
        orchestrator.state.mark_step_started(WorkflowStep.PARSE_DOCUMENTS)
        orchestrator.state.outputs["documents"] = ["test"]
        orchestrator.state.mark_step_completed(WorkflowStep.PARSE_DOCUMENTS)

        # Execute step - should return cached result
        result = orchestrator._execute_step(
            WorkflowStep.PARSE_DOCUMENTS,
            lambda: Mock(),  # Should not be called
            "documents",
        )

        assert result == ["test"]


class TestWorkflowResult:
    """Test workflow result data structure."""

    def test_create_result(self):
        """Test creating a workflow result."""
        result = WorkflowResult(
            workflow_id="test-123",
            status=WorkflowStatus.COMPLETED,
            output_dir="/tmp/output",
            prd_path="/tmp/output/prd.md",
            use_cases_path="/tmp/output/use_cases.md",
            completed_steps=["parse_documents", "extract_requirements"],
            total_duration_seconds=123.45,
        )

        assert result.workflow_id == "test-123"
        assert result.status == WorkflowStatus.COMPLETED
        assert result.prd_path == "/tmp/output/prd.md"
        assert len(result.completed_steps) == 2
        assert result.total_duration_seconds == 123.45

    def test_failed_result(self):
        """Test creating a failed result."""
        result = WorkflowResult(
            workflow_id="test-123",
            status=WorkflowStatus.FAILED,
            output_dir="/tmp/output",
            error_message="Something went wrong",
            completed_steps=["parse_documents"],
        )

        assert result.status == WorkflowStatus.FAILED
        assert result.error_message == "Something went wrong"
        assert result.prd_path is None
