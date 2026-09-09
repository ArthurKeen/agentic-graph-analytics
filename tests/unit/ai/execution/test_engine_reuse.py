"""Opt-in engine/graph reuse in GAEOrchestrator.

A FinReflect demo run deployed 34 engines at ~55s each for analyses that all
read the same two collections, and the platform began returning 503s partway
through. Reuse mode shares one engine and one loaded graph across calls; it is
off by default so existing callers are unaffected.
"""

from unittest.mock import MagicMock

import pytest

from graph_analytics_ai.gae_orchestrator import AnalysisConfig, GAEOrchestrator


def _config(name: str, algorithm: str = "pagerank", **overrides) -> AnalysisConfig:
    args = {
        "name": name,
        "algorithm": algorithm,
        "description": name,
        "vertex_collections": ["Node"],
        "edge_collections": ["relations"],
        "database": "FinReflectKgOneShard",
        "graph_name": "FinReflectKG",
        "retry_on_failure": False,
        "max_retries": 0,
    }
    args.update(overrides)
    return AnalysisConfig(**args)


@pytest.fixture
def orchestrator_factory(monkeypatch):
    """Build an orchestrator whose GAE calls are all stubbed."""

    def build(reuse_engine: bool):
        orch = GAEOrchestrator(verbose=False, reuse_engine=reuse_engine)
        gae = MagicMock()
        gae.deploy_engine.side_effect = [{"id": f"engine-{i}"} for i in range(1, 50)]
        gae.load_graph.side_effect = [{"graph_id": f"g{i}"} for i in range(1, 50)]
        orch.gae = gae
        # Neutralise everything after the load; reuse only concerns deploy/load.
        monkeypatch.setattr(orch, "_initialize_connections", lambda: None)
        monkeypatch.setattr(orch, "_check_existing_engines", lambda: None)
        monkeypatch.setattr(orch, "_run_algorithm", lambda result: None)
        monkeypatch.setattr(orch, "_store_results", lambda result: None)
        monkeypatch.setattr(orch, "_validate_results", lambda result: None)
        monkeypatch.setattr(orch, "_cleanup_engine", lambda result: None)
        return orch, gae

    return build


def test_reuse_mode_deploys_one_engine_and_loads_the_graph_once(orchestrator_factory):
    orch, gae = orchestrator_factory(reuse_engine=True)

    for name in ("pagerank-run", "wcc-run", "scc-run"):
        orch.run_analysis(_config(name))

    assert gae.deploy_engine.call_count == 1
    assert gae.load_graph.call_count == 1
    # The engine is deliberately NOT released per analysis.
    assert gae.delete_engine.call_count == 0


def test_default_mode_is_unchanged(orchestrator_factory):
    """Existing callers must keep deploy-per-analysis."""

    orch, gae = orchestrator_factory(reuse_engine=False)

    for name in ("a", "b", "c"):
        orch.run_analysis(_config(name))

    assert gae.deploy_engine.call_count == 3
    assert gae.load_graph.call_count == 3


def test_a_different_collection_set_is_loaded_separately(orchestrator_factory):
    """Reuse is keyed on what determines the projection, not just the engine."""

    orch, gae = orchestrator_factory(reuse_engine=True)

    orch.run_analysis(_config("first"))
    orch.run_analysis(_config("second", vertex_collections=["Other"]))

    assert gae.deploy_engine.call_count == 1  # same engine
    assert gae.load_graph.call_count == 2  # different projection


def test_shutdown_releases_the_shared_engine(orchestrator_factory):
    orch, gae = orchestrator_factory(reuse_engine=True)
    orch.run_analysis(_config("only"))

    assert orch.shutdown() is True
    gae.delete_engine.assert_called_once_with("engine-1")
    # Idempotent: nothing held, nothing deleted, no raise.
    assert orch.shutdown() is True
    assert gae.delete_engine.call_count == 1


def test_shutdown_never_raises_when_release_fails(orchestrator_factory):
    """A failure here must not mask the error that prompted the shutdown."""

    orch, gae = orchestrator_factory(reuse_engine=True)
    orch.run_analysis(_config("only"))
    gae.delete_engine.side_effect = RuntimeError("platform unavailable")

    assert orch.shutdown() is False
