"""
Base agent models and framework.

Defines the core agent architecture and communication protocol.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from functools import wraps

from ..llm.base import LLMProvider


def handle_agent_errors(func):
    """
    Decorator to handle agent processing errors consistently.
    
    Automatically catches exceptions in agent process() methods,
    logs the error, updates state, and returns a properly formatted
    error message to the orchestrator.
    
    Usage:
        @handle_agent_errors
        def process(self, message: AgentMessage, state: AgentState) -> AgentMessage:
            # Just implement the happy path!
            result = do_work()
            return self.create_success_message(...)
    
    Benefits:
        - Reduces code duplication
        - Consistent error handling across all agents
        - Cleaner agent code (focus on logic, not error handling)
        - Automatic error logging and state updates
    """
    @wraps(func)
    def wrapper(self: 'Agent', message: 'AgentMessage', state: 'AgentState') -> 'AgentMessage':
        try:
            return func(self, message, state)
        except Exception as e:
            # Log the error
            self.log(f"Error: {e}", "error")
            
            # Update state
            state.add_error(self.name, str(e))
            
            # Return error message to orchestrator
            return self.create_error_message(
                to_agent="orchestrator",
                error=str(e),
                reply_to=message.message_id
            )
    return wrapper


class AgentType(Enum):
    """Type of agent."""
    ORCHESTRATOR = "orchestrator"
    SCHEMA_ANALYSIS = "schema_analysis"
    REQUIREMENTS = "requirements"
    USE_CASE = "use_case"
    TEMPLATE = "template"
    EXECUTION = "execution"
    REPORTING = "reporting"
    QUALITY_ASSURANCE = "quality_assurance"


@dataclass
class AgentMessage:
    """
    Message between agents.
    
    Agents communicate through structured messages.
    """
    
    from_agent: str
    """Agent sending the message."""
    
    to_agent: str
    """Agent receiving the message."""
    
    message_type: str
    """Type of message (task, result, question, etc)."""
    
    content: Dict[str, Any]
    """Message payload."""
    
    timestamp: datetime = field(default_factory=datetime.now)
    """When message was sent."""
    
    reply_to: Optional[str] = None
    """ID of message this is replying to."""
    
    message_id: str = field(default_factory=lambda: f"msg_{datetime.now().timestamp()}")
    """Unique message ID."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "reply_to": self.reply_to,
            "message_id": self.message_id
        }


