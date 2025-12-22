"""Tests for agent base classes."""


class TestAgentBase:
    """Basic tests for agent base module."""

    def test_import_agent(self):
        """Test that Agent class can be imported."""
        from graph_analytics_ai.ai.agents.base import Agent

        assert Agent is not None

    def test_import_agent_message(self):
        """Test that AgentMessage can be imported."""
        from graph_analytics_ai.ai.agents.base import AgentMessage

        assert AgentMessage is not None

    def test_import_agent_state(self):
        """Test that AgentState can be imported."""
        from graph_analytics_ai.ai.agents.base import AgentState

        assert AgentState is not None

    def test_import_handle_agent_errors(self):
        """Test that handle_agent_errors decorator can be imported."""
        from graph_analytics_ai.ai.agents.base import handle_agent_errors

        assert handle_agent_errors is not None
