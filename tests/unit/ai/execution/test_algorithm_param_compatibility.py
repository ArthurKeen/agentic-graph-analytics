"""Tuning parameters must never crash an analysis.

`GAEOrchestrator._run_algorithm` splats `algorithm_params` into a typed engine
method, but those names are authored in a different module
(`TemplateGenerator._optimize_parameters`). That split produced three names no
engine method accepts — `max_iterations` and `sample_size` (observed killing a
FinReflectKG run) and `threshold` (latent: only emitted when avg_degree > 10).
A tuning knob is advisory; losing the analysis over one is not acceptable.
"""

import inspect

import pytest

from graph_analytics_ai.gae_connection import GAEConnectionBase
from graph_analytics_ai.gae_orchestrator import GAEOrchestrator
from graph_analytics_ai.ai.templates.generator import TemplateGenerator

ALGORITHMS = ["pagerank", "label_propagation", "betweenness", "scc", "wcc"]


def _accepted(algorithm: str) -> set:
    method = getattr(GAEConnectionBase, f"run_{algorithm}")
    return set(inspect.signature(method).parameters) - {"self"}


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_generator_emits_only_accepted_parameter_names(algorithm):
    """Every name the template optimizer can emit must exist on the engine API.

    Drives the real optimizer across graph sizes and densities so the
    size-conditional branches (the `threshold` one needs avg_degree > 10) are
    all exercised, rather than asserting against a hand-copied list.
    """
    gen = TemplateGenerator.__new__(TemplateGenerator)
    accepted = _accepted(algorithm)

    for total_docs, avg_degree in [(500, 2), (50_000, 20), (5_000_000, 6)]:
        params = _emit(gen, algorithm, total_docs, avg_degree)
        unknown = set(params) - accepted
        assert not unknown, (
            f"run_{algorithm}() would reject {sorted(unknown)} "
            f"(total_docs={total_docs}, avg_degree={avg_degree}); "
            f"accepted: {sorted(accepted)}"
        )


def _emit(gen, algorithm, total_docs, avg_degree):
    """Call the real optimizer with a schema shaped to hit each size branch."""
    from types import SimpleNamespace

    from graph_analytics_ai.ai.templates.models import AlgorithmType

    algo_type = {
        "pagerank": AlgorithmType.PAGERANK,
        "label_propagation": AlgorithmType.LABEL_PROPAGATION,
        "betweenness": AlgorithmType.BETWEENNESS_CENTRALITY,
        "scc": AlgorithmType.SCC,
        "wcc": AlgorithmType.WCC,
    }[algorithm]

    # The optimizer reads only these two fields and derives
    # avg_degree = 2 * total_edges / total_documents.
    schema = SimpleNamespace(
        total_documents=total_docs,
        total_edges=int(avg_degree * total_docs / 2),
    )
    return TemplateGenerator._optimize_parameters(gen, algo_type, {}, schema) or {}


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_orchestrator_drops_unknown_params_instead_of_raising(algorithm):
    """An unknown tuning key is dropped with a warning, not raised."""

    class _StubGAE:
        def run_pagerank(
            self, graph_id, damping_factor=0.85, maximum_supersteps=100
        ): ...
        def run_label_propagation(self, graph_id, maximum_supersteps=100): ...
        def run_betweenness(self, graph_id, maximum_supersteps=100): ...
        def run_scc(self, graph_id): ...
        def run_wcc(self, graph_id): ...

    orch = GAEOrchestrator.__new__(GAEOrchestrator)
    orch.gae = _StubGAE()
    logged = []
    orch._log = lambda msg, level="INFO": logged.append(msg)

    dirty = {
        "graph_id": "g1",
        "max_iterations": 30,
        "sample_size": 1000,
        "threshold": 0.0005,
    }
    cleaned = orch._accepted_params(algorithm, dirty)

    assert cleaned["graph_id"] == "g1"
    assert not {"max_iterations", "sample_size", "threshold"} & set(cleaned)
    assert any("does not accept" in m for m in logged)
    # The filtered params must actually be callable on the real signature.
    getattr(_StubGAE(), f"run_{algorithm}")(**cleaned)