@dataclass
class AgentState:
    """
    Shared state between agents.
    
    Contains all intermediate results and context.
    """
    
    # Input
    input_documents: List[Dict[str, Any]] = field(default_factory=list)
    database_config: Dict[str, Any] = field(default_factory=dict)
    
    # Intermediate results
    schema: Optional[Any] = None
    schema_analysis: Optional[Any] = None
    requirements: Optional[Any] = None
    prd: Optional[Any] = None
    use_cases: List[Any] = field(default_factory=list)
    templates: List[Any] = field(default_factory=list)
    execution_results: List[Any] = field(default_factory=list)
    reports: List[Any] = field(default_factory=list)
    
    # Workflow state
    current_step: str = "init"
    completed_steps: List[str] = field(default_factory=list)
    messages: List[AgentMessage] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    started_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, message: AgentMessage) -> None:
        """Add message to history."""
        self.messages.append(message)
    
    def add_error(self, agent: str, error: str) -> None:
        """Add error to history."""
        self.errors.append({
            "agent": agent,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
    
    def mark_step_complete(self, step: str) -> None:
        """Mark a step as completed."""
        if step not in self.completed_steps:
            self.completed_steps.append(step)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "messages_count": len(self.messages),
            "errors_count": len(self.errors),
            "started_at": self.started_at.isoformat(),
            "metadata": self.metadata
        }


class Agent(ABC):
    """
    Base class for all agents.
    
    Agents are autonomous entities that:
    - Have a specific role and expertise
    - Can reason about their domain
    - Make decisions autonomously
    - Communicate with other agents
    - Use tools to accomplish tasks
    """
    
    def __init__(
        self,
        agent_type: AgentType,
        name: str,
        llm_provider: LLMProvider,
        tools: Optional[Dict[str, Callable]] = None
    ):
        """
        Initialize agent.
        
        Args:
            agent_type: Type of agent
            name: Agent name
            llm_provider: LLM provider for reasoning
            tools: Available tools for this agent
        """
        self.agent_type = agent_type
        self.name = name
        self.llm_provider = llm_provider
        self.tools = tools or {}
        self.memory: List[Dict[str, Any]] = []
    
    @abstractmethod
    def process(
        self,
        message: AgentMessage,
        state: AgentState
    ) -> AgentMessage:
        """
        Process a message and return a response.
        
        Args:
            message: Incoming message
            state: Shared state
            
        Returns:
            Response message
        """
        pass
    
    def reason(self, prompt: str) -> str:
        """
        Use LLM to reason about a problem.
        
        Args:
            prompt: Reasoning prompt
            
        Returns:
            LLM response
        """
        response = self.llm_provider.generate(prompt)
        return response.content
    
    def use_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Use a tool.
        
        Args:
            tool_name: Name of tool
            **kwargs: Tool arguments
            
        Returns:
            Tool result
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not available to agent {self.name}")
        
        return self.tools[tool_name](**kwargs)
    
    def add_to_memory(self, entry: Dict[str, Any]) -> None:
        """Add entry to agent memory."""
        self.memory.append({
            **entry,
            "timestamp": datetime.now().isoformat()
        })
    
    def create_message(
        self,
        to_agent: str,
        message_type: str,
        content: Dict[str, Any],
        reply_to: Optional[str] = None
    ) -> AgentMessage:
        """
        Create a message to send.
        
        Args:
            to_agent: Recipient agent
            message_type: Type of message
            content: Message content
            reply_to: Message ID being replied to
            
        Returns:
            Agent message
        """
        return AgentMessage(
            from_agent=self.name,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            reply_to=reply_to
        )
    
    def create_success_message(
        self,
        to_agent: str,
        content: Dict[str, Any],
        reply_to: Optional[str] = None
    ) -> AgentMessage:
        """
        Create a success result message.
        
        Helper method to reduce boilerplate for successful operations.
        
        Args:
            to_agent: Recipient agent
            content: Success message content
            reply_to: Message ID being replied to
            
        Returns:
            Success message with status='success'
        """
        return self.create_message(
            to_agent=to_agent,
            message_type="result",
            content={"status": "success", **content},
            reply_to=reply_to
        )
    
    def create_error_message(
        self,
        to_agent: str,
        error: str,
        reply_to: Optional[str] = None
    ) -> AgentMessage:
        """
        Create an error message.
        
        Helper method to reduce boilerplate for error handling.
        
        Args:
            to_agent: Recipient agent
            error: Error message
            reply_to: Message ID being replied to
            
        Returns:
            Error message
        """
        return self.create_message(
            to_agent=to_agent,
            message_type="error",
            content={"error": error},
            reply_to=reply_to
        )
    
    def log(self, message: str, level: str = "info") -> None:
        """Log a message."""
        print(f"[{self.name}] {level.upper()}: {message}")
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, type={self.agent_type.value})>"


class SpecializedAgent(Agent):
    """
    Base class for specialized domain agents.
    
    Provides common functionality for agents with specific expertise.
    """
    
    def __init__(
        self,
        agent_type: AgentType,
        name: str,
        llm_provider: LLMProvider,
        system_prompt: str,
        tools: Optional[Dict[str, Callable]] = None
    ):
        """
        Initialize specialized agent.
        
        Args:
            agent_type: Type of agent
            name: Agent name
            llm_provider: LLM provider
            system_prompt: System prompt defining agent's expertise
            tools: Available tools
        """
        super().__init__(agent_type, name, llm_provider, tools)
        self.system_prompt = system_prompt
    
    def reason_with_context(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Reason with additional context.
        
        Args:
            prompt: Question or task
            context: Additional context
            
        Returns:
            LLM response
        """
        full_prompt = f"""
{self.system_prompt}

Context:
{context}

Task:
{prompt}
"""
        return self.reason(full_prompt)
