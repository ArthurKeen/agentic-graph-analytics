"""
Trace replay and debugging functionality.

Allows loading and inspecting saved traces, with debug mode for verbose logging.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from . import WorkflowTrace, TraceEvent, TraceEventType, WorkflowPerformanceMetrics


class TraceReplayer:
    """
    Loads and replays saved workflow traces.

    Useful for debugging, analysis, and understanding workflow behavior.
    """

    def __init__(self, trace_path: str):
        """
        Initialize replayer with saved trace.

        Args:
            trace_path: Path to JSON trace file
        """
        self.trace_path = trace_path
        self.trace = self._load_trace()

    def _load_trace(self) -> WorkflowTrace:
        """Load trace from JSON file."""
        with open(self.trace_path, "r") as f:
            data = json.load(f)

        # Reconstruct trace from JSON
        events = [
            TraceEvent(
                event_id=e["event_id"],
                event_type=TraceEventType(e["event_type"]),
                timestamp=e["timestamp"],
                agent_name=e.get("agent_name"),
                duration_ms=e.get("duration_ms"),
                data=e.get("data", {}),
                parent_event_id=e.get("parent_event_id"),
                metadata=e.get("metadata", {}),
            )
            for e in data.get("events", [])
        ]

        trace = WorkflowTrace(
            trace_id=data["trace_id"],
            workflow_id=data["workflow_id"],
            events=events,
            state_snapshots=data.get("state_snapshots", []),
            metadata=data.get("metadata", {}),
        )

        # Reconstruct performance metrics if present
        if data.get("performance"):
            perf_data = data["performance"]
            trace.performance = self._reconstruct_performance(perf_data)

        return trace

    def _reconstruct_performance(
        self, perf_data: Dict[str, Any]
    ) -> WorkflowPerformanceMetrics:
        """Reconstruct performance metrics from JSON data."""
        from . import AgentPerformanceMetrics

        agent_metrics = {}
        for agent_name, metrics_data in perf_data.get("agent_metrics", {}).items():
            agent_metrics[agent_name] = AgentPerformanceMetrics(
                agent_name=agent_name,
                invocation_count=metrics_data.get("invocation_count", 0),
                total_time_ms=metrics_data.get("total_time_ms", 0),
                llm_calls=metrics_data.get("llm_calls", 0),
                llm_time_ms=metrics_data.get("llm_time_ms", 0),
                llm_tokens_input=metrics_data.get("llm_tokens_input", 0),
                llm_tokens_output=metrics_data.get("llm_tokens_output", 0),
                tool_calls=metrics_data.get("tool_calls", 0),
                tool_time_ms=metrics_data.get("tool_time_ms", 0),
                errors=metrics_data.get("errors", 0),
                messages_sent=metrics_data.get("messages_sent", 0),
                messages_received=metrics_data.get("messages_received", 0),
            )

        return WorkflowPerformanceMetrics(
            workflow_id=perf_data["workflow_id"],
            started_at=perf_data["started_at"],
            ended_at=perf_data.get("ended_at"),
            total_time_ms=perf_data.get("total_time_ms", 0),
            agent_metrics=agent_metrics,
            total_llm_calls=perf_data.get("total_llm_calls", 0),
            total_llm_time_ms=perf_data.get("total_llm_time_ms", 0),
            total_llm_tokens=perf_data.get("total_llm_tokens", 0),
            total_messages=perf_data.get("total_messages", 0),
            total_errors=perf_data.get("total_errors", 0),
            steps_completed=perf_data.get("steps_completed", 0),
        )

    def print_summary(self) -> None:
        """Print trace summary."""
        print(f"\n{'='*70}")
        print(f"Trace Summary: {self.trace.trace_id}")
        print(f"{'='*70}\n")

        print(f"Workflow ID: {self.trace.workflow_id}")
        print(f"Total Events: {len(self.trace.events)}")

        if self.trace.performance:
            perf = self.trace.performance
            print("\nPerformance:")
            print(f"  Total Time: {perf.total_time_ms/1000:.2f}s")
            print(f"  Steps: {perf.steps_completed}")
            print(f"  LLM Calls: {perf.total_llm_calls}")
            print(f"  Total Tokens: {perf.total_llm_tokens:,}")
            print(f"  Estimated Cost: ${perf.llm_cost_estimate_usd:.4f}")
            print(f"  Errors: {perf.total_errors}")

        print()

    def replay_timeline(
        self, speed: float = 1.0, filter_types: Optional[List[TraceEventType]] = None
    ) -> None:
        """
        Replay trace events in chronological order.

        Args:
            speed: Playback speed multiplier (1.0 = real-time, 2.0 = 2x, etc.)
            filter_types: Optional list of event types to show
        """
        import time

        print(f"\n🎬 Replaying trace: {self.trace.trace_id}")
        print(f"   Speed: {speed}x")
        if filter_types:
            print(f"   Filters: {[t.value for t in filter_types]}")
        print()

        events = self.trace.events
        if filter_types:
            events = [e for e in events if e.event_type in filter_types]

        start_time = None
        for event in events:
            # Calculate delay based on event timestamps
            if start_time is None:
                start_time = datetime.fromisoformat(event.timestamp)
            else:
                event_time = datetime.fromisoformat(event.timestamp)
                delay = (event_time - start_time).total_seconds() / speed
                if delay > 0:
                    time.sleep(min(delay, 2))  # Cap at 2 seconds
                start_time = event_time

            self._print_event(event)

    def _print_event(self, event: TraceEvent) -> None:
        """Print a single event."""
        timestamp = event.timestamp.split("T")[1][:12]
        agent = event.agent_name or "System"
        event_type = event.event_type.value.replace("_", " ").title()

        duration_str = f" ({event.duration_ms:.0f}ms)" if event.duration_ms else ""

        # Color-code by event type
        if "error" in event.event_type.value:
            prefix = "❌"
        elif "completed" in event.event_type.value:
            prefix = "✅"
        elif "start" in event.event_type.value or "invoked" in event.event_type.value:
            prefix = "🔵"
        else:
            prefix = "◦"

        print(f"{prefix} [{timestamp}] {agent:20s} {event_type:25s}{duration_str}")

        # Print key data points
        if event.data:
            for key, value in list(event.data.items())[:3]:  # Show first 3 data items
                if len(str(value)) < 100:  # Only show short values
                    print(f"     {key}: {value}")

    def find_bottlenecks(self, threshold_ms: float = 1000) -> List[Dict[str, Any]]:
        """
        Find operations that took longer than threshold.

        Args:
            threshold_ms: Threshold in milliseconds

        Returns:
            List of slow operations
        """
        bottlenecks = []

        for event in self.trace.events:
            if event.duration_ms and event.duration_ms > threshold_ms:
                bottlenecks.append(
                    {
                        "timestamp": event.timestamp,
                        "agent": event.agent_name,
                        "event_type": event.event_type.value,
                        "duration_ms": event.duration_ms,
                        "data": event.data,
                    }
                )

        # Sort by duration
        bottlenecks.sort(key=lambda x: x["duration_ms"], reverse=True)

        return bottlenecks

    def analyze_agent_communication(self) -> Dict[str, Any]:
        """
        Analyze message flow between agents.

        Returns:
            Communication analysis with statistics
        """
        messages = self.trace.get_agent_interactions()

        # Count messages between each pair
        pairs = {}
        for msg in messages:
            from_agent = msg["from_agent"]
            to_agent = msg["to_agent"]
            key = f"{from_agent} → {to_agent}"
            pairs[key] = pairs.get(key, 0) + 1

        # Find most active pairs
        sorted_pairs = sorted(pairs.items(), key=lambda x: x[1], reverse=True)

        # Count messages per agent
        agent_sends = {}
        agent_receives = {}
        for msg in messages:
            from_agent = msg["from_agent"]
            to_agent = msg["to_agent"]
            agent_sends[from_agent] = agent_sends.get(from_agent, 0) + 1
            agent_receives[to_agent] = agent_receives.get(to_agent, 0) + 1

        return {
            "total_messages": len(messages),
            "unique_pairs": len(pairs),
            "most_active_pairs": sorted_pairs[:5],
            "most_active_senders": sorted(
                agent_sends.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "most_active_receivers": sorted(
                agent_receives.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }

    def get_agent_timeline(self, agent_name: str) -> List[TraceEvent]:
        """
        Get chronological events for a specific agent.

        Args:
            agent_name: Name of agent

        Returns:
            List of events for that agent
        """
        return self.trace.get_events_by_agent(agent_name)

    def compare_with(self, other_trace_path: str) -> Dict[str, Any]:
        """
        Compare this trace with another trace.

        Args:
            other_trace_path: Path to other trace JSON file

        Returns:
            Comparison results
        """
        other_replayer = TraceReplayer(other_trace_path)
        other_trace = other_replayer.trace

        comparison = {
            "this_trace": self.trace.trace_id,
            "other_trace": other_trace.trace_id,
            "events": {
                "this": len(self.trace.events),
                "other": len(other_trace.events),
                "diff": len(self.trace.events) - len(other_trace.events),
            },
        }

        if self.trace.performance and other_trace.performance:
            this_perf = self.trace.performance
            other_perf = other_trace.performance

            comparison["performance"] = {
                "total_time_ms": {
                    "this": this_perf.total_time_ms,
                    "other": other_perf.total_time_ms,
                    "diff": this_perf.total_time_ms - other_perf.total_time_ms,
                    "percent_change": (
                        (
                            (this_perf.total_time_ms - other_perf.total_time_ms)
                            / other_perf.total_time_ms
                            * 100
                        )
                        if other_perf.total_time_ms > 0
                        else 0
                    ),
                },
                "llm_calls": {
                    "this": this_perf.total_llm_calls,
                    "other": other_perf.total_llm_calls,
                    "diff": this_perf.total_llm_calls - other_perf.total_llm_calls,
                },
                "total_tokens": {
                    "this": this_perf.total_llm_tokens,
                    "other": other_perf.total_llm_tokens,
                    "diff": this_perf.total_llm_tokens - other_perf.total_llm_tokens,
                },
                "cost": {
                    "this": this_perf.llm_cost_estimate_usd,
                    "other": other_perf.llm_cost_estimate_usd,
                    "diff": this_perf.llm_cost_estimate_usd
                    - other_perf.llm_cost_estimate_usd,
                },
            }

        return comparison


class DebugMode:
    """
    Debug mode for verbose workflow tracing.

    Enables detailed logging, state snapshots, and debugging output.
    """

    def __init__(self, enabled: bool = False, snapshot_interval: int = 5):
        """
        Initialize debug mode.

        Args:
            enabled: Whether debug mode is enabled
            snapshot_interval: How often to take state snapshots (every N events)
        """
        self.enabled = enabled
        self.snapshot_interval = snapshot_interval
        self.snapshot_counter = 0
        self.debug_log: List[Dict[str, Any]] = []

    def log(
        self, level: str, message: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log debug message.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            message: Log message
            data: Optional additional data
        """
        if not self.enabled:
            return

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "data": data or {},
        }

        self.debug_log.append(entry)

        # Print to console
        prefix = {"DEBUG": "🔍", "INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌"}.get(
            level, "◦"
        )

        print(f"{prefix} [{level}] {message}")
        if data and len(data) <= 3:
            for key, value in data.items():
                print(f"     {key}: {value}")

    def should_snapshot(self) -> bool:
        """Check if it's time to take a state snapshot."""
        if not self.enabled:
            return False

        self.snapshot_counter += 1
        if self.snapshot_counter >= self.snapshot_interval:
            self.snapshot_counter = 0
            return True
        return False

    def export_log(self, output_path: str) -> None:
        """
        Export debug log to file.

        Args:
            output_path: Output file path
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(self.debug_log, f, indent=2, default=str)

        print(f"🐛 Debug log exported to: {output_path}")


def load_trace(trace_path: str) -> WorkflowTrace:
    """
    Load a saved workflow trace.

    Args:
        trace_path: Path to JSON trace file

    Returns:
        Loaded workflow trace
    """
    replayer = TraceReplayer(trace_path)
    return replayer.trace


def compare_traces(trace_path1: str, trace_path2: str) -> Dict[str, Any]:
    """
    Compare two workflow traces.

    Args:
        trace_path1: Path to first trace
        trace_path2: Path to second trace

    Returns:
        Comparison results
    """
    replayer1 = TraceReplayer(trace_path1)
    return replayer1.compare_with(trace_path2)
