"""Tests for inline-AQL graph loading (PRD v0.7 / FR-71, FR-74).

Covers:
- ``build_aql_load_phases`` phase/query construction from projection specs.
- ``GenAIGAEConnection.load_graph_aql`` payload + ``supports_aql_load`` toggle.
- ``GAEOrchestrator._load_graph_data`` strategy selection and fallback.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from graph_analytics_ai.gae_orchestrator import (
    AnalysisConfig,
    AnalysisResult,
    AnalysisStatus,
    GAEOrchestrator,
    build_aql_load_phases,
)


# --------------------------------------------------------------------------
# build_aql_load_phases
# --------------------------------------------------------------------------


def test_build_phases_vertices_then_edges():
    projections = [
        {
            "logical_type": "Person",
            "source_collection": "entities",
            "discriminator_field": "type",
            "discriminator_value": "Person",
            "kind": "node",
        },
        {
            "logical_type": "WORKS_FOR",
            "source_collection": "relationships",
            "discriminator_field": "relType",
            "discriminator_value": "WORKS_FOR",
            "kind": "edge",
        },
    ]

    phases = build_aql_load_phases(projections)

    # Two phases: vertices first, edges second.
    assert len(phases) == 2
    vertex_q = phases[0]["queries"][0]
    edge_q = phases[1]["queries"][0]

    assert "vertices: [doc]" in vertex_q["query"]
    assert "FILTER doc.`type` == @value" in vertex_q["query"]
    assert vertex_q["bind_vars"] == {"value": "Person"}

    assert "edges:" in edge_q["query"]
    assert "_from: doc._from" in edge_q["query"]
    assert edge_q["bind_vars"] == {"value": "WORKS_FOR"}


def test_build_phases_skips_incomplete_specs():
    projections = [
        {"source_collection": "entities"},  # missing field/value
        {
            "source_collection": "entities",
            "discriminator_field": "type",
            "discriminator_value": "Org",
            "kind": "node",
        },
    ]
    phases = build_aql_load_phases(projections)
    assert len(phases) == 1
    assert len(phases[0]["queries"]) == 1


def test_build_phases_empty():
    assert build_aql_load_phases([]) == []
    assert build_aql_load_phases(None) == []


# --------------------------------------------------------------------------
# Connection: load_graph_aql payload + capability toggle
# --------------------------------------------------------------------------


@patch("graph_analytics_ai.gae_connection.get_arango_config")
def test_load_graph_aql_payload(mock_get_config, mock_env_self_managed):
    from graph_analytics_ai.gae_connection import GenAIGAEConnection

    mock_get_config.return_value = {
        "endpoint": "https://test.com:8529",
        "database": "testdb",
        "user": "u",
        "password": "p",
    }
    gae = GenAIGAEConnection()
    gae.engine_id = "engine-1"  # skip service bootstrap

    captured = {}

    def fake_make_request(method, endpoint, payload=None, **kwargs):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["payload"] = payload
        return {"job_id": "j1", "graph_id": "g1"}

    phases = [{"queries": [{"query": "FOR v IN c RETURN {vertices: [v]}", "bind_vars": {}}]}]

    with patch.object(gae, "_make_request", side_effect=fake_make_request), patch.object(
        gae, "_get_engine_url", return_value="http://engine"
    ), patch.object(gae, "_get_headers", return_value={}):
        result = gae.load_graph_aql(database="testdb", phases=phases, parallelism=8)

    assert captured["method"] == "POST"
    assert captured["endpoint"].endswith("loaddataaql")
    assert captured["payload"]["database"] == "testdb"
    assert captured["payload"]["phases"] == phases
    assert captured["payload"]["parallelism"] == 8
    # vertex_attributes / edge_attributes are required by the GAE body even
    # when empty (omitting them returns a 400 missing-field error).
    assert captured["payload"]["vertex_attributes"] == []
    assert captured["payload"]["edge_attributes"] == []
    assert result["graph_id"] == "g1"


@patch("graph_analytics_ai.gae_connection.get_arango_config")
def test_load_graph_aql_requires_phases(mock_get_config, mock_env_self_managed):
    from graph_analytics_ai.gae_connection import GenAIGAEConnection

    mock_get_config.return_value = {
        "endpoint": "https://test.com:8529",
        "database": "testdb",
        "user": "u",
        "password": "p",
    }
    gae = GenAIGAEConnection()
    gae.engine_id = "engine-1"
    with pytest.raises(ValueError):
        gae.load_graph_aql(database="testdb", phases=[])


@patch("graph_analytics_ai.gae_connection.get_arango_config")
def test_supports_aql_load_env_toggle(mock_get_config, mock_env_self_managed, monkeypatch):
    from graph_analytics_ai.gae_connection import GenAIGAEConnection

    mock_get_config.return_value = {
        "endpoint": "https://test.com:8529",
        "database": "testdb",
        "user": "u",
        "password": "p",
    }
    gae = GenAIGAEConnection()

    monkeypatch.delenv("GAE_DISABLE_LOADDATAAQL", raising=False)
    assert gae.supports_aql_load() is True

    monkeypatch.setenv("GAE_DISABLE_LOADDATAAQL", "true")
    assert gae.supports_aql_load() is False


# --------------------------------------------------------------------------
# Orchestrator: strategy selection + fallback
# --------------------------------------------------------------------------


class _FakeGAE:
    def __init__(self, supports=True, aql_raises=False):
        self._supports = supports
        self._aql_raises = aql_raises
        self.aql_calls = []
        self.collection_calls = []

    def supports_aql_load(self):
        return self._supports

    def load_graph_aql(self, **kwargs):
        if self._aql_raises:
            raise RuntimeError("loaddataaql not available")
        self.aql_calls.append(kwargs)
        return {"graph_id": "g-aql", "job_id": None}

    def load_graph(self, **kwargs):
        self.collection_calls.append(kwargs)
        return {"graph_id": "g-coll", "job_id": None}


def _orchestrator_with(gae):
    orch = object.__new__(GAEOrchestrator)
    orch.gae = gae
    orch._log = lambda *a, **k: None
    return orch


def _result_with_projections(projections, strategy="auto"):
    config = AnalysisConfig(
        name="t",
        algorithm="pagerank",
        vertex_collections=["entities"],
        edge_collections=["relationships"],
        database="testdb",
        lpg_projections=projections,
        load_strategy=strategy,
    )
    return AnalysisResult(
        config=config, status=AnalysisStatus.PENDING, start_time=datetime.now()
    )


_PROJ = [
    {
        "logical_type": "Person",
        "source_collection": "entities",
        "discriminator_field": "type",
        "discriminator_value": "Person",
        "kind": "node",
    }
]


def test_orchestrator_uses_inline_aql_when_supported():
    gae = _FakeGAE(supports=True)
    orch = _orchestrator_with(gae)
    result = _result_with_projections(_PROJ)

    info = orch._load_graph_data(result)

    assert info["graph_id"] == "g-aql"
    assert len(gae.aql_calls) == 1
    assert not gae.collection_calls
    assert result.projection["strategy"] == "inline_aql"
    assert result.projection["logical_types"] == ["Person"]


def test_orchestrator_falls_back_when_unsupported():
    gae = _FakeGAE(supports=False)
    orch = _orchestrator_with(gae)
    result = _result_with_projections(_PROJ)

    info = orch._load_graph_data(result)

    assert info["graph_id"] == "g-coll"
    assert not gae.aql_calls
    assert len(gae.collection_calls) == 1
    assert result.projection["strategy"] == "collections_fallback"


def test_orchestrator_falls_back_when_aql_raises():
    gae = _FakeGAE(supports=True, aql_raises=True)
    orch = _orchestrator_with(gae)
    result = _result_with_projections(_PROJ)

    info = orch._load_graph_data(result)

    assert info["graph_id"] == "g-coll"
    assert len(gae.collection_calls) == 1


def test_orchestrator_pg_path_no_projection_metadata():
    gae = _FakeGAE(supports=True)
    orch = _orchestrator_with(gae)
    result = _result_with_projections([])  # PG: no projections

    info = orch._load_graph_data(result)

    assert info["graph_id"] == "g-coll"
    assert not gae.aql_calls
    assert result.projection is None


# --------------------------------------------------------------------------
# Executor: projection provenance surfaces onto the job (catalog lineage)
# --------------------------------------------------------------------------


class _FakeOrchestrator:
    def __init__(self, projection):
        self._projection = projection

    def run_analysis(self, config):
        return AnalysisResult(
            config=config,
            status=AnalysisStatus.CLEANING_UP,
            start_time=datetime.now(),
            job_id="job-1",
            duration_seconds=1.0,
            projection=self._projection,
        )


def test_executor_surfaces_projection_into_job_metadata():
    from graph_analytics_ai.ai.execution.executor import AnalysisExecutor
    from graph_analytics_ai.ai.execution.models import ExecutionConfig
    from graph_analytics_ai.ai.templates.models import (
        AnalysisTemplate,
        AlgorithmParameters,
        AlgorithmType,
        TemplateConfig,
    )

    proj = {"strategy": "inline_aql", "phase_count": 2, "logical_types": ["ORG"]}
    executor = AnalysisExecutor(
        config=ExecutionConfig(auto_collect_results=False),
        orchestrator=_FakeOrchestrator(proj),
        auto_track=False,
    )
    template = AnalysisTemplate(
        name="t",
        description="d",
        algorithm=AlgorithmParameters(algorithm=AlgorithmType.PAGERANK, parameters={}),
        config=TemplateConfig(
            graph_name="g",
            vertex_collections=["Node"],
            edge_collections=["relations"],
        ),
    )

    result = executor.execute_template(template, wait=True)

    assert result.success
    assert result.job.metadata.get("projection") == proj
