"""
Tests for async agent execution.

Tests parallel execution capabilities and performance improvements.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from graph_analytics_ai.ai.agents.base import (
    Agent,
    AgentType,
    AgentMessage,
    AgentState,
)
from graph_analytics_ai.ai.llm.base import LLMProvider, LLMResponse, LLMConfig


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self):
        config = LLMConfig(api_key="test", model="test-model")
        super().__init__(config)
        self.call_count = 0

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Mock generate."""
        self.call_count += 1
        return LLMResponse(
            content=f"Mock response {self.call_count}",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )

    def generate_structured(self, prompt: str, schema: dict, **kwargs) -> dict:
        """Mock structured generation."""
        return {"result": "mock"}

    def chat(self, messages: list, **kwargs) -> LLMResponse:
        """Mock chat."""
        return self.generate("mock chat")


class SimpleAgent(Agent):
    """Simple test agent."""

    def process(self, message: AgentMessage, state: AgentState) -> AgentMessage:
        """Process synchronously."""
        return self.create_message(
            to_agent="test",
            message_type="result",
            content={"status": "success"},
        )


@pytest.mark.asyncio
async def test_agent_process_async():
    """Test that agent can process messages asynchronously."""
    llm = MockLLMProvider()
    agent = SimpleAgent(
        agent_type=AgentType.ORCHESTRATOR,
        name="TestAgent",
        llm_provider=llm,
    )
    
    state = AgentState()
    message = AgentMessage(
        from_agent="user",
        to_agent="TestAgent",
        message_type="task",
        content={},
    )
    
    # Test async processing
    response = await agent.process_async(message, state)
    
    assert response is not None
    assert response.message_type == "result"
    assert response.content["status"] == "success"


@pytest.mark.asyncio
async def test_agent_reason_async():
    """Test that agent can reason asynchronously."""
    llm = MockLLMProvider()
    agent = SimpleAgent(
        agent_type=AgentType.ORCHESTRATOR,
        name="TestAgent",
        llm_provider=llm,
    )
    
    # Test async reasoning
    result = await agent.reason_async("Test prompt")
    
    assert result is not None
    assert "Mock response" in result
    assert llm.call_count == 1


@pytest.mark.asyncio
async def test_agent_state_async_methods():
    """Test AgentState async methods for thread safety."""
    state = AgentState()
    
    # Test async message adding
    message = AgentMessage(
        from_agent="agent1",
        to_agent="agent2",
        message_type="task",
        content={},
    )
    
    await state.add_message_async(message)
    assert len(state.messages) == 1
    
    # Test async error adding
    await state.add_error_async("agent1", "test error")
    assert len(state.errors) == 1
    assert state.errors[0]["agent"] == "agent1"
    
    # Test async step completion
    await state.mark_step_complete_async("test_step")
    assert "test_step" in state.completed_steps


@pytest.mark.asyncio
async def test_parallel_execution():
    """Test that multiple async operations can run in parallel."""
    llm = MockLLMProvider()
    
    # Create multiple agents
    agents = [
        SimpleAgent(
            agent_type=AgentType.ORCHESTRATOR,
            name=f"Agent{i}",
            llm_provider=llm,
        )
        for i in range(3)
    ]
    
    state = AgentState()
    message = AgentMessage(
        from_agent="user",
        to_agent="TestAgent",
        message_type="task",
        content={},
    )
    
    # Execute all agents in parallel
    start_time = asyncio.get_event_loop().time()
    
    tasks = [agent.process_async(message, state) for agent in agents]
    responses = await asyncio.gather(*tasks)
    
    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time
    
    # Verify all completed
    assert len(responses) == 3
    for response in responses:
        assert response.message_type == "result"
    
    # Parallel execution should be fast (< 1 second for 3 simple operations)
    assert duration < 1.0


def test_sync_execution_still_works():
    """Test that synchronous execution still works."""
    llm = MockLLMProvider()
    agent = SimpleAgent(
        agent_type=AgentType.ORCHESTRATOR,
        name="TestAgent",
        llm_provider=llm,
    )
    
    state = AgentState()
    message = AgentMessage(
        from_agent="user",
        to_agent="TestAgent",
        message_type="task",
        content={},
    )
    
    # Test sync processing
    response = agent.process(message, state)
    
    assert response is not None
    assert response.message_type == "result"
    assert response.content["status"] == "success"


@pytest.mark.asyncio
async def test_llm_async_generate():
    """Test async LLM generation."""
    llm = MockLLMProvider()
    
    # Test async generate
    response = await llm.generate_async("test prompt")
    
    assert response is not None
    assert response.content is not None
    assert response.total_tokens > 0


if __name__ == "__main__":
    # Run async tests
    asyncio.run(test_agent_process_async())
    asyncio.run(test_agent_reason_async())
    asyncio.run(test_agent_state_async_methods())
    asyncio.run(test_parallel_execution())
    asyncio.run(test_llm_async_generate())
    
    # Run sync test
    test_sync_execution_still_works()
    
    print("✓ All async agent tests passed!")

