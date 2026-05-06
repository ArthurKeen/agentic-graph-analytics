"""Tests for FR-31a Phase 1: AgenticRunSupervisor + service wiring.

These tests cover the four locked design decisions from PRD v0.4 at
the unit-test level:

1. Canonical six-step layout — service replaces user-supplied steps
   when ``workflow_mode == AGENTIC`` and stamps ``executor_kind`` on
   the run row so future migrations can tell where the row came from.
2. In-process executor — supervisor runs work on a ThreadPoolExecutor
   and routes per-step trace events back into ``update_workflow_step``
   via :class:`StepStatusReporter`.
3. LLM provider seam — ``LLMProviderFactory.for_workspace`` is the
   call site even in Phase 1; tests inject a stub factory.
4. Cancellation + orphan sweep — ``cancel_workflow_run`` delivers a
   cooperative cancel signal; orphan sweep flips stale RUNNING rows
   to FAILED on supervisor startup.

The tests deliberately don't exercise ``AgenticWorkflowRunner`` or
real LLM providers — that's an integration concern. Here we use a
``_FakeRunner`` that emits a scripted sequence of trace events so we
can assert exact step-status transitions without paying for LLM calls.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from graph_analytics_ai.ai.agents.constants import WorkflowSteps
from graph_analytics_ai.ai.agents.orchestrator import WorkflowCancelled
from graph_analytics_ai.ai.tracing import TraceCollector, TraceEventType
from graph_analytics_ai.product import (
    ProductService,
    WorkflowDAGEdge,
    WorkflowMode,
    WorkflowRunStatus,
    WorkflowStep,
    WorkflowStepStatus,
    create_connection_profile,
    create_graph_profile,
    create_workspace,
)
from graph_analytics_ai.product.models import DeploymentMode
from graph_analytics_ai.product.agentic_run_supervisor import (
    AGENTIC_STEP_LAYOUT,
    AgenticRunSupervisor,
    LLMProviderFactory,
    RUN_OUTCOME_CANCELLED,
    RUN_OUTCOME_COMPLETED,
    RUN_OUTCOME_FAILED,
    StepStatusReporter,
    canonical_steps,
    step_id_for_phase,
)

# Reuse the established fake repository shape from the main service tests.
# tests/unit/product is not a package (no __init__.py), so we import via
# pytest's rootdir-relative path through a sibling test module.
import importlib.util
import os
import sys

_SERVICE_TEST_PATH = os.path.join(os.path.dirname(__file__), "test_service.py")
_spec = importlib.util.spec_from_file_location(
    "_test_service_for_agentic_supervisor", _SERVICE_TEST_PATH
)
assert _spec is not None and _spec.loader is not None
_service_test_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _service_test_module
_spec.loader.exec_module(_service_test_module)
FakeProductRepository = _service_test_module.FakeProductRepository


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _FakeRunner:
    """Minimal stand-in for ``AgenticWorkflowRunner``.

    Drives a pre-baked event script through a real ``TraceCollector``
    so the reporter sees the same ``TraceEvent`` shape it would in
    production. Optionally raises a configured exception to simulate
    runner failures.
    """

    def __init__(
        self,
        *,
        events: List[Dict[str, Any]],
        raise_at: Optional[BaseException] = None,
        wait_event: Optional[threading.Event] = None,
    ) -> None:
        self.events = events
        self.raise_at = raise_at
        self.wait_event = wait_event
        self.trace_collector = TraceCollector("workflow-fake")
        self.run_called_with: Dict[str, Any] = {}

    def run(
        self,
        *,
        input_documents=None,
        database_config=None,
        max_executions=3,
        cancel_token=None,
    ):
        # Capture so tests can assert wiring (e.g. that the cancel
        # token actually reached the runner).
        self.run_called_with = {
            "input_documents": input_documents,
            "database_config": database_config,
            "max_executions": max_executions,
            "cancel_token": cancel_token,
        }

        for event in self.events:
            # Control events come first so they don't touch the
            # missing ``event_type`` key. Tests can mix control and
            # data events freely in the script.
            if event.get("__wait__"):
                if self.wait_event is not None:
                    self.wait_event.wait(timeout=2)
                continue

            if event.get("__check_cancel__"):
                if cancel_token is not None and cancel_token.is_set():
                    raise WorkflowCancelled(observed_at_step=event.get("step"))
                continue

            self.trace_collector.record_event(
                event_type=event["event_type"],
                agent_name=event.get("agent_name"),
                data=event.get("data"),
                duration_ms=event.get("duration_ms"),
            )

        if self.raise_at is not None:
            raise self.raise_at


class _RecordingService:
    """Wraps a ProductService to capture update_workflow_step calls.

    Lets us assert the reporter's translation of trace events without
    coupling to repository internals.
    """

    def __init__(self, inner: ProductService) -> None:
        self._inner = inner
        self.repository = inner.repository
        self.db_connector = inner.db_connector
        self.secret_resolver = inner.secret_resolver
        self.calls: List[Dict[str, Any]] = []

    def update_workflow_step(self, **kwargs):  # noqa: D401
        self.calls.append(kwargs)
        return self._inner.update_workflow_step(**kwargs)

    def __getattr__(self, name):
        return getattr(self._inner, name)


# ---------------------------------------------------------------------------
# Helpers to build a fully-wired workspace + agentic run
# ---------------------------------------------------------------------------


def _seed_workspace_and_run(
    *,
    workflow_mode: WorkflowMode = WorkflowMode.AGENTIC,
    requirement_version_metadata: Optional[Dict[str, Any]] = None,
):
    repository = FakeProductRepository()
    service = ProductService(
        repository=repository,
        secret_resolver=_StaticSecretResolver({"vault://db": "shh"}),
        db_connector=_FakeDbConnector(),
    )
    workspace = create_workspace(
        customer_name="Acme",
        project_name="Risk",
        environment="dev",
    )
    repository.create_workspace(workspace)

    connection = create_connection_profile(
        workspace_id=workspace.workspace_id,
        name="primary",
        deployment_mode=DeploymentMode.SELF_MANAGED,
        endpoint="http://arango",
        database="risk",
        username="root",
        secret_refs={"password": "vault://db"},
        verify_ssl=False,
    )
    repository.create_connection_profile(connection)

    graph_profile = create_graph_profile(
        workspace_id=workspace.workspace_id,
        connection_profile_id=connection.connection_profile_id,
        graph_name="risk-graph",
    )
    repository.create_graph_profile(graph_profile)

    # User supplies bogus free-form steps to prove the service
    # ignores them in agentic mode.
    user_steps = [WorkflowStep(step_id="user-typed", label="Find Anomalies")]
    user_edges: List[WorkflowDAGEdge] = []

    run = service.create_workflow_run_from_steps(
        workspace_id=workspace.workspace_id,
        workflow_mode=workflow_mode,
        steps=user_steps,
        dag_edges=user_edges,
        graph_profile_id=graph_profile.graph_profile_id,
    )

    return service, repository, run


class _StaticSecretResolver:
    def __init__(self, mapping: Dict[str, str]) -> None:
        self._mapping = mapping

    def resolve(self, ref: str) -> str:
        return self._mapping[ref]


class _FakeDbConnector:
    """Records connection arguments so tests can assert routing."""

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return object()


# ---------------------------------------------------------------------------
# Decision 1: canonical step layout
# ---------------------------------------------------------------------------


def test_canonical_layout_has_six_steps_in_known_order():
    """Decision 1: the runner has six fixed phases; we mirror them."""

    layout = canonical_steps()
    assert [c.step_id for c in layout] == [
        "schema_analysis",
        "requirements_extraction",
        "use_case_generation",
        "template_generation",
        "execution",
        "reporting",
    ]
    # Each canonical step maps cleanly to a runner phase name so the
    # reporter can route trace events back to the right product step.
    for canonical in layout:
        assert step_id_for_phase(canonical.runner_phase) == canonical.step_id

    # Unknown phases produce None so the reporter can drop them
    # (e.g. WORKFLOW_START emits with no agent_name).
    assert step_id_for_phase(None) is None
    assert step_id_for_phase("not_a_real_phase") is None


def test_create_workflow_run_in_agentic_mode_replaces_user_steps_with_canonical_six():
    """Decision 1: agentic runs ignore client step labels."""

    service, repository, run = _seed_workspace_and_run(
        workflow_mode=WorkflowMode.AGENTIC,
    )

    assert [step.step_id for step in run.steps] == [
        c.step_id for c in AGENTIC_STEP_LAYOUT
    ]
    # And the canonical edges form a strict chain so the visualizer
    # draws schema → requirements → ... → reporting.
    assert [(edge.from_step_id, edge.to_step_id) for edge in run.dag_edges] == [
        ("schema_analysis", "requirements_extraction"),
        ("requirements_extraction", "use_case_generation"),
        ("use_case_generation", "template_generation"),
        ("template_generation", "execution"),
        ("execution", "reporting"),
    ]
    # executor_kind stamped so future durable-executor migration can
    # tell which rows were produced by the in-process Phase 1 path.
    assert run.metadata["execution"]["executor_kind"] == "inprocess"
    assert run.metadata["execution"]["last_outcome"] == "pending"


def test_create_workflow_run_in_traditional_mode_keeps_user_steps():
    """Decision 1: traditional mode is intentionally untouched."""

    service, repository, run = _seed_workspace_and_run(
        workflow_mode=WorkflowMode.TRADITIONAL,
    )
    assert [step.step_id for step in run.steps] == ["user-typed"]
    # No execution metadata stamped — that's exclusive to agentic.
    assert "execution" not in (run.metadata or {})


# ---------------------------------------------------------------------------
# Decision 2 + 3: supervisor with fake runner + LLM factory seam
# ---------------------------------------------------------------------------


def test_supervisor_runs_canonical_steps_via_fake_runner_and_updates_status():
    """End-to-end: submit a fake runner, observe each step transition.

    Demonstrates that:
    * the supervisor builds a runner via the runner_factory injection
    * it passes the LLM provider produced by LLMProviderFactory
    * StepStatusReporter translates STEP_START → RUNNING and
      STEP_END → COMPLETED for each canonical phase
    * run.status rolls up to COMPLETED when the runner returns
    * execution.last_outcome is recorded as "completed"
    """

    service, repository, run = _seed_workspace_and_run()

    captured_factory_calls: List[Optional[str]] = []

    class _StubLLM:
        pass

    llm_factory = LLMProviderFactory(loader=lambda: _StubLLM())

    def runner_factory(**kwargs):
        # Assert the supervisor passed through what we expect.
        assert isinstance(kwargs["llm_provider"], _StubLLM)
        captured_factory_calls.append(kwargs.get("graph_name"))
        return _FakeRunner(
            events=[
                # Schema phase: start → end
                {
                    "event_type": TraceEventType.STEP_START,
                    "agent_name": WorkflowSteps.SCHEMA_ANALYSIS,
                },
                {
                    "event_type": TraceEventType.STEP_END,
                    "agent_name": WorkflowSteps.SCHEMA_ANALYSIS,
                    "duration_ms": 12.5,
                    "data": {"key_entities": 4},
                },
                # Requirements phase
                {
                    "event_type": TraceEventType.STEP_START,
                    "agent_name": WorkflowSteps.REQUIREMENTS_EXTRACTION,
                },
                {
                    "event_type": TraceEventType.STEP_END,
                    "agent_name": WorkflowSteps.REQUIREMENTS_EXTRACTION,
                },
                # Use cases
                {
                    "event_type": TraceEventType.STEP_START,
                    "agent_name": WorkflowSteps.USE_CASE_GENERATION,
                },
                {
                    "event_type": TraceEventType.STEP_END,
                    "agent_name": WorkflowSteps.USE_CASE_GENERATION,
                },
                # Templates
                {
                    "event_type": TraceEventType.STEP_START,
                    "agent_name": WorkflowSteps.TEMPLATE_GENERATION,
                },
                {
                    "event_type": TraceEventType.STEP_END,
                    "agent_name": WorkflowSteps.TEMPLATE_GENERATION,
                },
                # Execution
                {
                    "event_type": TraceEventType.STEP_START,
                    "agent_name": WorkflowSteps.EXECUTION,
                },
                {
                    "event_type": TraceEventType.STEP_END,
                    "agent_name": WorkflowSteps.EXECUTION,
                },
                # Reporting
                {
                    "event_type": TraceEventType.STEP_START,
                    "agent_name": WorkflowSteps.REPORTING,
                },
                {
                    "event_type": TraceEventType.STEP_END,
                    "agent_name": WorkflowSteps.REPORTING,
                },
            ],
        )

    supervisor = AgenticRunSupervisor(
        service=service,
        runner_factory=runner_factory,
        llm_provider_factory=llm_factory,
        max_workers=1,
    )
    service._agentic_run_supervisor = supervisor

    service.start_workflow_run(run.run_id)
    # Wait for the worker to drain. Bounded so a wedged supervisor
    # surfaces as a timeout instead of a hung test. The test
    # intentionally doesn't assert on a transient RUNNING state
    # right after start_workflow_run() because the worker thread can
    # finish before we observe it (FakeProductRepository shares
    # object refs across threads).
    handle = supervisor._handles[run.run_id]
    handle.future.result(timeout=5)
    supervisor.shutdown(wait=True, timeout_seconds=2)

    refreshed = repository.get_workflow_run(run.run_id)
    assert refreshed.status == WorkflowRunStatus.COMPLETED
    assert refreshed.metadata["execution"]["last_outcome"] == RUN_OUTCOME_COMPLETED

    # Each canonical step recorded a completed status with the
    # duration the runner emitted (where present).
    statuses = {step.step_id: step.status for step in refreshed.steps}
    for canonical in AGENTIC_STEP_LAYOUT:
        assert statuses[canonical.step_id] == WorkflowStepStatus.COMPLETED

    schema_step = next(
        step for step in refreshed.steps if step.step_id == "schema_analysis"
    )
    assert schema_step.cost.get("duration_ms") == 12.5
    assert schema_step.outputs.get("key_entities") == 4

    # Sanity: the LLM factory was the only source of the LLM provider
    # (decision 3 — the seam exists in Phase 1 even though the
    # workspace_id is currently ignored).
    assert captured_factory_calls == ["risk-graph"]


def test_runner_failure_marks_run_failed_with_error_recorded():
    """Decision 2: supervisor surfaces runner exceptions as FAILED."""

    service, repository, run = _seed_workspace_and_run()

    boom = RuntimeError("LLM provider disconnected")

    def runner_factory(**kwargs):
        return _FakeRunner(events=[], raise_at=boom)

    supervisor = AgenticRunSupervisor(
        service=service,
        runner_factory=runner_factory,
        llm_provider_factory=LLMProviderFactory(loader=lambda: object()),
        max_workers=1,
    )
    service._agentic_run_supervisor = supervisor

    service.start_workflow_run(run.run_id)
    supervisor._handles[run.run_id].future.result(timeout=5)
    supervisor.shutdown(wait=True, timeout_seconds=2)

    refreshed = repository.get_workflow_run(run.run_id)
    assert refreshed.status == WorkflowRunStatus.FAILED
    assert refreshed.metadata["execution"]["last_outcome"] == RUN_OUTCOME_FAILED
    assert any("LLM provider disconnected" in err for err in refreshed.errors)


# ---------------------------------------------------------------------------
# Decision 4: cancellation
# ---------------------------------------------------------------------------


def test_cancel_workflow_run_delivers_to_supervisor_when_owned():
    """Cancel signals the running fake runner via the cancel token.

    The fake runner pauses on ``__wait__`` so the main thread can fire
    the cancel between phases. After resume, the runner observes the
    set token at its next ``__check_cancel__`` event and raises
    WorkflowCancelled, which the supervisor maps to CANCELLED status.
    """

    service, repository, run = _seed_workspace_and_run()
    pause = threading.Event()

    def runner_factory(**kwargs):
        return _FakeRunner(
            events=[
                {
                    "event_type": TraceEventType.STEP_START,
                    "agent_name": WorkflowSteps.SCHEMA_ANALYSIS,
                },
                {
                    "event_type": TraceEventType.STEP_END,
                    "agent_name": WorkflowSteps.SCHEMA_ANALYSIS,
                },
                # Pause until the test fires the cancel.
                {"__wait__": True},
                # Then check the cancel token; the supervisor's cancel
                # set the threading.Event, so this will raise
                # WorkflowCancelled with observed_at_step=requirements_extraction.
                {
                    "__check_cancel__": True,
                    "step": WorkflowSteps.REQUIREMENTS_EXTRACTION,
                },
                # We should never get here.
                {
                    "event_type": TraceEventType.STEP_START,
                    "agent_name": WorkflowSteps.REQUIREMENTS_EXTRACTION,
                },
            ],
            wait_event=pause,
        )

    supervisor = AgenticRunSupervisor(
        service=service,
        runner_factory=runner_factory,
        llm_provider_factory=LLMProviderFactory(loader=lambda: object()),
        max_workers=1,
    )
    service._agentic_run_supervisor = supervisor

    service.start_workflow_run(run.run_id)

    # Wait until at least the schema_analysis STEP_END has been
    # processed by the reporter, then issue the cancel and let the
    # runner resume.
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        steps = {
            s.step_id: s.status
            for s in repository.get_workflow_run(run.run_id).steps
        }
        if steps["schema_analysis"] == WorkflowStepStatus.COMPLETED:
            break
        time.sleep(0.01)

    cancelled = service.cancel_workflow_run(run.run_id, actor="qa@example")
    pause.set()  # Let the worker proceed and observe the cancel.

    supervisor._handles[run.run_id].future.result(timeout=5)
    supervisor.shutdown(wait=True, timeout_seconds=2)

    final = repository.get_workflow_run(run.run_id)
    assert final.status == WorkflowRunStatus.CANCELLED
    assert final.metadata["execution"]["last_outcome"] == RUN_OUTCOME_CANCELLED
    # Audit trail records who initiated the cancel.
    actions = [event.action for event in repository.audit_events]
    assert "cancel_workflow_run" in actions
    assert cancelled.run_id == run.run_id


def test_cancel_workflow_run_falls_back_to_synchronous_when_no_supervisor():
    """If no supervisor owns the run, cancel still flips status synchronously.

    Covers the API-restart scenario: a run was started by a previous
    process and the new process has no in-memory handle. The user
    should still be able to cancel without the row sticking in
    RUNNING forever.
    """

    service, repository, run = _seed_workspace_and_run()
    # Note: no supervisor wired.

    service.start_workflow_run(run.run_id)
    cancelled = service.cancel_workflow_run(run.run_id)

    final = repository.get_workflow_run(run.run_id)
    assert final.status == WorkflowRunStatus.CANCELLED
    assert final.metadata["execution"]["cancel_path"] == "synchronous"
    assert cancelled.status == WorkflowRunStatus.CANCELLED


# ---------------------------------------------------------------------------
# Orphan sweep
# ---------------------------------------------------------------------------


def test_sweep_orphan_runs_flips_running_rows_to_failed():
    """Phase 1 in-process executor can't survive restart; sweep cleans up.

    This makes the visualizer honest: a row left in RUNNING after the
    API process restarted is by definition stale, and the sweep
    flips it to FAILED with a sentinel reason that the UI can show.
    """

    service, repository, run = _seed_workspace_and_run()

    # Repository extension required by sweep — equivalent to the
    # production storage's "list runs by status" query.
    def list_workflow_runs_by_status(status):
        return [
            r for r in repository.workflow_runs.values() if r.status == status
        ]

    repository.list_workflow_runs_by_status = list_workflow_runs_by_status  # type: ignore[attr-defined]

    # Mark the run as RUNNING (simulating a previous process started it).
    run.status = WorkflowRunStatus.RUNNING
    repository.update_workflow_run(run)

    supervisor = AgenticRunSupervisor(
        service=service,
        runner_factory=lambda **_: _FakeRunner(events=[]),
        llm_provider_factory=LLMProviderFactory(loader=lambda: object()),
        max_workers=1,
    )

    swept = supervisor.sweep_orphan_runs()
    supervisor.shutdown(wait=False)

    assert swept == [run.run_id]
    refreshed = repository.get_workflow_run(run.run_id)
    assert refreshed.status == WorkflowRunStatus.FAILED
    assert "stale_run_detected" in refreshed.errors
    assert refreshed.metadata["execution"]["last_outcome"] == RUN_OUTCOME_FAILED
    assert refreshed.metadata["execution"]["sweep_reason"] == "stale_run_detected"


def test_sweep_orphan_runs_is_a_noop_when_repository_lacks_status_query():
    """Defensive: sweep degrades gracefully on minimal repos."""

    service, repository, _ = _seed_workspace_and_run()
    supervisor = AgenticRunSupervisor(
        service=service,
        runner_factory=lambda **_: _FakeRunner(events=[]),
        llm_provider_factory=LLMProviderFactory(loader=lambda: object()),
        max_workers=1,
    )
    # FakeProductRepository doesn't implement list_workflow_runs_by_status
    # — sweep should return an empty list, not crash.
    assert supervisor.sweep_orphan_runs() == []
    supervisor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Status snapshot
# ---------------------------------------------------------------------------


def test_get_workflow_run_status_combines_persisted_state_and_supervisor_view():
    """The status endpoint surfaces both DB-side and supervisor-side state."""

    service, repository, run = _seed_workspace_and_run()

    class _SupervisorStub:
        def submit(self, run_id):
            return None

        def cancel(self, run_id):
            return False

        def get_status(self, run_id):
            return {
                "run_id": run_id,
                "supervised": True,
                "outcome": "running",
                "cancel_requested": False,
            }

    service._agentic_run_supervisor = _SupervisorStub()
    service.start_workflow_run(run.run_id)

    status = service.get_workflow_run_status(run.run_id)
    assert status["run_id"] == run.run_id
    assert status["status"] == "running"
    assert status["executor_kind"] == "inprocess"
    assert status["supervisor"] == {
        "run_id": run.run_id,
        "supervised": True,
        "outcome": "running",
        "cancel_requested": False,
    }


# ---------------------------------------------------------------------------
# Reporter direct unit test
# ---------------------------------------------------------------------------


def test_start_workflow_run_emits_audit_event_with_dispatch_metadata():
    """start_workflow_run records start in the audit log (FR-31a)."""

    service, repository, run = _seed_workspace_and_run()
    supervisor_stub_calls: List[str] = []

    class _SupervisorStub:
        def submit(self, run_id):
            supervisor_stub_calls.append(run_id)

        def cancel(self, run_id):
            return False

        def get_status(self, run_id):
            return {"supervised": True}

    service._agentic_run_supervisor = _SupervisorStub()

    service.start_workflow_run(run.run_id, actor="alice@example.com")

    starts = [e for e in repository.audit_events if e.action == "start_workflow_run"]
    assert len(starts) == 1
    event = starts[0]
    assert event.actor == "alice@example.com"
    assert event.target_type == "workflow_run"
    assert event.target_id == run.run_id
    assert event.metadata["workflow_mode"] == "agentic"
    assert event.metadata["dispatched_to_supervisor"] is True
    assert event.metadata["executor_kind"] == "inprocess"
    assert supervisor_stub_calls == [run.run_id]


def test_supervisor_finalize_emits_execute_workflow_audit_for_completed_run():
    """The supervisor records an execute_workflow audit on completion."""

    service, repository, run = _seed_workspace_and_run()

    def runner_factory(**kwargs):
        return _FakeRunner(events=[])

    supervisor = AgenticRunSupervisor(
        service=service,
        runner_factory=runner_factory,
        llm_provider_factory=LLMProviderFactory(loader=lambda: object()),
        max_workers=1,
    )
    service._agentic_run_supervisor = supervisor

    service.start_workflow_run(run.run_id)
    supervisor._handles[run.run_id].future.result(timeout=5)
    supervisor.shutdown(wait=True, timeout_seconds=2)

    executes = [e for e in repository.audit_events if e.action == "execute_workflow"]
    assert len(executes) == 1
    event = executes[0]
    assert event.actor == "workflow-runner"
    assert event.metadata["outcome"] == RUN_OUTCOME_COMPLETED
    assert event.metadata["step_count"] == 6
    assert event.metadata["error_message"] is None


def test_supervisor_finalize_emits_execute_workflow_audit_with_error_for_failed_run():
    """Failed runs record the error message in the audit metadata."""

    service, repository, run = _seed_workspace_and_run()
    boom = RuntimeError("LLM provider disconnected")

    def runner_factory(**kwargs):
        return _FakeRunner(events=[], raise_at=boom)

    supervisor = AgenticRunSupervisor(
        service=service,
        runner_factory=runner_factory,
        llm_provider_factory=LLMProviderFactory(loader=lambda: object()),
        max_workers=1,
    )
    service._agentic_run_supervisor = supervisor

    service.start_workflow_run(run.run_id)
    supervisor._handles[run.run_id].future.result(timeout=5)
    supervisor.shutdown(wait=True, timeout_seconds=2)

    executes = [e for e in repository.audit_events if e.action == "execute_workflow"]
    assert len(executes) == 1
    event = executes[0]
    assert event.metadata["outcome"] == RUN_OUTCOME_FAILED
    assert "LLM provider disconnected" in event.metadata["error_message"]


def test_supervisor_passes_kwargs_compatible_with_real_runner():
    """Pin the supervisor → AgenticWorkflowRunner contract.

    The fake runner used by the other tests accepts ``**kwargs``, so a
    typo like ``db=db`` instead of ``db_connection=db`` (which is the
    actual parameter name on AgenticWorkflowRunner.__init__) wouldn't
    surface there. This test introspects the real runner signature
    and asserts every kwarg the supervisor sends is a parameter the
    runner declares — so a future rename on either side fails loudly
    at the unit-test level instead of silently at run time inside a
    worker thread.
    """

    import inspect

    from graph_analytics_ai.ai.agents.runner import AgenticWorkflowRunner

    real_signature = inspect.signature(AgenticWorkflowRunner.__init__)
    declared_params = set(real_signature.parameters.keys())

    # Spy runner factory captures the kwargs the supervisor sends so
    # we can compare them against the real ctor signature.
    sent_kwargs: Dict[str, Any] = {}

    def spy_runner_factory(**kwargs):
        sent_kwargs.update(kwargs)
        return _FakeRunner(events=[])

    service, repository, run = _seed_workspace_and_run()
    supervisor = AgenticRunSupervisor(
        service=service,
        runner_factory=spy_runner_factory,
        llm_provider_factory=LLMProviderFactory(loader=lambda: object()),
        max_workers=1,
    )
    service._agentic_run_supervisor = supervisor

    service.start_workflow_run(run.run_id)
    supervisor._handles[run.run_id].future.result(timeout=5)
    supervisor.shutdown(wait=True, timeout_seconds=2)

    assert sent_kwargs, "supervisor must call its runner factory"
    unknown = set(sent_kwargs.keys()) - declared_params
    assert not unknown, (
        f"supervisor passed kwargs {unknown!r} that AgenticWorkflowRunner.__init__ "
        f"does not accept. Real signature: {sorted(declared_params)}"
    )

    # Spot-check that the critical wiring made it through with the
    # correct names — these are the ones a typo would break first.
    assert "db_connection" in sent_kwargs
    assert "llm_provider" in sent_kwargs
    assert "graph_name" in sent_kwargs
    assert "enable_tracing" in sent_kwargs


def test_supervisor_pulls_core_and_satellite_collections_from_graph_profile_roles():
    """Role-tagged collections flow into the runner ctor by category."""

    service, repository, run = _seed_workspace_and_run()

    # Tag the graph profile with role labels and update through the
    # repository so the supervisor reads the updated copy.
    graph_profile = next(iter(repository.graph_profiles))
    graph_profile.collection_roles = {
        "Device": ["core"],
        "Account": ["primary"],
        "AuditLog": ["satellite"],
        "Region": ["lookup"],
        "Misc": ["unrelated"],
    }

    captured: Dict[str, Any] = {}

    def spy_runner_factory(**kwargs):
        captured.update(kwargs)
        return _FakeRunner(events=[])

    supervisor = AgenticRunSupervisor(
        service=service,
        runner_factory=spy_runner_factory,
        llm_provider_factory=LLMProviderFactory(loader=lambda: object()),
        max_workers=1,
    )
    service._agentic_run_supervisor = supervisor

    service.start_workflow_run(run.run_id)
    supervisor._handles[run.run_id].future.result(timeout=5)
    supervisor.shutdown(wait=True, timeout_seconds=2)

    # Order isn't guaranteed (dict iteration), so compare sets.
    assert set(captured["core_collections"]) == {"Device", "Account"}
    assert set(captured["satellite_collections"]) == {"AuditLog", "Region"}


def test_step_status_reporter_translates_each_event_type():
    """Pin down the exact translation from trace event → step update."""

    service, repository, run = _seed_workspace_and_run()
    recorded = _RecordingService(service)
    reporter = StepStatusReporter(run_id=run.run_id, service=recorded)

    collector = TraceCollector("test")
    collector.add_listener(reporter)

    # Unknown phase: ignored.
    collector.record_event(TraceEventType.STEP_START, agent_name="something_else")
    # WORKFLOW_START has no agent_name, also ignored.
    collector.record_event(TraceEventType.WORKFLOW_START)
    # Real phase events.
    collector.record_event(
        TraceEventType.STEP_START, agent_name=WorkflowSteps.SCHEMA_ANALYSIS
    )
    collector.record_event(
        TraceEventType.STEP_END,
        agent_name=WorkflowSteps.SCHEMA_ANALYSIS,
        data={"step": WorkflowSteps.SCHEMA_ANALYSIS, "summary": "ok"},
        duration_ms=42.0,
    )
    collector.record_event(
        TraceEventType.AGENT_ERROR,
        agent_name=WorkflowSteps.REQUIREMENTS_EXTRACTION,
        data={"error": "missing input"},
    )

    # Three step updates routed (start, end, error). Unknown / no-name
    # events were dropped.
    assert len(recorded.calls) == 3

    start_call = recorded.calls[0]
    assert start_call["status"] == WorkflowStepStatus.RUNNING
    assert start_call["step_id"] == "schema_analysis"

    end_call = recorded.calls[1]
    assert end_call["status"] == WorkflowStepStatus.COMPLETED
    assert end_call["cost"] == {"duration_ms": 42.0}
    # data["step"] is filtered out so it doesn't pollute outputs
    assert end_call["outputs"] == {"summary": "ok"}

    error_call = recorded.calls[2]
    assert error_call["status"] == WorkflowStepStatus.FAILED
    assert error_call["errors"] == ["missing input"]
