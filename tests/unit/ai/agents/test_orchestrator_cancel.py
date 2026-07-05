"""Tests for cooperative cancellation in OrchestratorAgent.

The product layer's ``AgenticRunSupervisor`` controls long-running
agentic runs through a per-run ``threading.Event`` cancel token. The
orchestrator must:

* accept the token on both ``run_workflow`` and ``run_workflow_async``
* check it before starting any work (pre-flight)
* check it between steps in both the sync (delegation) and async
  (sequential / parallel) paths
* raise ``WorkflowCancelled`` so the supervisor can distinguish
  "user cancelled" from "agent failed"

These tests use stub agents that immediately complete each step so the
cancel/no-cancel paths are easy to assert without invoking real LLMs.
"""

from __future__ import annotations

import threading

import pytest

from graph_analytics_ai.ai.agents.base import (
    Agent,
    AgentMessage,
    AgentState,
    AgentType,
)
from graph_analytics_ai.ai.agents.constants import AgentNames, WorkflowSteps
from graph_analytics_ai.ai.agents.orchestrator import (
    OrchestratorAgent,
    WorkflowCancelled,
    _is_cancel_requested,
)


class _NoopAgent(Agent):
    """Minimal stub agent that immediately marks the step complete.

    Real agents call into LLMs and ArangoDB — too heavy for a unit
    test. The orchestrator only needs a "result" reply to advance.
    """

    def __init__(self, name: str, agent_type: AgentType) -> None:
        super().__init__(agent_type=agent_type, name=name, llm_provider=None)
        self.calls = 0

    def process(self, message: AgentMessage, state: AgentState) -> AgentMessage:
        self.calls += 1
        step = message.content.get("step")
        if step:
            state.mark_step_complete(step)
        return self.create_message(
            to_agent=AgentNames.ORCHESTRATOR,
            message_type="result",
            content={"status": "success"},
            reply_to=message.message_id,
        )


def _build_orchestrator() -> OrchestratorAgent:
    """All six canonical steps wired to noop agents."""

    return OrchestratorAgent(
        llm_provider=None,
        agents={
            AgentNames.SCHEMA_ANALYST: _NoopAgent(
                AgentNames.SCHEMA_ANALYST, AgentType.SCHEMA_ANALYSIS
            ),
            AgentNames.REQUIREMENTS_ANALYST: _NoopAgent(
                AgentNames.REQUIREMENTS_ANALYST, AgentType.REQUIREMENTS
            ),
            AgentNames.USE_CASE_EXPERT: _NoopAgent(
                AgentNames.USE_CASE_EXPERT, AgentType.USE_CASE
            ),
            AgentNames.TEMPLATE_ENGINEER: _NoopAgent(
                AgentNames.TEMPLATE_ENGINEER, AgentType.TEMPLATE
            ),
            AgentNames.EXECUTION_SPECIALIST: _NoopAgent(
                AgentNames.EXECUTION_SPECIALIST, AgentType.EXECUTION
            ),
            AgentNames.REPORTING_SPECIALIST: _NoopAgent(
                AgentNames.REPORTING_SPECIALIST, AgentType.REPORTING
            ),
        },
    )


# --- duck-typed cancel-token helper ------------------------------------------


def test_is_cancel_requested_handles_threading_event_callable_and_none():
    event = threading.Event()
    assert _is_cancel_requested(None) is False
    assert _is_cancel_requested(event) is False
    event.set()
    assert _is_cancel_requested(event) is True

    assert _is_cancel_requested(lambda: True) is True
    assert _is_cancel_requested(lambda: False) is False

    # A callable that raises is treated as "not cancelled" so a buggy
    # token never aborts a real run.
    def boom() -> bool:
        raise RuntimeError("kaboom")

    assert _is_cancel_requested(boom) is False


# --- sync (message-passing) path ---------------------------------------------


