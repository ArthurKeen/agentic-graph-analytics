"""Analyses must run bounded-concurrently, and one blow-up must not sink the rest.

`enable_parallelism=False` sequences workflow *steps* and never reaches
`ExecutionAgent.process_async`, so the fan-out there used to run every template
at once regardless. Analyses share one GAE engine and each loads the whole graph
first, so a FinReflectKG run (3.1M vertices / 17.5M edges) died on `503 Service
Unavailable` from /loaddata with three engines orphaned and billing.
"""

import asyncio
import os
import threading
import time

import pytest

from graph_analytics_ai.ai.agents.constants import AgentDefaults
from graph_analytics_ai.ai.agents.specialized import ExecutionAgent
from graph_analytics_ai.ai.agents.base import AgentMessage, AgentState


class _Tracker:
    """Records how many executions overlap."""

    def __init__(self, blow_up_on=None, hold=0.05):
        self.live = 0
        self.peak = 0
        self.started = []
        self._blow_up_on = blow_up_on or set()
        self._hold = hold
        self._lock = threading.Lock()

    def execute_template(self, template, wait, epoch, req, uc):
        # Hold the slot so overlap is observable. Without this the stub returns
        # before the next task starts and `peak` stays 1 whatever the bound is
        # — a test that passes for the wrong reason.
        with self._lock:
            self.live += 1
            self.peak = max(self.peak, self.live)
            self.started.append(template.name)
        try:
            time.sleep(self._hold)
            if template.name in self._blow_up_on:
                raise RuntimeError(f"engine 503 for {template.name}")
            return _ok(template)
        finally:
            with self._lock:
                self.live -= 1


def _ok(template):
    from graph_analytics_ai.ai.execution import (
        AnalysisJob,
        ExecutionResult,
        ExecutionStatus,
    )
    from datetime import datetime

    return ExecutionResult(
        job=AnalysisJob(
            job_id="j",
            template_name=template.name,
            algorithm="pagerank",
            status=ExecutionStatus.COMPLETED,
            submitted_at=datetime.now(),
            result_collection="r",
        ),
        success=True,
    )


def _template(name):
    from types import SimpleNamespace

    return SimpleNamespace(
        name=name,
        algorithm=SimpleNamespace(algorithm=SimpleNamespace(value="pagerank")),
        config=SimpleNamespace(result_collection=f"{name}_results"),
    )


def _agent(tracker):
    agent = ExecutionAgent.__new__(ExecutionAgent)
    agent.executor = tracker
    agent.log = lambda *a, **k: None
    return agent


def _run(agent, templates):
    state = AgentState.__new__(AgentState)
    state.templates = templates
    state.metadata = {}
    state.execution_results = []

    async def _mark(_):
        return None

    state.mark_step_complete_async = _mark
    msg = AgentMessage(
        from_agent="orchestrator",
        to_agent="execution-specialist",
        message_type="execute",
        content={"max_executions": len(templates)},
    )
    agent.create_success_message = lambda **kw: kw
    return (
        asyncio.run(ExecutionAgent.process_async.__wrapped__(agent, msg, state)),
        state,
    )


@pytest.mark.parametrize("limit", [1, 2, 3])
def test_concurrency_is_bounded(monkeypatch, limit):
    """Never more than the configured number of analyses in flight."""
    monkeypatch.setenv("GAE_MAX_CONCURRENT_ANALYSES", str(limit))
    tracker = _Tracker()
    templates = [_template(f"t{i}") for i in range(8)]

    _run(_agent(tracker), templates)

    assert tracker.peak <= limit, f"peak {tracker.peak} exceeded limit {limit}"
    assert len(tracker.started) == 8, "every template must still run"


def test_default_is_bounded_not_unbounded(monkeypatch):
    """With no override, the default bound applies rather than a free-for-all."""
    monkeypatch.delenv("GAE_MAX_CONCURRENT_ANALYSES", raising=False)
    tracker = _Tracker()
    templates = [_template(f"t{i}") for i in range(10)]

    _run(_agent(tracker), templates)

    assert tracker.peak <= AgentDefaults.MAX_CONCURRENT_ANALYSES
    assert tracker.peak < 10, "unbounded fan-out regressed"


def test_one_raising_analysis_does_not_sink_the_others(monkeypatch):
    """A raising analysis becomes a recorded failure; the rest still complete.

    This also covers the exception branch end to end — it constructs
    ExecutionResult/AnalysisJob/ExecutionStatus/datetime, which are easy to use
    in that branch without importing.
    """
    monkeypatch.setenv("GAE_MAX_CONCURRENT_ANALYSES", "2")
    tracker = _Tracker(blow_up_on={"t1", "t3"})
    templates = [_template(f"t{i}") for i in range(5)]

    _, state = _run(_agent(tracker), templates)

    results = state.execution_results
    assert len(results) == 5, "every template must produce a result row"
    failed = [r for r in results if not r.success]
    assert {r.job.template_name for r in failed} == {"t1", "t3"}
    assert all("503" in (r.error or "") for r in failed)
    assert len([r for r in results if r.success]) == 3
