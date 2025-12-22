"""
Tracing and observability for agentic workflows.

Provides comprehensive tracing, performance metrics, and debugging capabilities
for understanding and optimizing workflow execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import time


class TraceEventType(Enum):
    """Types of trace events."""

    WORKFLOW_START = "workflow_start"
    WORKFLOW_END = "workflow_end"
    AGENT_INVOKED = "agent_invoked"
    AGENT_COMPLETED = "agent_completed"
    AGENT_ERROR = "agent_error"
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    LLM_CALL_START = "llm_call_start"
    LLM_CALL_END = "llm_call_end"
    TOOL_INVOKED = "tool_invoked"
    TOOL_COMPLETED = "tool_completed"
    DECISION_MADE = "decision_made"
    STATE_SNAPSHOT = "state_snapshot"
    STEP_START = "step_start"
    STEP_END = "step_end"


@dataclass
class TraceEvent:
    """
    A single trace event in the workflow.

    Records what happened, when, by whom, and with what result.
    """

    event_id: str
    """Unique event identifier."""

    event_type: TraceEventType
    """Type of event."""

    timestamp: str
    """ISO format timestamp."""

    agent_name: Optional[str] = None
    """Agent that triggered this event."""

    duration_ms: Optional[float] = None
    """Duration in milliseconds (for timed events)."""

    data: Dict[str, Any] = field(default_factory=dict)
    """Event-specific data."""

    parent_event_id: Optional[str] = None
    """Parent event (for nested events)."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "duration_ms": self.duration_ms,
            "data": self.data,
            "parent_event_id": self.parent_event_id,
            "metadata": self.metadata,
        }