def test_run_workflow_raises_cancelled_when_token_set_before_start():
    orchestrator = _build_orchestrator()
    cancel = threading.Event()
    cancel.set()

    with pytest.raises(WorkflowCancelled) as excinfo:
        orchestrator.run_workflow(cancel_token=cancel)

    # Pre-flight cancellation has no observed step — distinguishes
    # this from "cancelled mid-step N".
    assert excinfo.value.observed_at_step is None
    # No agent was ever invoked.
    for agent in orchestrator.agents.values():
        assert agent.calls == 0


def test_run_workflow_raises_after_first_step_when_token_flips_mid_run():
    orchestrator = _build_orchestrator()
    cancel = threading.Event()

    schema_agent = orchestrator.agents[AgentNames.SCHEMA_ANALYST]
    original_process = schema_agent.process

    def trip_after_schema(message: AgentMessage, state: AgentState) -> AgentMessage:
        # Flip the cancel flag during the schema step. The next
        # _delegate_to_agent call (for requirements) must see it.
        cancel.set()
        return original_process(message, state)

    schema_agent.process = trip_after_schema  # type: ignore[assignment]

    with pytest.raises(WorkflowCancelled) as excinfo:
        orchestrator.run_workflow(cancel_token=cancel)

    # The first step ran, but the second step (requirements_extraction)
    # was the one observed_at_step the cancel was caught at.
    assert excinfo.value.observed_at_step == WorkflowSteps.REQUIREMENTS_EXTRACTION
    assert orchestrator.agents[AgentNames.SCHEMA_ANALYST].calls == 1
    assert (
        orchestrator.agents[AgentNames.REQUIREMENTS_ANALYST].calls == 0
    ), "requirements agent must not be invoked once cancel is observed"


def test_run_workflow_runs_to_completion_when_no_cancel_token():
    orchestrator = _build_orchestrator()
    state = orchestrator.run_workflow()
    # All six steps recorded as complete.
    assert set(state.completed_steps) == {
        WorkflowSteps.SCHEMA_ANALYSIS,
        WorkflowSteps.REQUIREMENTS_EXTRACTION,
        WorkflowSteps.USE_CASE_GENERATION,
        WorkflowSteps.TEMPLATE_GENERATION,
        WorkflowSteps.EXECUTION,
        WorkflowSteps.REPORTING,
    }


# --- live step-status telemetry ----------------------------------------------


def test_run_workflow_emits_step_events_that_drive_the_reporter():
    """Regression: the orchestrator must emit STEP_START/STEP_END per phase.

    These events (agent_name == the phase) are what the product-layer
    ``StepStatusReporter`` maps to WorkflowStep rows. Before this was
    wired, the events were defined but never recorded, so the run DAG
    stayed ``pending`` for the whole run.
    """

    from graph_analytics_ai.ai.tracing import TraceCollector, TraceEventType
    from graph_analytics_ai.product.agentic_run_supervisor import StepStatusReporter
    from graph_analytics_ai.product.models import WorkflowStepStatus

    orchestrator = _build_orchestrator()
    collector = TraceCollector("workflow-step-events")
    orchestrator.trace_collector = collector

    # Raw event capture (phase routing) + the real reporter (status).
    raw: list[tuple] = []
    collector.add_listener(lambda e: raw.append((e.event_type, e.agent_name)))
    transitions: list[tuple] = []

    class _RecordingService:
        def update_workflow_step(self, run_id, step_id, status, **kwargs):
            transitions.append((step_id, status))

    collector.add_listener(
        StepStatusReporter(run_id="run-x", service=_RecordingService())
    )

    orchestrator.run_workflow()

    for step in WorkflowSteps.STANDARD_WORKFLOW:
        assert (TraceEventType.STEP_START, step) in raw
        assert (TraceEventType.STEP_END, step) in raw
        assert (step, WorkflowStepStatus.RUNNING) in transitions
        assert (step, WorkflowStepStatus.COMPLETED) in transitions
