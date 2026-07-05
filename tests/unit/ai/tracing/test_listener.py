"""Tests for the TraceCollector listener subscription API.

The listener API exists so the product-layer ``StepStatusReporter``
can translate runner trace events into ``WorkflowStep`` status
transitions without monkey-patching ``record_event``. These tests
pin down the contract that reporter relies on:

* listeners receive every event in order
* listeners are isolated from each other (one raising does not
  starve others, nor break ``record_event``)
* listeners can be removed and idempotent removes are no-ops
"""

from graph_analytics_ai.ai.tracing import TraceCollector, TraceEventType


def test_add_listener_receives_each_event_in_order():
    collector = TraceCollector("workflow-test")
    received = []

    collector.add_listener(received.append)

    collector.record_event(TraceEventType.WORKFLOW_START)
    collector.record_event(TraceEventType.STEP_START, agent_name="schema")
    collector.record_event(TraceEventType.STEP_END, agent_name="schema")

    assert [event.event_type for event in received] == [
        TraceEventType.WORKFLOW_START,
        TraceEventType.STEP_START,
        TraceEventType.STEP_END,
    ]
    # The agent_name on STEP_START should reach the listener verbatim
    # so the reporter can route by phase name.
    assert received[1].agent_name == "schema"


def test_add_listener_is_idempotent():
    collector = TraceCollector("workflow-test")
    received = []

    listener = received.append
    collector.add_listener(listener)
    # Second add must not double-fire — the reporter relies on this
    # so callers don't have to track subscription state.
    collector.add_listener(listener)

    collector.record_event(TraceEventType.WORKFLOW_START)

    assert len(received) == 1


def test_listener_exception_does_not_break_record_event_or_other_listeners():
    collector = TraceCollector("workflow-test")
    received_good = []

    def bad_listener(event):  # noqa: ARG001 - intentionally raises
        raise RuntimeError("boom")

    collector.add_listener(bad_listener)
    collector.add_listener(received_good.append)

    # Must not raise.
    collector.record_event(TraceEventType.WORKFLOW_START)
    collector.record_event(TraceEventType.WORKFLOW_END)

    # The good listener still gets both events.
    assert len(received_good) == 2
    # And the trace itself is intact.
    assert len(collector.trace.events) == 2


def test_remove_listener_stops_delivery_and_unknown_remove_is_noop():
    collector = TraceCollector("workflow-test")
    received = []
    listener = received.append

    collector.add_listener(listener)
    collector.record_event(TraceEventType.WORKFLOW_START)

    collector.remove_listener(listener)
    collector.record_event(TraceEventType.WORKFLOW_END)

    assert [e.event_type for e in received] == [TraceEventType.WORKFLOW_START]

    # Removing a listener that was never added must not raise so
    # cleanup paths can be unconditional.
    collector.remove_listener(lambda _e: None)