@dataclass
class AgentPerformanceMetrics:
    """Performance metrics for a single agent."""

    agent_name: str
    """Agent name."""

    invocation_count: int = 0
    """Number of times agent was invoked."""

    total_time_ms: float = 0.0
    """Total execution time in milliseconds."""

    llm_calls: int = 0
    """Number of LLM calls made."""

    llm_time_ms: float = 0.0
    """Total LLM call time in milliseconds."""

    llm_tokens_input: int = 0
    """Total input tokens to LLM."""

    llm_tokens_output: int = 0
    """Total output tokens from LLM."""

    tool_calls: int = 0
    """Number of tool invocations."""

    tool_time_ms: float = 0.0
    """Total tool execution time."""

    errors: int = 0
    """Number of errors encountered."""

    messages_sent: int = 0
    """Number of messages sent."""

    messages_received: int = 0
    """Number of messages received."""

    @property
    def avg_time_ms(self) -> float:
        """Average execution time per invocation."""
        if self.invocation_count == 0:
            return 0.0
        return self.total_time_ms / self.invocation_count

    @property
    def llm_time_percent(self) -> float:
        """Percentage of time spent in LLM calls."""
        if self.total_time_ms == 0:
            return 0.0
        return (self.llm_time_ms / self.total_time_ms) * 100

    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output)."""
        return self.llm_tokens_input + self.llm_tokens_output

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "invocation_count": self.invocation_count,
            "total_time_ms": round(self.total_time_ms, 2),
            "avg_time_ms": round(self.avg_time_ms, 2),
            "llm_calls": self.llm_calls,
            "llm_time_ms": round(self.llm_time_ms, 2),
            "llm_time_percent": round(self.llm_time_percent, 1),
            "llm_tokens_input": self.llm_tokens_input,
            "llm_tokens_output": self.llm_tokens_output,
            "total_tokens": self.total_tokens,
            "tool_calls": self.tool_calls,
            "tool_time_ms": round(self.tool_time_ms, 2),
            "errors": self.errors,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
        }


@dataclass
class WorkflowPerformanceMetrics:
    """Overall workflow performance metrics."""

    workflow_id: str
    """Workflow identifier."""

    started_at: str
    """Workflow start time (ISO format)."""

    ended_at: Optional[str] = None
    """Workflow end time (ISO format)."""

    total_time_ms: float = 0.0
    """Total workflow execution time."""

    agent_metrics: Dict[str, AgentPerformanceMetrics] = field(default_factory=dict)
    """Per-agent performance metrics."""

    total_llm_calls: int = 0
    """Total LLM calls across all agents."""

    total_llm_time_ms: float = 0.0
    """Total LLM time across all agents."""

    total_llm_tokens: int = 0
    """Total tokens used."""

    total_messages: int = 0
    """Total messages exchanged."""

    total_errors: int = 0
    """Total errors encountered."""

    steps_completed: int = 0
    """Number of workflow steps completed."""

    @property
    def llm_cost_estimate_usd(self) -> float:
        """
        Estimate LLM cost in USD.

        Assumes GPT-4 pricing (~$0.03/1K input, ~$0.06/1K output tokens).
        This is a rough estimate - actual costs depend on model used.
        """
        input_tokens = sum(m.llm_tokens_input for m in self.agent_metrics.values())
        output_tokens = sum(m.llm_tokens_output for m in self.agent_metrics.values())

        input_cost = (input_tokens / 1000) * 0.03
        output_cost = (output_tokens / 1000) * 0.06

        return input_cost + output_cost

    @property
    def avg_time_per_step_ms(self) -> float:
        """Average time per workflow step."""
        if self.steps_completed == 0:
            return 0.0
        return self.total_time_ms / self.steps_completed

    def get_slowest_agents(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Get the N slowest agents by total time."""
        sorted_agents = sorted(
            self.agent_metrics.values(), key=lambda m: m.total_time_ms, reverse=True
        )

        return [
            {
                "agent": m.agent_name,
                "total_time_ms": round(m.total_time_ms, 2),
                "invocations": m.invocation_count,
            }
            for m in sorted_agents[:top_n]
        ]

    def get_top_llm_consumers(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Get the N agents that used most LLM tokens."""
        sorted_agents = sorted(
            self.agent_metrics.values(), key=lambda m: m.total_tokens, reverse=True
        )

        return [
            {
                "agent": m.agent_name,
                "total_tokens": m.total_tokens,
                "llm_calls": m.llm_calls,
            }
            for m in sorted_agents[:top_n]
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "total_time_ms": round(self.total_time_ms, 2),
            "total_time_seconds": round(self.total_time_ms / 1000, 2),
            "total_llm_calls": self.total_llm_calls,
            "total_llm_time_ms": round(self.total_llm_time_ms, 2),
            "total_llm_tokens": self.total_llm_tokens,
            "estimated_cost_usd": round(self.llm_cost_estimate_usd, 4),
            "total_messages": self.total_messages,
            "total_errors": self.total_errors,
            "steps_completed": self.steps_completed,
            "avg_time_per_step_ms": round(self.avg_time_per_step_ms, 2),
            "agent_metrics": {
                name: metrics.to_dict() for name, metrics in self.agent_metrics.items()
            },
            "slowest_agents": self.get_slowest_agents(),
            "top_llm_consumers": self.get_top_llm_consumers(),
        }


@dataclass
class WorkflowTrace:
    """
    Complete trace of workflow execution.

    Contains all events, performance metrics, and state snapshots.
    """

    trace_id: str
    """Unique trace identifier."""

    workflow_id: str
    """Workflow this trace belongs to."""

    events: List[TraceEvent] = field(default_factory=list)
    """All trace events."""

    performance: Optional[WorkflowPerformanceMetrics] = None
    """Performance metrics."""

    state_snapshots: List[Dict[str, Any]] = field(default_factory=list)
    """State snapshots taken during execution."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional trace metadata."""

    def add_event(self, event: TraceEvent) -> None:
        """Add event to trace."""
        self.events.append(event)

    def get_events_by_type(self, event_type: TraceEventType) -> List[TraceEvent]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_by_agent(self, agent_name: str) -> List[TraceEvent]:
        """Get all events from a specific agent."""
        return [e for e in self.events if e.agent_name == agent_name]

    def get_timeline(self) -> List[Dict[str, Any]]:
        """
        Get chronological timeline of major events.

        Returns simplified view of key workflow milestones.
        """
        timeline = []

        for event in self.events:
            # Filter to major events
            if event.event_type in [
                TraceEventType.WORKFLOW_START,
                TraceEventType.WORKFLOW_END,
                TraceEventType.STEP_START,
                TraceEventType.STEP_END,
                TraceEventType.AGENT_INVOKED,
                TraceEventType.AGENT_COMPLETED,
                TraceEventType.AGENT_ERROR,
                TraceEventType.DECISION_MADE,
            ]:
                timeline.append(
                    {
                        "timestamp": event.timestamp,
                        "event": event.event_type.value,
                        "agent": event.agent_name,
                        "duration_ms": event.duration_ms,
                        "summary": self._summarize_event(event),
                    }
                )

        return timeline

    def _summarize_event(self, event: TraceEvent) -> str:
        """Create human-readable summary of event."""
        if event.event_type == TraceEventType.WORKFLOW_START:
            return "Workflow execution started"
        elif event.event_type == TraceEventType.WORKFLOW_END:
            duration_str = f" in {event.duration_ms:.0f}ms" if event.duration_ms else ""
            return f"Workflow completed{duration_str}"
        elif event.event_type == TraceEventType.AGENT_INVOKED:
            return f"{event.agent_name} invoked"
        elif event.event_type == TraceEventType.AGENT_COMPLETED:
            duration_str = f" in {event.duration_ms:.0f}ms" if event.duration_ms else ""
            return f"{event.agent_name} completed{duration_str}"
        elif event.event_type == TraceEventType.AGENT_ERROR:
            error = event.data.get("error", "Unknown error")
            return f"{event.agent_name} error: {error}"
        elif event.event_type == TraceEventType.DECISION_MADE:
            decision = event.data.get("decision", "")
            return f"{event.agent_name} decided: {decision}"
        elif event.event_type == TraceEventType.STEP_START:
            step = event.data.get("step", "")
            return f"Step '{step}' started"
        elif event.event_type == TraceEventType.STEP_END:
            step = event.data.get("step", "")
            return f"Step '{step}' completed"
        else:
            return event.event_type.value

    def get_agent_interactions(self) -> List[Dict[str, Any]]:
        """
        Get agent-to-agent message flow.

        Shows communication patterns between agents.
        """
        interactions = []

        for event in self.events:
            if event.event_type == TraceEventType.MESSAGE_SENT:
                interactions.append(
                    {
                        "timestamp": event.timestamp,
                        "from_agent": event.data.get("from_agent"),
                        "to_agent": event.data.get("to_agent"),
                        "message_type": event.data.get("message_type"),
                        "message_id": event.data.get("message_id"),
                    }
                )

        return interactions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "workflow_id": self.workflow_id,
            "events_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
            "performance": self.performance.to_dict() if self.performance else None,
            "state_snapshots_count": len(self.state_snapshots),
            "state_snapshots": self.state_snapshots,
            "timeline": self.get_timeline(),
            "agent_interactions": self.get_agent_interactions(),
            "metadata": self.metadata,
        }


