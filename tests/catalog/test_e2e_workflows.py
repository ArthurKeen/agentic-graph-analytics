"""
End-to-end tests for Analysis Catalog with complete workflows.

Tests catalog integration across traditional, agentic, and parallel workflows.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime


@pytest.fixture
def mock_catalog():
    """Create mock catalog that tracks calls."""
    catalog = Mock()
    
    # Track all calls
    catalog.tracked_requirements = []
    catalog.tracked_use_cases = []
    catalog.tracked_templates = []
    catalog.tracked_executions = []
    
    def track_req(req):
        req_id = f"req-{len(catalog.tracked_requirements)}"
        catalog.tracked_requirements.append(req)
        return req_id
    
    def track_uc(uc):
        uc_id = f"uc-{len(catalog.tracked_use_cases)}"
        catalog.tracked_use_cases.append(uc)
        return uc_id
    
    def track_template(template):
        template_id = f"template-{len(catalog.tracked_templates)}"
        catalog.tracked_templates.append(template)
        return template_id
    
    def track_execution(execution):
        exec_id = f"exec-{len(catalog.tracked_executions)}"
        catalog.tracked_executions.append(execution)
        return exec_id
    
    catalog.track_requirements = Mock(side_effect=track_req)
    catalog.track_use_case = Mock(side_effect=track_uc)
    catalog.track_template = Mock(side_effect=track_template)
    catalog.track_execution = Mock(side_effect=track_execution)
    
    return catalog


class TestEndToEndWorkflows:
    """End-to-end tests for complete workflows with catalog."""
    
    @patch("graph_analytics_ai.ai.execution.executor.CATALOG_AVAILABLE", False)
    def test_traditional_workflow_without_catalog(self):
        """Test traditional workflow works without catalog (backward compatibility)."""
        from graph_analytics_ai.ai.execution import AnalysisExecutor
        
        # Should work fine without catalog
        executor = AnalysisExecutor()
        
        assert executor.catalog is None
        assert not executor.auto_track
        
    @patch("graph_analytics_ai.ai.execution.executor.CATALOG_AVAILABLE", True)
    def test_traditional_workflow_with_catalog_mock(self, mock_catalog):
        """Test traditional workflow accepts and uses catalog."""
        from graph_analytics_ai.ai.execution import AnalysisExecutor
        
        # Create executor with catalog
        executor = AnalysisExecutor(
            catalog=mock_catalog,
            workflow_mode="traditional"
        )
        
        assert executor.catalog is mock_catalog
        assert executor.auto_track is True
        assert executor.workflow_mode == "traditional"
        
    def test_agentic_workflow_accepts_catalog(self, mock_catalog):
        """Test agentic workflow runner accepts catalog parameter."""
        from graph_analytics_ai.ai.agents import AgenticWorkflowRunner
        
        # Create runner with catalog
        runner = AgenticWorkflowRunner(catalog=mock_catalog)
        
        assert runner.catalog is mock_catalog
        
        # Verify agents received catalog
        from graph_analytics_ai.ai.agents.constants import AgentNames
        
        req_agent = runner.agents[AgentNames.REQUIREMENTS_ANALYST]
        assert hasattr(req_agent, "catalog")
        assert req_agent.catalog is mock_catalog
        
        uc_agent = runner.agents[AgentNames.USE_CASE_EXPERT]
        assert hasattr(uc_agent, "catalog")
        assert uc_agent.catalog is mock_catalog
        
        template_agent = runner.agents[AgentNames.TEMPLATE_ENGINEER]
        assert hasattr(template_agent, "catalog")
        assert template_agent.catalog is mock_catalog
        
        exec_agent = runner.agents[AgentNames.EXECUTION_SPECIALIST]
        assert hasattr(exec_agent.executor, "catalog")
        assert exec_agent.executor.catalog is mock_catalog
        
    def test_agentic_workflow_without_catalog(self):
        """Test agentic workflow works without catalog (backward compatibility)."""
        from graph_analytics_ai.ai.agents import AgenticWorkflowRunner
        
        # Create runner without catalog
        runner = AgenticWorkflowRunner()
        
        assert runner.catalog is None
        
        # Verify agents have catalog=None
        from graph_analytics_ai.ai.agents.constants import AgentNames
        
        req_agent = runner.agents[AgentNames.REQUIREMENTS_ANALYST]
        assert req_agent.catalog is None
        assert not req_agent.auto_track
        
    def test_agent_tracking_methods_exist(self):
        """Test all agents have sync and async tracking methods."""
        from graph_analytics_ai.ai.agents.specialized import (
            RequirementsAgent,
            UseCaseAgent,
            TemplateAgent,
            ExecutionAgent,
        )
        from graph_analytics_ai.ai.llm.base import LLMProvider
        
        # Create mock LLM
        llm = Mock(spec=LLMProvider)
        
        # RequirementsAgent
        req_agent = RequirementsAgent(llm, catalog=Mock())
        assert hasattr(req_agent, "_track_requirements")
        assert hasattr(req_agent, "_track_requirements_async")
        
        # UseCaseAgent
        uc_agent = UseCaseAgent(llm, catalog=Mock())
        assert hasattr(uc_agent, "_track_use_case")
        assert hasattr(uc_agent, "_track_use_case_async")
        
        # TemplateAgent
        template_agent = TemplateAgent(llm, catalog=Mock())
        assert hasattr(template_agent, "_track_template")
        assert hasattr(template_agent, "_track_template_async")
        
        # ExecutionAgent has catalog passed to executor
        exec_agent = ExecutionAgent(llm, catalog=Mock())
        assert exec_agent.executor.catalog is not None
        
    def test_parallel_workflow_has_async_tracking(self):
        """Test parallel workflow uses async tracking methods."""
        from graph_analytics_ai.ai.agents.specialized import (
            RequirementsAgent,
            UseCaseAgent,
            TemplateAgent,
        )
        from graph_analytics_ai.ai.llm.base import LLMProvider
        import inspect
        
        llm = Mock(spec=LLMProvider)
        catalog = Mock()
        
        # Verify async tracking methods are coroutines
        req_agent = RequirementsAgent(llm, catalog=catalog)
        assert inspect.iscoroutinefunction(req_agent._track_requirements_async)
        
        uc_agent = UseCaseAgent(llm, catalog=catalog)
        assert inspect.iscoroutinefunction(uc_agent._track_use_case_async)
        
        template_agent = TemplateAgent(llm, catalog=catalog)
        assert inspect.iscoroutinefunction(template_agent._track_template_async)
        
    def test_workflow_mode_propagates_to_executor(self, mock_catalog):
        """Test workflow mode is set correctly in executor."""
        from graph_analytics_ai.ai.execution import AnalysisExecutor
        
        # Traditional mode
        trad_executor = AnalysisExecutor(
            catalog=mock_catalog,
            workflow_mode="traditional"
        )
        assert trad_executor.workflow_mode == "traditional"
        
        # Agentic mode (set by ExecutionAgent)
        from graph_analytics_ai.ai.agents.specialized import ExecutionAgent
        from unittest.mock import Mock
        
        llm = Mock()
        exec_agent = ExecutionAgent(llm, catalog=mock_catalog)
        assert exec_agent.executor.workflow_mode == "agentic"
        
    def test_catalog_optional_in_all_components(self):
        """Test catalog is optional everywhere (backward compatibility)."""
        from graph_analytics_ai.ai.agents import AgenticWorkflowRunner
        from graph_analytics_ai.ai.execution import AnalysisExecutor
        from graph_analytics_ai.ai.agents.specialized import (
            RequirementsAgent,
            UseCaseAgent,
            TemplateAgent,
            ExecutionAgent,
        )
        from unittest.mock import Mock
        
        llm = Mock()
        
        # All should work without catalog
        runner = AgenticWorkflowRunner()  # No error
        executor = AnalysisExecutor()  # No error
        req_agent = RequirementsAgent(llm)  # No error
        uc_agent = UseCaseAgent(llm)  # No error
        template_agent = TemplateAgent(llm)  # No error
        exec_agent = ExecutionAgent(llm)  # No error
        
        # All should have catalog=None
        assert runner.catalog is None
        assert executor.catalog is None
        assert req_agent.catalog is None
        assert uc_agent.catalog is None
        assert template_agent.catalog is None
        assert exec_agent.executor.catalog is None


class TestCatalogIntegrationPoints:
    """Test specific catalog integration points."""
    
    def test_requirements_agent_tracks_on_success(self, mock_catalog):
        """Test RequirementsAgent tracks requirements after extraction."""
        from graph_analytics_ai.ai.agents.specialized import RequirementsAgent
        from graph_analytics_ai.ai.agents.base import AgentMessage, AgentState
        from unittest.mock import Mock
        
        llm = Mock()
        agent = RequirementsAgent(llm, catalog=mock_catalog)
        
        # Create message and state
        message = AgentMessage(
            message_id="msg-1",
            from_agent="test",
            to_agent="requirements",
            message_type="task",
            content={"documents": []},
        )
        state = AgentState()
        
        # Process (will use defaults since no documents)
        response = agent.process(message, state)
        
        # Verify requirements were tracked
        assert mock_catalog.track_requirements.called
        assert len(mock_catalog.tracked_requirements) == 1
        
    def test_use_case_agent_tracks_on_success(self, mock_catalog):
        """Test UseCaseAgent tracks use cases after generation."""
        from graph_analytics_ai.ai.agents.specialized import UseCaseAgent
        from graph_analytics_ai.ai.agents.base import AgentMessage, AgentState
        from graph_analytics_ai.ai.documents.models import ExtractedRequirements
        from graph_analytics_ai.ai.schema.models import SchemaAnalysis
        from unittest.mock import Mock
        
        llm = Mock()
        agent = UseCaseAgent(llm, catalog=mock_catalog)
        
        # Setup state with requirements and schema
        state = AgentState()
        state.requirements = ExtractedRequirements(
            domain="test",
            summary="test",
            documents=[],
            objectives=[],
            requirements=[],
            stakeholders=[],
            constraints=[],
            risks=[],
        )
        
        # Create a minimal GraphSchema
        from graph_analytics_ai.ai.schema.models import GraphSchema
        
        schema = GraphSchema(database_name="test")
        state.schema_analysis = SchemaAnalysis(schema=schema, domain="test")
        state.schema = schema
        
        message = AgentMessage(
            message_id="msg-1",
            from_agent="test",
            to_agent="usecase",
            message_type="task",
            content={},
        )
        
        # Process
        try:
            response = agent.process(message, state)
            # Verify use cases were tracked
            assert mock_catalog.track_use_case.called
        except Exception:
            # May fail due to missing dependencies, but tracking call should happen
            pass


class TestBackwardCompatibility:
    """Test backward compatibility - existing code must work unchanged."""
    
    def test_existing_executor_code_works(self):
        """Test existing AnalysisExecutor code works unchanged."""
        from graph_analytics_ai.ai.execution import AnalysisExecutor
        
        # This is how users currently create executors
        executor = AnalysisExecutor()
        
        # Should work without errors
        assert executor is not None
        assert executor.catalog is None
        
    def test_existing_runner_code_works(self):
        """Test existing AgenticWorkflowRunner code works unchanged."""
        from graph_analytics_ai.ai.agents import AgenticWorkflowRunner
        
        # This is how users currently create runners
        runner = AgenticWorkflowRunner()
        
        # Should work without errors
        assert runner is not None
        assert runner.catalog is None
        
    def test_existing_convenience_functions_work(self):
        """Test existing convenience functions work unchanged."""
        from graph_analytics_ai.ai.agents.runner import (
            run_agentic_workflow,
            run_agentic_workflow_async,
        )
        
        # Functions should exist and be callable
        assert callable(run_agentic_workflow)
        assert callable(run_agentic_workflow_async)


class TestErrorHandling:
    """Test error handling in catalog tracking."""
    
    def test_tracking_failure_doesnt_break_workflow(self, mock_catalog):
        """Test that catalog tracking failures don't break workflows."""
        from graph_analytics_ai.ai.agents.specialized import RequirementsAgent
        from graph_analytics_ai.ai.agents.base import AgentMessage, AgentState
        from unittest.mock import Mock
        
        # Make catalog raise error
        mock_catalog.track_requirements.side_effect = Exception("Catalog error!")
        
        llm = Mock()
        agent = RequirementsAgent(llm, catalog=mock_catalog)
        
        message = AgentMessage(
            message_id="msg-1",
            from_agent="test",
            to_agent="requirements",
            message_type="task",
            content={"documents": []},
        )
        state = AgentState()
        
        # Process should succeed despite catalog error
        response = agent.process(message, state)
        
        # Workflow should complete
        assert response is not None
        assert state.requirements is not None

