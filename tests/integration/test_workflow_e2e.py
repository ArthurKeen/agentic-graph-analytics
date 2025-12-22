"""
End-to-end workflow integration tests.

Tests the complete agentic workflow from business requirements to generated outputs.

Requirements:
- OPENROUTER_API_KEY environment variable
- ARANGO_ENDPOINT, ARANGO_DATABASE, ARANGO_PASSWORD environment variables
- Test database with sample data

Run with: pytest tests/integration/test_workflow_e2e.py --run-integration -v
"""

import pytest
from pathlib import Path

from graph_analytics_ai.ai.workflow import WorkflowOrchestrator, WorkflowStatus


@pytest.mark.integration
@pytest.mark.requires_llm
@pytest.mark.requires_db
class TestWorkflowE2E:
    """End-to-end workflow tests."""

    def test_complete_workflow_with_real_services(
        self, check_env_vars, test_use_case_file, temp_output_dir
    ):
        """
        Test complete workflow with real LLM and database.

        This test:
        1. Parses business requirements
        2. Extracts requirements using LLM
        3. Extracts schema from database
        4. Analyzes schema using LLM
        5. Generates PRD using LLM
        6. Generates use cases using LLM
        7. Saves all outputs
        """
        # Initialize orchestrator
        orchestrator = WorkflowOrchestrator(
            output_dir=str(temp_output_dir), enable_checkpoints=True, max_retries=2
        )

        # Run complete workflow
        result = orchestrator.run_complete_workflow(
            business_requirements=[test_use_case_file],
            database_endpoint=check_env_vars["db_endpoint"],
            database_name=check_env_vars["db_name"],
            database_username=check_env_vars["db_user"],
            database_password=check_env_vars["db_password"],
            product_name="E2E Test Project",
            resume_from_checkpoint=False,
        )

        # Verify workflow completed
        assert (
            result.status == WorkflowStatus.COMPLETED
        ), f"Workflow failed: {result.error_message}"
        assert result.workflow_id is not None
        assert result.total_duration_seconds is not None
        assert result.total_duration_seconds > 0

        # Verify all expected outputs were generated
        assert result.prd_path is not None, "PRD was not generated"
        assert Path(result.prd_path).exists(), f"PRD file not found: {result.prd_path}"

        assert result.use_cases_path is not None, "Use cases were not generated"
        assert Path(
            result.use_cases_path
        ).exists(), f"Use cases file not found: {result.use_cases_path}"

        assert result.schema_path is not None, "Schema analysis was not generated"
        assert Path(
            result.schema_path
        ).exists(), f"Schema file not found: {result.schema_path}"

        assert result.requirements_path is not None, "Requirements were not generated"
        assert Path(
            result.requirements_path
        ).exists(), f"Requirements file not found: {result.requirements_path}"

        # Verify completed steps
        assert (
            len(result.completed_steps) == 7
        ), f"Expected 7 completed steps, got {len(result.completed_steps)}"
        expected_steps = [
            "parse_documents",
            "extract_requirements",
            "extract_schema",
            "analyze_schema",
            "generate_prd",
            "generate_use_cases",
            "save_outputs",
        ]
        for step in expected_steps:
            assert (
                step in result.completed_steps
            ), f"Step '{step}' not in completed steps"

        # Verify file contents are substantial (not empty)
        prd_content = Path(result.prd_path).read_text()
        assert len(prd_content) > 500, "PRD content too short"
        assert (
            "Product Requirements Document" in prd_content
            or "Requirements" in prd_content
        )

        use_cases_content = Path(result.use_cases_path).read_text()
        assert len(use_cases_content) > 200, "Use cases content too short"

        schema_content = Path(result.schema_path).read_text()
        assert len(schema_content) > 200, "Schema content too short"
        assert (
            "customers" in schema_content.lower()
            or "products" in schema_content.lower()
        )

        print("\n✅ E2E workflow test passed!")
        print(f"   Workflow ID: {result.workflow_id}")
        print(f"   Duration: {result.total_duration_seconds:.1f}s")
        print(f"   Output directory: {result.output_dir}")

    def test_workflow_with_checkpoint_recovery(
        self, check_env_vars, test_use_case_file, temp_output_dir
    ):
        """
        Test workflow checkpoint and recovery.

        This test verifies that the workflow can save checkpoints and
        resume from them if interrupted.
        """
        # First run - will be interrupted
        orchestrator1 = WorkflowOrchestrator(
            output_dir=str(temp_output_dir), enable_checkpoints=True
        )

        # Run workflow (it should complete, but we'll test resume anyway)
        result1 = orchestrator1.run_complete_workflow(
            business_requirements=[test_use_case_file],
            database_endpoint=check_env_vars["db_endpoint"],
            database_name=check_env_vars["db_name"],
            database_username=check_env_vars["db_user"],
            database_password=check_env_vars["db_password"],
            product_name="Checkpoint Test",
            resume_from_checkpoint=False,
        )

        # Verify checkpoints were saved
        checkpoint_files = list(Path(temp_output_dir).glob("checkpoint_*.json"))
        assert len(checkpoint_files) > 0, "No checkpoint files found"

        # Second run - resume from checkpoint
        orchestrator2 = WorkflowOrchestrator(
            output_dir=str(temp_output_dir), enable_checkpoints=True
        )

        result2 = orchestrator2.run_complete_workflow(
            business_requirements=[test_use_case_file],
            database_endpoint=check_env_vars["db_endpoint"],
            database_name=check_env_vars["db_name"],
            database_username=check_env_vars["db_user"],
            database_password=check_env_vars["db_password"],
            product_name="Checkpoint Test",
            resume_from_checkpoint=True,
        )

        # Both should complete successfully
        assert result1.status == WorkflowStatus.COMPLETED
        assert result2.status == WorkflowStatus.COMPLETED

        print("\n✅ Checkpoint recovery test passed!")

    def test_workflow_error_handling(self, check_env_vars, temp_output_dir):
        """
        Test workflow error handling with invalid inputs.
        """
        orchestrator = WorkflowOrchestrator(
            output_dir=str(temp_output_dir), enable_checkpoints=False
        )

        # Try to run with non-existent file
        result = orchestrator.run_complete_workflow(
            business_requirements=["nonexistent_file.md"],
            database_endpoint=check_env_vars["db_endpoint"],
            database_name=check_env_vars["db_name"],
            database_username=check_env_vars["db_user"],
            database_password=check_env_vars["db_password"],
            product_name="Error Test",
        )

        # Should fail gracefully
        assert result.status == WorkflowStatus.FAILED
        assert result.error_message is not None
        assert len(result.error_message) > 0

        print("\n✅ Error handling test passed!")
        print(f"   Error captured: {result.error_message[:100]}...")