class TraceCollector:
    """
    Collects trace events during workflow execution.

    Thread-safe collector that can be used by multiple agents simultaneously.
    """

    def __init__(self, workflow_id: str, enable_state_snapshots: bool = False):
        """
        Initialize trace collector.

        Args:
            workflow_id: Workflow identifier
            enable_state_snapshots: Whether to capture state snapshots
        """
        self.workflow_id = workflow_id
        self.trace_id = f"trace-{workflow_id}-{int(time.time() * 1000)}"
        self.enable_state_snapshots = enable_state_snapshots

        self.trace = WorkflowTrace(trace_id=self.trace_id, workflow_id=workflow_id)

        self.performance = WorkflowPerformanceMetrics(
            workflow_id=workflow_id, started_at=datetime.utcnow().isoformat()
        )

        self._event_counter = 0
        self._active_timers: Dict[str, float] = {}

    def record_event(
        self,
        event_type: TraceEventType,
        agent_name: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        parent_event_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> str:
        """
        Record a trace event.

        Args:
            event_type: Type of event
            agent_name: Agent that triggered event
            data: Event data
            parent_event_id: Parent event ID for nested events
            duration_ms: Event duration

        Returns:
            Event ID
        """
        self._event_counter += 1
        event_id = f"evt-{self._event_counter}"

        event = TraceEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            agent_name=agent_name,
            duration_ms=duration_ms,
            data=data or {},
            parent_event_id=parent_event_id,
        )

        self.trace.add_event(event)
        self._update_metrics(event)

        return event_id

    def start_timer(self, timer_id: str) -> None:
        """Start a named timer."""
        self._active_timers[timer_id] = time.time()

    def stop_timer(self, timer_id: str) -> float:
        """
        Stop a named timer and return elapsed milliseconds.

        Args:
            timer_id: Timer identifier

        Returns:
            Elapsed time in milliseconds
        """
        if timer_id not in self._active_timers:
            return 0.0

        start_time = self._active_timers.pop(timer_id)
        elapsed_ms = (time.time() - start_time) * 1000
        return elapsed_ms

    def snapshot_state(self, state: Any) -> None:
        """
        Capture a state snapshot.

        Args:
            state: State object to snapshot
        """
        if not self.enable_state_snapshots:
            return

        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "state": state.to_dict() if hasattr(state, "to_dict") else str(state),
        }

        self.trace.state_snapshots.append(snapshot)

    def finalize(self) -> WorkflowTrace:
        """
        Finalize trace collection.

        Returns:
            Complete workflow trace
        """
        self.performance.ended_at = datetime.utcnow().isoformat()

        # Calculate total workflow time
        if self.trace.events:
            start_event = next(
                (
                    e
                    for e in self.trace.events
                    if e.event_type == TraceEventType.WORKFLOW_START
                ),
                None,
            )
            end_event = next(
                (
                    e
                    for e in reversed(self.trace.events)
                    if e.event_type == TraceEventType.WORKFLOW_END
                ),
                None,
            )

            if start_event and end_event:
                start_time = datetime.fromisoformat(start_event.timestamp)
                end_time = datetime.fromisoformat(end_event.timestamp)
                self.performance.total_time_ms = (
                    end_time - start_time
                ).total_seconds() * 1000

        # Attach performance metrics to trace
        self.trace.performance = self.performance

        return self.trace

    def _update_metrics(self, event: TraceEvent) -> None:
        """Update performance metrics based on event."""
        if event.agent_name:
            if event.agent_name not in self.performance.agent_metrics:
                self.performance.agent_metrics[event.agent_name] = (
                    AgentPerformanceMetrics(agent_name=event.agent_name)
                )

            metrics = self.performance.agent_metrics[event.agent_name]

            if event.event_type == TraceEventType.AGENT_INVOKED:
                metrics.invocation_count += 1
            elif (
                event.event_type == TraceEventType.AGENT_COMPLETED and event.duration_ms
            ):
                metrics.total_time_ms += event.duration_ms
            elif event.event_type == TraceEventType.AGENT_ERROR:
                metrics.errors += 1
                self.performance.total_errors += 1
            elif event.event_type == TraceEventType.MESSAGE_SENT:
                metrics.messages_sent += 1
                self.performance.total_messages += 1
            elif event.event_type == TraceEventType.MESSAGE_RECEIVED:
                metrics.messages_received += 1
            elif event.event_type == TraceEventType.LLM_CALL_END:
                metrics.llm_calls += 1
                self.performance.total_llm_calls += 1

                if event.duration_ms:
                    metrics.llm_time_ms += event.duration_ms
                    self.performance.total_llm_time_ms += event.duration_ms

                if "tokens_input" in event.data:
                    metrics.llm_tokens_input += event.data["tokens_input"]
                if "tokens_output" in event.data:
                    metrics.llm_tokens_output += event.data["tokens_output"]

                self.performance.total_llm_tokens += event.data.get(
                    "tokens_input", 0
                ) + event.data.get("tokens_output", 0)

            elif event.event_type == TraceEventType.TOOL_INVOKED:
                metrics.tool_calls += 1
            elif (
                event.event_type == TraceEventType.TOOL_COMPLETED and event.duration_ms
            ):
                metrics.tool_time_ms += event.duration_ms
            elif event.event_type == TraceEventType.STEP_END:
                self.performance.steps_completed += 1
