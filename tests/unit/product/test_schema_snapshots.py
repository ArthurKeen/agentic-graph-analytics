"""Unit tests for the v0.6 schema-snapshot persistence layer.

Covers:

- :class:`SchemaSnapshot` round-trip and the create_schema_snapshot helper.
- :class:`GraphProfile` round-trip with the v0.6 additive fields populated
  AND with them omitted (back-compat with v0.5 documents).
- :class:`WorkspaceSchemaCache` adapter — get/set/invalidate semantics
  against a fake repository, ensuring it satisfies the SchemaCache
  Protocol contract used by ``acquire_schema``.
- ``discover_graph_profile`` stamps schema_kind / conceptual_schema /
  physical_mapping / analyzer_metadata / schema_snapshot_id when the
  acquisition succeeds, and omits them when it fails (graceful
  degradation).
- ``get_graph_profile_schema_change`` returns a SchemaChangeView with
  the right status without mutating the cache.
- ``GET /api/graph-profiles/{id}/schema-change`` is registered and
  dispatches to the service method.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from graph_analytics_ai.ai.schema.acquire import (
    InMemorySchemaCache,
    SchemaAcquisitionBundle,
    cache_key,
    reset_default_cache,
)
from graph_analytics_ai.product import (
    PRODUCT_API_ENDPOINTS,
    GraphProfile,
    ProductAPIDispatcher,
    SchemaSnapshot,
    WorkspaceSchemaCache,
    create_graph_profile,
    create_schema_snapshot,
)
from graph_analytics_ai.product.api import ProductAPIEndpoint
from graph_analytics_ai.product.constants import (
    PRODUCT_COLLECTIONS,
    SCHEMA_SNAPSHOTS_COLLECTION,
)
from graph_analytics_ai.product.service import SchemaChangeView

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_default_cache():
    reset_default_cache()
    yield
    reset_default_cache()


def _bundle(
    *,
    database: str = "hr_demo",
    graph_name: str = "acme_kg",
    schema_kind: str = "lpg",
    shape: str = "SHAPE_AAA",
    full: str = "FULL_AAA",
    source: str = "analyzer_baseline",
) -> SchemaAcquisitionBundle:
    return SchemaAcquisitionBundle(
        schema_kind=schema_kind,  # type: ignore[arg-type]
        conceptual_schema={
            "entities": [{"name": "Person", "labels": ["Person"], "properties": []}],
            "relationships": [
                {
                    "type": "WORKS_FOR",
                    "fromEntity": "Person",
                    "toEntity": "Org",
                    "properties": [],
                }
            ],
            "properties": [],
        },
        physical_mapping={
            "entities": {
                "Person": {
                    "style": "LABEL",
                    "collectionName": "Entities",
                    "typeField": "type",
                    "typeValue": "Person",
                }
            },
            "relationships": {
                "WORKS_FOR": {
                    "style": "GENERIC_WITH_TYPE",
                    "edgeCollectionName": "Relationships",
                    "typeField": "type",
                    "typeValue": "WORKS_FOR",
                }
            },
        },
        analyzer_metadata={"source": source, "confidence": 0.85, "warnings": []},
        shape_fingerprint=shape,
        full_fingerprint=full,
        database=database,
        graph_name=graph_name,
    )


class _FakeRepository:
    """In-memory stand-in for ProductRepository.

    Implements only the SchemaSnapshot CRUD surface that
    :class:`WorkspaceSchemaCache` consumes. Records each call so the
    tests can assert behavior without standing up an ArangoDB.
    """

    def __init__(self) -> None:
        self._snapshots: Dict[str, SchemaSnapshot] = {}
        self._by_cache_key: Dict[str, str] = {}
        self.create_calls: List[SchemaSnapshot] = []
        self.update_calls: List[SchemaSnapshot] = []
        self.delete_calls: List[str] = []

    def create_schema_snapshot(self, snapshot: SchemaSnapshot) -> str:
        self.create_calls.append(snapshot)
        self._snapshots[snapshot.schema_snapshot_id] = snapshot
        self._by_cache_key[snapshot.cache_key] = snapshot.schema_snapshot_id
        return snapshot.schema_snapshot_id

    def update_schema_snapshot(self, snapshot: SchemaSnapshot) -> str:
        self.update_calls.append(snapshot)
        self._snapshots[snapshot.schema_snapshot_id] = snapshot
        return snapshot.schema_snapshot_id

    def get_schema_snapshot_by_cache_key(self, key: str) -> Optional[SchemaSnapshot]:
        sid = self._by_cache_key.get(key)
        if sid is None:
            return None
        return self._snapshots.get(sid)

    def delete_schema_snapshot_by_cache_key(self, key: str) -> int:
        self.delete_calls.append(key)
        sid = self._by_cache_key.pop(key, None)
        if sid is None:
            return 0
        self._snapshots.pop(sid, None)
        return 1


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_schema_snapshots_collection_listed(self):
        assert SCHEMA_SNAPSHOTS_COLLECTION == "aga_schema_snapshots"
        assert SCHEMA_SNAPSHOTS_COLLECTION in PRODUCT_COLLECTIONS


# ---------------------------------------------------------------------------
# SchemaSnapshot model
# ---------------------------------------------------------------------------


class TestSchemaSnapshotModel:
    def test_round_trip(self):
        snapshot = create_schema_snapshot(
            workspace_id="ws-1",
            cache_key="abc123",
            database="hr_demo",
            graph_name="acme_kg",
            schema_kind="lpg",
            shape_fingerprint="S1",
            full_fingerprint="F1",
            conceptual_schema={"entities": [{"name": "Person"}]},
            physical_mapping={"entities": {"Person": {"style": "LABEL"}}},
            analyzer_metadata={"source": "analyzer_llm"},
        )
        d = snapshot.to_dict()
        assert d["_key"] == snapshot.schema_snapshot_id
        assert d["cache_key"] == "abc123"
        round_tripped = SchemaSnapshot.from_dict(d)
        assert round_tripped == snapshot

    def test_create_helper_generates_unique_id(self):
        a = create_schema_snapshot(
            workspace_id="ws-1",
            cache_key="k",
            database="d",
            graph_name="__db__",
            schema_kind="pg",
            shape_fingerprint="S",
            full_fingerprint="F",
        )
        b = create_schema_snapshot(
            workspace_id="ws-1",
            cache_key="k",
            database="d",
            graph_name="__db__",
            schema_kind="pg",
            shape_fingerprint="S",
            full_fingerprint="F",
        )
        assert a.schema_snapshot_id != b.schema_snapshot_id
        assert a.schema_snapshot_id.startswith("schema-snapshot-")


# ---------------------------------------------------------------------------
# GraphProfile additive fields
# ---------------------------------------------------------------------------


class TestGraphProfileV6Fields:
    def test_v06_fields_round_trip(self):
        profile = create_graph_profile(
            workspace_id="ws-1",
            connection_profile_id="cp-1",
            graph_name="acme_kg",
            schema_kind="lpg",
            graph_purpose="knowledge_graph",
            schema_snapshot_id="schema-snapshot-xyz",
            conceptual_schema={"entities": [{"name": "Person"}]},
            physical_mapping={"entities": {"Person": {"style": "LABEL"}}},
            analyzer_metadata={"source": "analyzer_baseline", "confidence": 0.9},
        )
        d = profile.to_dict()
        assert d["schema_kind"] == "lpg"
        assert d["graph_purpose"] == "knowledge_graph"
        assert d["schema_snapshot_id"] == "schema-snapshot-xyz"
        assert "conceptual_schema" in d
        assert "physical_mapping" in d
        assert "analyzer_metadata" in d
        round_tripped = GraphProfile.from_dict(d)
        assert round_tripped.schema_kind == "lpg"
        assert round_tripped.graph_purpose == "knowledge_graph"
        assert round_tripped.conceptual_schema == {"entities": [{"name": "Person"}]}

    def test_v05_documents_round_trip_unchanged(self):
        """Documents written by v0.5 (no v0.6 fields) deserialize cleanly."""
        v05_doc = {
            "_key": "graph-profile-old",
            "graph_profile_id": "graph-profile-old",
            "workspace_id": "ws-1",
            "connection_profile_id": "cp-1",
            "graph_name": "social",
            "version": 1,
            "status": "draft",
            "schema_hash": None,
            "vertex_collections": ["users"],
            "edge_collections": ["follows"],
            "edge_definitions": [],
            "collection_roles": {},
            "counts": {},
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "created_by": None,
            "metadata": {},
        }
        profile = GraphProfile.from_dict(v05_doc)
        assert profile.schema_kind is None
        assert profile.graph_purpose is None
        assert profile.conceptual_schema is None
        # And re-serializing must NOT introduce the new fields with None
        # values — they're omitted entirely so v0.5 documents stay tidy.
        re_serialized = profile.to_dict()
        assert "schema_kind" not in re_serialized
        assert "conceptual_schema" not in re_serialized
        assert "analyzer_metadata" not in re_serialized


# ---------------------------------------------------------------------------
# WorkspaceSchemaCache adapter
# ---------------------------------------------------------------------------


class TestWorkspaceSchemaCache:
    def test_protocol_compliance(self):
        """The adapter must satisfy the SchemaCache duck-type."""
        cache = WorkspaceSchemaCache(_FakeRepository(), "ws-1")  # type: ignore[arg-type]
        assert callable(cache.get)
        assert callable(cache.set)
        assert callable(cache.invalidate)
        assert cache.workspace_id == "ws-1"

    def test_get_returns_none_on_miss(self):
        cache = WorkspaceSchemaCache(_FakeRepository(), "ws-1")  # type: ignore[arg-type]
        assert cache.get(cache_key(database="x", graph_name="y")) is None

    def test_set_then_get_roundtrips_bundle(self):
        repo = _FakeRepository()
        cache = WorkspaceSchemaCache(repo, "ws-1")  # type: ignore[arg-type]
        bundle = _bundle()
        key = cache_key(database=bundle.database, graph_name=bundle.graph_name)

        cache.set(key, bundle)
        out = cache.get(key)
        assert out is not None
        assert out.schema_kind == "lpg"
        assert out.shape_fingerprint == bundle.shape_fingerprint
        assert out.full_fingerprint == bundle.full_fingerprint
        assert out.physical_mapping == bundle.physical_mapping
        assert len(repo.create_calls) == 1
        assert len(repo.update_calls) == 0

    def test_set_updates_existing_row(self):
        """A second set() for the same key must update, not duplicate."""
        repo = _FakeRepository()
        cache = WorkspaceSchemaCache(repo, "ws-1")  # type: ignore[arg-type]
        bundle = _bundle(shape="S1", full="F1")
        key = cache_key(database=bundle.database, graph_name=bundle.graph_name)
        cache.set(key, bundle)

        bundle2 = _bundle(shape="S2", full="F2", schema_kind="hybrid")
        cache.set(key, bundle2)

        assert len(repo.create_calls) == 1
        assert len(repo.update_calls) == 1
        out = cache.get(key)
        assert out is not None
        assert out.shape_fingerprint == "S2"
        assert out.schema_kind == "hybrid"

    def test_invalidate_drops_row(self):
        repo = _FakeRepository()
        cache = WorkspaceSchemaCache(repo, "ws-1")  # type: ignore[arg-type]
        bundle = _bundle()
        key = cache_key(database=bundle.database, graph_name=bundle.graph_name)
        cache.set(key, bundle)
        cache.invalidate(key)
        assert key in repo.delete_calls
        assert cache.get(key) is None

    def test_set_failure_is_swallowed(self):
        """A storage outage must NOT propagate — degrade to L1-only."""
        repo = _FakeRepository()

        def _boom(_snap):
            raise RuntimeError("storage down")

        repo.create_schema_snapshot = _boom  # type: ignore[assignment]

        cache = WorkspaceSchemaCache(repo, "ws-1")  # type: ignore[arg-type]
        bundle = _bundle()
        key = cache_key(database=bundle.database, graph_name=bundle.graph_name)
        cache.set(key, bundle)  # must not raise
        assert cache.get(key) is None


# ---------------------------------------------------------------------------
# Service: discover_graph_profile stamps v0.6 fields
# ---------------------------------------------------------------------------


def _make_db(
    *,
    name: str = "hr_demo",
    collections: Optional[List[Dict[str, Any]]] = None,
    samples: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> MagicMock:
    db = MagicMock()
    db.name = name
    db.collections.return_value = collections or []
    samples = samples or {}

    def _aql_execute(query: str, bind_vars: Dict[str, Any]):
        col = bind_vars.get("@col") or bind_vars.get("col")
        return iter(samples.get(col, []))

    db.aql.execute.side_effect = _aql_execute

    def _collection(name: str) -> MagicMock:
        col = MagicMock()
        col.count.return_value = len(samples.get(name, []))
        return col

    db.collection.side_effect = _collection
    return db


class _StubExtractor:
    """Returns a minimal GraphSchema so service.discover_graph_profile
    can run end-to-end without an ArangoDB."""

    def __init__(self, db: Any, **_: Any) -> None:
        self.db = db

    def extract(self):
        from graph_analytics_ai.ai.schema.models import (
            CollectionSchema,
            CollectionType,
            GraphSchema,
        )

        schema = GraphSchema(database_name="hr_demo")
        schema.vertex_collections["Entities"] = CollectionSchema(
            name="Entities", type=CollectionType.VERTEX, document_count=5
        )
        edges = CollectionSchema(
            name="Relationships", type=CollectionType.EDGE, document_count=3
        )
        edges.from_collections = {"Entities"}
        edges.to_collections = {"Entities"}
        schema.edge_collections["Relationships"] = edges
        return schema


class _StubSecretResolver:
    def resolve(self, ref: str) -> str:
        return "password"


class _StubServiceRepository:
    """Minimal ProductRepository surface that ProductService uses inside
    discover_graph_profile + get_graph_profile_schema_change."""

    def __init__(self) -> None:
        self._fake = _FakeRepository()
        self._connection = MagicMock(
            connection_profile_id="cp-1",
            workspace_id="ws-1",
            endpoint="http://localhost:8529",
            username="root",
            database="hr_demo",
            verify_ssl=False,
            secret_refs={"password": "secret://pw"},
        )
        self.created_graph_profiles: List[GraphProfile] = []
        self._graph_profiles: Dict[str, GraphProfile] = {}

    def get_connection_profile(self, _id: str):
        return self._connection

    def create_graph_profile(self, profile: GraphProfile) -> str:
        self.created_graph_profiles.append(profile)
        self._graph_profiles[profile.graph_profile_id] = profile
        return profile.graph_profile_id

    def get_graph_profile(self, graph_profile_id: str) -> GraphProfile:
        return self._graph_profiles[graph_profile_id]

    # SchemaSnapshot CRUD — delegate to the fake.
    def create_schema_snapshot(self, snapshot: SchemaSnapshot) -> str:
        return self._fake.create_schema_snapshot(snapshot)

    def update_schema_snapshot(self, snapshot: SchemaSnapshot) -> str:
        return self._fake.update_schema_snapshot(snapshot)

    def get_schema_snapshot_by_cache_key(self, key: str) -> Optional[SchemaSnapshot]:
        return self._fake.get_schema_snapshot_by_cache_key(key)

    def delete_schema_snapshot_by_cache_key(self, key: str) -> int:
        return self._fake.delete_schema_snapshot_by_cache_key(key)


class TestDiscoverGraphProfileV6:
    def _service(self, db: MagicMock, repo: _StubServiceRepository):
        from graph_analytics_ai.product.service import ProductService

        return ProductService(
            repository=repo,  # type: ignore[arg-type]
            secret_resolver=_StubSecretResolver(),  # type: ignore[arg-type]
            db_connector=lambda **_: db,
            schema_extractor_factory=_StubExtractor,
        )

    def _lpg_db(self) -> MagicMock:
        return _make_db(
            collections=[
                {"name": "Entities", "type": "document"},
                {"name": "Relationships", "type": "edge"},
            ],
            samples={
                "Entities": [
                    {"_key": "p1", "type": "Person", "name": "Alice"},
                    {"_key": "p2", "type": "Person", "name": "Bob"},
                    {"_key": "o1", "type": "Org", "name": "ACME"},
                ],
                "Relationships": [
                    {
                        "_from": "Entities/p1",
                        "_to": "Entities/o1",
                        "type": "WORKS_FOR",
                    }
                ],
            },
        )

    def test_discover_stamps_v06_fields_for_lpg_graph(self, monkeypatch):
        repo = _StubServiceRepository()
        db = self._lpg_db()
        service = self._service(db, repo)

        # Force the heuristic strategy so the test does not depend on
        # whether arangodb-schema-analyzer is installed in the dev env.
        result = service.discover_graph_profile(
            connection_profile_id="cp-1", schema_strategy="heuristic"
        )

        assert len(repo.created_graph_profiles) == 1
        profile = repo.created_graph_profiles[0]
        assert profile.schema_kind == "lpg"
        assert profile.conceptual_schema is not None
        assert "entities" in profile.conceptual_schema
        assert profile.physical_mapping is not None
        assert "Person" in profile.physical_mapping["entities"]
        assert profile.analyzer_metadata is not None
        assert profile.analyzer_metadata["source"] == "heuristic"
        assert profile.schema_snapshot_id is not None  # back-pointer set

        # The discovery result reflects the stamped fields.
        result_dict = result.to_dict()["graph_profile"]
        assert result_dict["schema_kind"] == "lpg"
        assert result_dict["schema_snapshot_id"] == profile.schema_snapshot_id

    def test_discover_succeeds_when_acquisition_raises(self, monkeypatch):
        """A failure in acquire_schema must NOT block profile creation."""
        repo = _StubServiceRepository()
        db = self._lpg_db()
        service = self._service(db, repo)

        # Patch the acquisition entry point used inside discover.
        from graph_analytics_ai.product import service as service_mod

        def _boom(*args, **kwargs):
            raise RuntimeError("simulated analyzer failure")

        monkeypatch.setattr(service_mod, "acquire_schema", _boom)

        result = service.discover_graph_profile(connection_profile_id="cp-1")
        profile = repo.created_graph_profiles[0]
        # v0.6 fields must be absent so the profile shape matches v0.5.
        assert profile.schema_kind is None
        assert profile.conceptual_schema is None
        assert profile.schema_snapshot_id is None
        # And the result still serializes cleanly.
        assert "graph_profile" in result.to_dict()


# ---------------------------------------------------------------------------
# Service: get_graph_profile_schema_change
# ---------------------------------------------------------------------------


class TestSchemaChangeProbe:
    def _service(self, db: MagicMock, repo: _StubServiceRepository):
        from graph_analytics_ai.product.service import ProductService

        return ProductService(
            repository=repo,  # type: ignore[arg-type]
            secret_resolver=_StubSecretResolver(),  # type: ignore[arg-type]
            db_connector=lambda **_: db,
            schema_extractor_factory=_StubExtractor,
        )

    def test_no_cache_status(self):
        repo = _StubServiceRepository()
        db = _make_db(collections=[{"name": "Entities", "type": "document"}])
        service = self._service(db, repo)
        # Pre-seed a graph profile referencing the connection.
        profile = create_graph_profile(
            workspace_id="ws-1",
            connection_profile_id="cp-1",
            graph_name="__db__",
        )
        repo.create_graph_profile(profile)

        view = service.get_graph_profile_schema_change(
            graph_profile_id=profile.graph_profile_id
        )
        assert isinstance(view, SchemaChangeView)
        assert view.status == "no_cache"
        assert view.needs_full_rebuild is True
        assert view.cached_shape_fingerprint is None

    def test_returns_unchanged_when_cache_matches(self):
        repo = _StubServiceRepository()
        db = _make_db(
            collections=[{"name": "Entities", "type": "document"}],
            samples={"Entities": [{"_key": "p1", "type": "Person"}]},
        )
        service = self._service(db, repo)

        profile = create_graph_profile(
            workspace_id="ws-1",
            connection_profile_id="cp-1",
            graph_name="acme_kg",
        )
        repo.create_graph_profile(profile)

        # Run discover first so the L2 cache is populated.
        service.discover_graph_profile(
            connection_profile_id="cp-1", schema_strategy="heuristic"
        )
        # Use the freshly-created profile from discover (which has the
        # right graph_name to align with the cache key).
        latest = repo.created_graph_profiles[-1]

        view = service.get_graph_profile_schema_change(
            graph_profile_id=latest.graph_profile_id
        )
        assert view.status == "unchanged"
        assert view.needs_full_rebuild is False
        assert view.cached_shape_fingerprint is not None
        assert view.cached_full_fingerprint is not None


# ---------------------------------------------------------------------------
# API endpoint registration
# ---------------------------------------------------------------------------


class TestSchemaChangeEndpoint:
    def test_endpoint_registered(self):
        endpoint = next(
            (
                e
                for e in PRODUCT_API_ENDPOINTS
                if e.path == "/api/graph-profiles/{graph_profile_id}/schema-change"
            ),
            None,
        )
        assert endpoint is not None
        assert isinstance(endpoint, ProductAPIEndpoint)
        assert endpoint.method == "GET"
        assert endpoint.service_method == "get_graph_profile_schema_change"
        assert "graph-profiles" in endpoint.tags

    def test_dispatcher_routes_to_service_method(self):
        """The framework-neutral dispatcher must hand off to the right
        service method with the path param coerced into a kwarg.
        """

        class _Service:
            def get_graph_profile_schema_change(self, graph_profile_id: str):
                return SchemaChangeView(
                    graph_profile_id=graph_profile_id,
                    status="no_cache",
                    current_shape_fingerprint="S",
                    current_full_fingerprint="F",
                    cached_shape_fingerprint=None,
                    cached_full_fingerprint=None,
                    needs_full_rebuild=True,
                )

        dispatcher = ProductAPIDispatcher(_Service())
        result = dispatcher.dispatch(
            method="GET",
            path="/api/graph-profiles/{graph_profile_id}/schema-change",
            path_params={"graph_profile_id": "graph-profile-1"},
        )
        assert result["graph_profile_id"] == "graph-profile-1"
        assert result["status"] == "no_cache"
        assert result["needs_full_rebuild"] is True


# ---------------------------------------------------------------------------
# Phase 6b — PATCH endpoints + graph_purpose stamping
# ---------------------------------------------------------------------------


class TestGraphPurposeStamping:
    """discover_graph_profile classifies + stamps graph_purpose (FR-61..FR-63)."""

    def _service(self, db: MagicMock, repo: _StubServiceRepository):
        from graph_analytics_ai.product.service import ProductService

        return ProductService(
            repository=repo,  # type: ignore[arg-type]
            secret_resolver=_StubSecretResolver(),  # type: ignore[arg-type]
            db_connector=lambda **_: db,
            schema_extractor_factory=_StubExtractor,
        )

    def test_lpg_graphrag_kg_stamped_as_knowledge_graph(self):
        """An LPG with Entities + Relationships collections classifies
        as knowledge_graph, with the result mirrored in
        analyzer_metadata.graph_purpose_classification.
        """
        repo = _StubServiceRepository()
        db = _make_db(
            collections=[
                {"name": "Entities", "type": "document"},
                {"name": "Relationships", "type": "edge"},
            ],
            samples={
                "Entities": [
                    {"_key": "p1", "type": "Person", "name": "A"},
                    {"_key": "p2", "type": "Person", "name": "B"},
                    {"_key": "o1", "type": "Org", "name": "C"},
                ],
                "Relationships": [
                    {"_from": "Entities/p1", "_to": "Entities/o1", "type": "WORKS_FOR"},
                ],
            },
        )
        service = self._service(db, repo)
        service.discover_graph_profile(
            connection_profile_id="cp-1", schema_strategy="heuristic"
        )

        assert len(repo.created_graph_profiles) == 1
        profile = repo.created_graph_profiles[0]
        assert profile.graph_purpose == "knowledge_graph"
        meta = profile.analyzer_metadata or {}
        assert "graph_purpose_classification" in meta
        classification = meta["graph_purpose_classification"]
        assert classification["purpose"] == "knowledge_graph"
        assert classification["confidence"] > 0.5
        assert classification["reasons"]


class TestPatchConceptualSchemaEndpoint:
    def _service(self, repo: _StubServiceRepository):
        from graph_analytics_ai.product.service import ProductService

        return ProductService(
            repository=repo,  # type: ignore[arg-type]
            secret_resolver=_StubSecretResolver(),  # type: ignore[arg-type]
        )

    def test_endpoint_registered(self):
        endpoint = next(
            (
                e
                for e in PRODUCT_API_ENDPOINTS
                if e.path == "/api/graph-profiles/{graph_profile_id}/conceptual-schema"
            ),
            None,
        )
        assert endpoint is not None
        assert endpoint.method == "PATCH"
        assert endpoint.service_method == "update_graph_profile_conceptual_schema"

    def test_patch_replaces_conceptual_schema(self):
        repo = _StubServiceRepository()
        # Pre-seed a graph profile and pre-stub the audit-event sink.
        repo.create_audit_event = MagicMock(return_value="audit-1")  # type: ignore[attr-defined]
        repo.update_graph_profile = MagicMock()  # type: ignore[attr-defined]

        profile = create_graph_profile(
            workspace_id="ws-1",
            connection_profile_id="cp-1",
            graph_name="acme_kg",
            conceptual_schema={"entities": [], "relationships": [], "properties": []},
        )
        repo.create_graph_profile(profile)

        new_schema = {
            "entities": [{"name": "Person", "labels": ["Person"]}],
            "relationships": [{"type": "WORKS_FOR"}],
            "properties": [],
        }
        service = self._service(repo)
        result = service.update_graph_profile_conceptual_schema(
            graph_profile_id=profile.graph_profile_id,
            conceptual_schema=new_schema,
            actor="alice",
        )
        assert result.conceptual_schema == new_schema
        # Manual-override marker was stamped onto analyzer_metadata.
        assert result.analyzer_metadata is not None
        override = result.analyzer_metadata["manual_override"]
        assert override["edited_by"] == "alice"
        assert override["field"] == "conceptual_schema"
        # Repository update + audit event were both invoked.
        repo.update_graph_profile.assert_called_once()
        repo.create_audit_event.assert_called_once()

    def test_patch_rejects_non_dict_payload(self):
        from graph_analytics_ai.product.exceptions import ValidationError

        repo = _StubServiceRepository()
        repo.create_audit_event = MagicMock()  # type: ignore[attr-defined]
        profile = create_graph_profile(
            workspace_id="ws-1", connection_profile_id="cp-1", graph_name="g"
        )
        repo.create_graph_profile(profile)

        service = self._service(repo)
        with pytest.raises(ValidationError):
            service.update_graph_profile_conceptual_schema(
                graph_profile_id=profile.graph_profile_id,
                conceptual_schema=["not", "a", "dict"],  # type: ignore[arg-type]
            )

    def test_patch_rejects_payload_missing_required_keys(self):
        from graph_analytics_ai.product.exceptions import ValidationError

        repo = _StubServiceRepository()
        repo.create_audit_event = MagicMock()  # type: ignore[attr-defined]
        profile = create_graph_profile(
            workspace_id="ws-1", connection_profile_id="cp-1", graph_name="g"
        )
        repo.create_graph_profile(profile)

        service = self._service(repo)
        # Missing "relationships".
        with pytest.raises(ValidationError):
            service.update_graph_profile_conceptual_schema(
                graph_profile_id=profile.graph_profile_id,
                conceptual_schema={"entities": []},
            )


class TestPatchGraphPurposeEndpoint:
    def _service(self, repo: _StubServiceRepository):
        from graph_analytics_ai.product.service import ProductService

        return ProductService(
            repository=repo,  # type: ignore[arg-type]
            secret_resolver=_StubSecretResolver(),  # type: ignore[arg-type]
        )

    def test_endpoint_registered(self):
        endpoint = next(
            (
                e
                for e in PRODUCT_API_ENDPOINTS
                if e.path == "/api/graph-profiles/{graph_profile_id}/graph-purpose"
            ),
            None,
        )
        assert endpoint is not None
        assert endpoint.method == "PATCH"
        assert endpoint.service_method == "update_graph_profile_purpose"

    def test_patch_overrides_classifier_verdict(self):
        repo = _StubServiceRepository()
        repo.create_audit_event = MagicMock()  # type: ignore[attr-defined]
        repo.update_graph_profile = MagicMock()  # type: ignore[attr-defined]

        profile = create_graph_profile(
            workspace_id="ws-1",
            connection_profile_id="cp-1",
            graph_name="g",
            graph_purpose="hybrid",
        )
        repo.create_graph_profile(profile)

        service = self._service(repo)
        result = service.update_graph_profile_purpose(
            graph_profile_id=profile.graph_profile_id,
            graph_purpose="knowledge_graph",
            actor="bob",
        )
        assert result.graph_purpose == "knowledge_graph"
        assert result.analyzer_metadata is not None
        override = result.analyzer_metadata["manual_override"]
        assert override["field"] == "graph_purpose"
        assert override["previous_value"] == "hybrid"
        assert override["edited_by"] == "bob"
        repo.update_graph_profile.assert_called_once()
        repo.create_audit_event.assert_called_once()

    def test_patch_rejects_unknown_purpose_value(self):
        from graph_analytics_ai.product.exceptions import ValidationError

        repo = _StubServiceRepository()
        repo.create_audit_event = MagicMock()  # type: ignore[attr-defined]
        profile = create_graph_profile(
            workspace_id="ws-1", connection_profile_id="cp-1", graph_name="g"
        )
        repo.create_graph_profile(profile)

        service = self._service(repo)
        with pytest.raises(ValidationError):
            service.update_graph_profile_purpose(
                graph_profile_id=profile.graph_profile_id,
                graph_purpose="bogus",
            )


# ---------------------------------------------------------------------------
# Phase 6b — bulk inventory endpoint (FR-67)
# ---------------------------------------------------------------------------


class TestDiscoverGraphProfilesBulk:
    """``discover_graph_profiles`` (plural) bulk-discovery endpoint."""

    def _service(
        self,
        db: MagicMock,
        repo: _StubServiceRepository,
        named_graphs: List[Dict[str, Any]],
    ):
        from graph_analytics_ai.product.service import ProductService

        service = ProductService(
            repository=repo,  # type: ignore[arg-type]
            secret_resolver=_StubSecretResolver(),  # type: ignore[arg-type]
            db_connector=lambda **_: db,
            schema_extractor_factory=_StubExtractor,
        )
        # Patch list_connection_profile_graphs at the service-method
        # level so we don't need to mock db.graphs() / driver internals.
        from graph_analytics_ai.product.service import (
            ConnectionGraphsResult,
            ConnectionGraphSummary,
        )

        summaries = [
            ConnectionGraphSummary(
                name=g["name"],
                is_system=g.get("is_system", False),
                vertex_collections=g.get("vertex_collections", []),
                edge_collections=g.get("edge_collections", []),
                orphan_collections=[],
                edge_definitions=[],
            )
            for g in named_graphs
        ]
        service.list_connection_profile_graphs = MagicMock(  # type: ignore[assignment]
            return_value=ConnectionGraphsResult(
                connection_profile_id="cp-1",
                workspace_id="ws-1",
                database="hr_demo",
                graphs=summaries,
            )
        )
        return service

    def _kg_db(self) -> MagicMock:
        return _make_db(
            collections=[
                {"name": "Entities", "type": "document"},
                {"name": "Relationships", "type": "edge"},
            ],
            samples={
                "Entities": [
                    {"_key": "p1", "type": "Person"},
                    {"_key": "p2", "type": "Person"},
                    {"_key": "o1", "type": "Org"},
                ],
                "Relationships": [
                    {"_from": "Entities/p1", "_to": "Entities/o1", "type": "WORKS_FOR"},
                ],
            },
        )

    def test_endpoint_registered(self):
        endpoint = next(
            (
                e
                for e in PRODUCT_API_ENDPOINTS
                if e.path
                == "/api/connection-profiles/{connection_profile_id}/discover-graph-profiles"
            ),
            None,
        )
        assert endpoint is not None
        assert endpoint.method == "POST"
        assert endpoint.service_method == "discover_graph_profiles"

    def test_discover_iterates_every_named_graph(self):
        repo = _StubServiceRepository()
        db = self._kg_db()
        named_graphs = [
            {"name": "corpus_g"},
            {"name": "knowledge_g"},
            {"name": "structured_g"},
        ]
        service = self._service(db, repo, named_graphs)

        result = service.discover_graph_profiles(
            connection_profile_id="cp-1", schema_strategy="heuristic"
        )

        # FR-67b: the bulk discover now produces N+1 profiles (one per
        # named graph + the "default" all-collections profile). The
        # ``database_only`` slot remains None because there *are* named
        # graphs; the default profile lives alongside them.
        assert result.discovered_graph_count == 4
        assert len(result.graph_profiles) == 4
        names = {p["graph_name"] for p in result.graph_profiles}
        assert names == {"default", "corpus_g", "knowledge_g", "structured_g"}
        assert result.failures == []
        assert result.database_only is None
        # Each profile got the v0.6 enrichment.
        for prof in result.graph_profiles:
            assert prof["schema_kind"] in {"pg", "lpg", "hybrid", "rpt", "unknown"}

    def test_failure_in_one_graph_does_not_abort_sweep(self, monkeypatch):
        """A single per-graph failure must collect into ``failures``,
        not raise."""
        repo = _StubServiceRepository()
        db = self._kg_db()
        service = self._service(
            db,
            repo,
            named_graphs=[{"name": "good_g"}, {"name": "broken_g"}],
        )

        # Make discover_graph_profile raise for one specific graph.
        original = service.discover_graph_profile

        def _selective(connection_profile_id, **kwargs):
            if kwargs.get("graph_name") == "broken_g":
                raise RuntimeError("simulated per-graph failure")
            return original(connection_profile_id, **kwargs)

        service.discover_graph_profile = _selective  # type: ignore[assignment]

        result = service.discover_graph_profiles(
            connection_profile_id="cp-1", schema_strategy="heuristic"
        )

        # FR-67b: discovered_graph_count is "good_g" (1) + the always-
        # present "default" profile (1) = 2.
        assert result.discovered_graph_count == 2
        assert {p["graph_name"] for p in result.graph_profiles} == {
            "default",
            "good_g",
        }
        assert len(result.failures) == 1
        failure = result.failures[0]
        assert failure["graph_name"] == "broken_g"
        assert failure["error_type"] == "RuntimeError"
        assert "simulated" in failure["message"]

    def test_database_only_fallback_when_no_named_graphs(self):
        """When no named graphs exist, the single ``default`` profile
        is BOTH the only entry in ``graph_profiles`` AND mirrored into
        the legacy ``database_only`` slot for backwards compatibility
        with older frontends (FR-67b).
        """
        repo = _StubServiceRepository()
        db = self._kg_db()
        service = self._service(db, repo, named_graphs=[])

        result = service.discover_graph_profiles(
            connection_profile_id="cp-1", schema_strategy="heuristic"
        )
        assert result.discovered_graph_count == 1
        assert len(result.graph_profiles) == 1
        assert result.graph_profiles[0]["graph_name"] == "default"
        # Legacy slot still populated for old frontends.
        assert result.database_only is not None
        assert "graph_profile" in result.database_only
        assert "schema_summary" in result.database_only
        assert result.database_only["graph_profile"]["graph_name"] == "default"

    def test_system_graphs_filtered(self):
        repo = _StubServiceRepository()
        db = self._kg_db()
        service = self._service(
            db,
            repo,
            named_graphs=[
                {"name": "_system_graph", "is_system": True},
                {"name": "real_graph"},
            ],
        )
        result = service.discover_graph_profiles(
            connection_profile_id="cp-1", schema_strategy="heuristic"
        )
        # FR-67b: system graph is filtered + "default" is always created,
        # so we end up with {default, real_graph}.
        assert result.discovered_graph_count == 2
        assert {p["graph_name"] for p in result.graph_profiles} == {
            "default",
            "real_graph",
        }


# ---------------------------------------------------------------------------
# v0.6.1 — Autograph auto-pairing in discover_graph_profiles
# ---------------------------------------------------------------------------


class _AutographStubRepo(_StubServiceRepository):
    """Extends the basic stub with GraphSet + audit-event surface so the
    auto-pair code path exercises end-to-end (not just degrades silently)."""

    def __init__(self) -> None:
        super().__init__()
        self._graph_sets: Dict[str, Any] = {}
        self.audit_events: List[Any] = []

    def create_audit_event(self, event: Any) -> str:
        self.audit_events.append(event)
        return getattr(event, "audit_event_id", "ae-1")

    def list_graph_sets(self, workspace_id: str) -> List[Any]:
        return [
            gs for gs in self._graph_sets.values() if gs.workspace_id == workspace_id
        ]

    def create_graph_set(self, graph_set: Any) -> str:
        self._graph_sets[graph_set.graph_set_id] = graph_set
        return graph_set.graph_set_id


class TestAutographAutoPair:
    """When discover_graph_profiles encounters Autograph-shaped names,
    it MUST detect the projects and auto-create one GraphSet per
    complete project (PRD v0.6.1 / Phase 6e)."""

    def _service_with_autograph(
        self, named_graphs: List[Dict[str, Any]]
    ) -> tuple[Any, _AutographStubRepo]:
        from graph_analytics_ai.product.service import (
            ConnectionGraphsResult,
            ConnectionGraphSummary,
            ProductService,
        )

        repo = _AutographStubRepo()
        db = _make_db(
            collections=[
                {"name": "P_Entities", "type": "document"},
                {"name": "P_Documents", "type": "document"},
                {"name": "P_Chunks", "type": "document"},
                {"name": "P_Communities", "type": "document"},
                {"name": "P_domains", "type": "document"},
                {"name": "P_modules", "type": "document"},
                {"name": "P_sources", "type": "document"},
                {"name": "P_rags", "type": "document"},
                {"name": "P_corpus_relations", "type": "edge"},
                {"name": "P_Relations", "type": "edge"},
                {"name": "P_similarities", "type": "edge"},
            ],
            samples={},
        )
        service = ProductService(
            repository=repo,  # type: ignore[arg-type]
            secret_resolver=_StubSecretResolver(),  # type: ignore[arg-type]
            db_connector=lambda **_: db,
            schema_extractor_factory=_StubExtractor,
        )
        summaries = [
            ConnectionGraphSummary(
                name=g["name"],
                is_system=g.get("is_system", False),
                vertex_collections=g.get("vertex_collections", []),
                edge_collections=g.get("edge_collections", []),
                orphan_collections=[],
                edge_definitions=[],
            )
            for g in named_graphs
        ]
        service.list_connection_profile_graphs = MagicMock(  # type: ignore[assignment]
            return_value=ConnectionGraphsResult(
                connection_profile_id="cp-1",
                workspace_id="ws-1",
                database="hr_demo",
                graphs=summaries,
            )
        )
        return service, repo

    def test_complete_project_auto_creates_one_graph_set(self):
        service, repo = self._service_with_autograph(
            named_graphs=[
                {
                    "name": "P_CorpusGraph",
                    "vertex_collections": [
                        "P_domains",
                        "P_modules",
                        "P_sources",
                        "P_rags",
                    ],
                    "edge_collections": ["P_corpus_relations", "P_similarities"],
                },
                {
                    "name": "P_kg",
                    "vertex_collections": [
                        "P_Chunks",
                        "P_Communities",
                        "P_Documents",
                        "P_Entities",
                    ],
                    "edge_collections": ["P_Relations"],
                },
            ],
        )
        result = service.discover_graph_profiles(
            connection_profile_id="cp-1", schema_strategy="heuristic"
        )
        # FR-67b: 2 named-graph profiles + 1 "default" profile = 3.
        # The Autograph detector still only pairs the named-graph
        # corpus + kg into one GraphSet (the default profile is not
        # an Autograph artefact and is correctly ignored by the
        # detector).
        assert result.discovered_graph_count == 3
        assert "default" in {p["graph_name"] for p in result.graph_profiles}

        # Detector ran and surfaced the project.
        assert result.arango_product is not None
        assert result.arango_product["kind"] == "autograph"
        assert len(result.arango_product["projects"]) == 1
        assert result.arango_product["projects"][0]["project_name"] == "P"
        assert result.arango_product["projects"][0]["completeness"] == "complete"

        # GraphSet auto-created.
        assert len(result.auto_created_graph_sets) == 1
        gs = result.auto_created_graph_sets[0]
        assert gs["name"] == "autograph:P"
        assert len(gs["graph_profile_ids"]) == 2
        # Cross-graph link populated from the implicit GraphRAG seed link.
        assert len(gs["cross_graph_links"]) == 1
        link = gs["cross_graph_links"][0]
        assert link["metadata"]["kind"] == "graphrag_entity_type_seed"
        assert link["metadata"]["discovered_by"] == "autograph_detector"
        # Persisted in the stub repo.
        assert len(repo._graph_sets) == 1

    def test_corpus_only_project_auto_creates_single_member_graph_set(self):
        service, repo = self._service_with_autograph(
            named_graphs=[
                {
                    "name": "P_CorpusGraph",
                    "vertex_collections": [
                        "P_domains",
                        "P_modules",
                        "P_sources",
                        "P_rags",
                    ],
                    "edge_collections": ["P_corpus_relations", "P_similarities"],
                },
            ],
        )
        result = service.discover_graph_profiles(
            connection_profile_id="cp-1", schema_strategy="heuristic"
        )
        # Detector still fires and reports corpus_only.
        assert result.arango_product is not None
        proj = result.arango_product["projects"][0]
        assert proj["completeness"] == "corpus_only"
        assert any("INCOMPLETE_AUTOGRAPH_RUN" in w for w in proj["warnings"])

        # Single-member GraphSet auto-created (no cross-graph link
        # possible without the KG side).
        assert len(result.auto_created_graph_sets) == 1
        gs = result.auto_created_graph_sets[0]
        assert len(gs["graph_profile_ids"]) == 1
        assert gs["cross_graph_links"] == []

    def test_idempotent_does_not_duplicate_graph_set_on_re_discover(self):
        service, repo = self._service_with_autograph(
            named_graphs=[
                {"name": "P_CorpusGraph"},
                {"name": "P_kg"},
            ],
        )
        # First run: creates the GraphSet.
        first = service.discover_graph_profiles(
            connection_profile_id="cp-1", schema_strategy="heuristic"
        )
        assert len(first.auto_created_graph_sets) == 1
        assert len(repo._graph_sets) == 1

        # Second run: must reuse, not duplicate.
        second = service.discover_graph_profiles(
            connection_profile_id="cp-1", schema_strategy="heuristic"
        )
        assert len(second.auto_created_graph_sets) == 1
        assert (
            len(repo._graph_sets) == 1
        ), "Re-running discover must not create a duplicate GraphSet"

    def test_no_autograph_names_means_no_detector_or_graph_set(self):
        from graph_analytics_ai.product.service import (
            ConnectionGraphsResult,
            ConnectionGraphSummary,
            ProductService,
        )

        repo = _AutographStubRepo()
        # Plain hand-built schema (no Autograph names anywhere).
        db = _make_db(
            collections=[
                {"name": "Users", "type": "document"},
                {"name": "Follows", "type": "edge"},
            ],
            samples={},
        )
        service = ProductService(
            repository=repo,  # type: ignore[arg-type]
            secret_resolver=_StubSecretResolver(),  # type: ignore[arg-type]
            db_connector=lambda **_: db,
            schema_extractor_factory=_StubExtractor,
        )
        service.list_connection_profile_graphs = MagicMock(  # type: ignore[assignment]
            return_value=ConnectionGraphsResult(
                connection_profile_id="cp-1",
                workspace_id="ws-1",
                database="hr_demo",
                graphs=[
                    ConnectionGraphSummary(
                        name="UserGraph",
                        is_system=False,
                        vertex_collections=["Users"],
                        edge_collections=["Follows"],
                        orphan_collections=[],
                        edge_definitions=[],
                    )
                ],
            )
        )
        result = service.discover_graph_profiles(
            connection_profile_id="cp-1", schema_strategy="heuristic"
        )
        assert result.arango_product is None
        assert result.auto_created_graph_sets == []
        assert len(repo._graph_sets) == 0
