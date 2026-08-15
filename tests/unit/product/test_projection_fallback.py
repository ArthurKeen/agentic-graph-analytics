"""Tests for the FR-71 projection fallback chain.

The chain is inline_aql -> materialized -> whole collections.

The PRD calls tier 2 a "server-side view fallback", but GAE's loaddata takes
collection names and cannot load an ArangoSearch view, so the implementation
materializes the typed projection into real collections instead — same intent,
via a mechanism the engine supports. The materialization AQL is idempotent
UPSERT against a deterministic collection name, which is also what makes a
projection reusable across runs.
"""

from graph_analytics_ai.gae_orchestrator import GAEOrchestrator


class _FakeAql:
    def __init__(self):
        self.executed = []

    def execute(self, aql, bind_vars=None):
        self.executed.append(aql)
        return []


class _FakeDb:
    def __init__(self, existing=()):
        self.aql = _FakeAql()
        self._existing = set(existing)
        self.created = []

    def has_collection(self, name):
        return name in self._existing

    def create_collection(self, name, edge=False):
        self.created.append((name, edge))
        self._existing.add(name)


class _FakeGae:
    def __init__(self, db, supports_aql=False, aql_load_raises=False):
        self._db = db
        self._supports_aql = supports_aql
        self._aql_load_raises = aql_load_raises
        self.load_graph_calls = []

    def get_db(self):
        return self._db

    def supports_aql_load(self):
        return self._supports_aql

    def load_graph_aql(self, **kwargs):
        if self._aql_load_raises:
            raise RuntimeError("loaddataaql unavailable")
        return {"graph_id": "g-inline"}

    def load_graph(self, **kwargs):
        self.load_graph_calls.append(kwargs)
        return {"graph_id": "g-loaded"}


def _orchestrator(gae):
    orchestrator = GAEOrchestrator.__new__(GAEOrchestrator)
    orchestrator.gae = gae
    orchestrator._log = lambda *_args, **_kwargs: None
    return orchestrator


class _Config:
    database = "demo"
    vertex_collections = ["Entities"]
    edge_collections = ["Relationships"]
    vertex_attributes = None
    graph_name = None
    load_strategy = "auto"

    def __init__(self, projections):
        self.lpg_projections = projections


class _Result:
    def __init__(self, projections):
        self.config = _Config(projections)
        self.projection = None


# Full LpgProjection.to_dict shape: source_collection / discriminator_field /
# discriminator_value are what build_aql_load_phases needs to emit inline
# phases, and materialization_* are what the tier-2 fallback needs. A fixture
# missing the former silently skips inline and would make an "inline wins"
# assertion vacuous.
_PROJECTIONS = [
    {
        "logical_type": "Person",
        "kind": "node",
        "source_collection": "Entities",
        "discriminator_field": "type",
        "discriminator_value": "Person",
        "materialization_collection": "proj_Person",
        "materialization_aql": "UPSERT {} INSERT {} UPDATE {} IN proj_Person",
    },
    {
        "logical_type": "WORKS_AT",
        "kind": "edge",
        "source_collection": "Relationships",
        "discriminator_field": "type",
        "discriminator_value": "WORKS_AT",
        "materialization_collection": "proj_WORKS_AT",
        "materialization_aql": "UPSERT {} INSERT {} UPDATE {} IN proj_WORKS_AT",
    },
]


def test_materialized_tier_is_used_when_inline_aql_is_unavailable():
    db = _FakeDb()
    gae = _FakeGae(db, supports_aql=False)
    result = _Result(_PROJECTIONS)

    _orchestrator(gae)._load_graph_data(result)

    assert result.projection["strategy"] == "materialized"
    # Node and edge projections are created with the right collection type.
    assert ("proj_Person", False) in db.created
    assert ("proj_WORKS_AT", True) in db.created
    assert len(db.aql.executed) == 2
    loaded = gae.load_graph_calls[0]
    assert loaded["vertex_collections"] == ["proj_Person"]
    assert loaded["edge_collections"] == ["proj_WORKS_AT"]


def test_inline_aql_still_wins_when_the_engine_supports_it():
    db = _FakeDb()
    gae = _FakeGae(db, supports_aql=True)
    result = _Result(_PROJECTIONS)

    _orchestrator(gae)._load_graph_data(result)

    assert result.projection["strategy"] == "inline_aql"
    # Nothing was materialized — inline load avoids writing to the database.
    assert db.created == []


def test_materialized_tier_catches_a_failing_inline_load():
    db = _FakeDb()
    gae = _FakeGae(db, supports_aql=True, aql_load_raises=True)
    result = _Result(_PROJECTIONS)

    _orchestrator(gae)._load_graph_data(result)

    assert result.projection["strategy"] == "materialized"


def test_existing_projection_collections_are_reused_across_runs():
    """Re-running over unchanged data is a no-op UPSERT, not a rebuild."""

    db = _FakeDb(existing=["proj_Person", "proj_WORKS_AT"])
    gae = _FakeGae(db, supports_aql=False)
    result = _Result(_PROJECTIONS)

    _orchestrator(gae)._load_graph_data(result)

    assert db.created == []
    assert result.projection["reused"] == ["proj_Person", "proj_WORKS_AT"]


def test_falls_through_to_whole_collections_when_materialization_fails():
    class _BrokenDb(_FakeDb):
        def __init__(self):
            super().__init__()

            class _BrokenAql:
                def execute(self, *_a, **_k):
                    raise RuntimeError("no write permission")

            self.aql = _BrokenAql()

    db = _BrokenDb()
    gae = _FakeGae(db, supports_aql=False)
    result = _Result(_PROJECTIONS)

    _orchestrator(gae)._load_graph_data(result)

    assert result.projection["strategy"] == "collections_fallback"
    # The original source collections were loaded, not the projections.
    assert gae.load_graph_calls[0]["vertex_collections"] == ["Entities"]


def test_no_projections_loads_whole_collections_without_materializing():
    db = _FakeDb()
    gae = _FakeGae(db, supports_aql=True)
    result = _Result([])

    _orchestrator(gae)._load_graph_data(result)

    assert db.created == []
    assert gae.load_graph_calls[0]["vertex_collections"] == ["Entities"]
