"""Unit tests for graph_analytics_ai.ai.schema.acquire (Phase 6a).

Covers:

- Heuristic-only PG/LPG/hybrid classification (no schema_analyzer required).
- Analyzer-installed path produces a bundle with source == analyzer_*.
- Analyzer-missing fallback attaches the ANALYZER_NOT_INSTALLED warning.
- Two-tier cache: in-memory L1 + injected persistent L2.
- ``shape`` fingerprint stable across stats-only changes; ``full`` differs.
- ``acquire_schema`` reuses cached mapping on full-fingerprint match,
  refreshes statistics on shape-stable + counts-changed, full re-introspects
  on shape change.
- ``describe_schema_change`` returns the right ChangeStatus in each case
  without mutating the cache.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from graph_analytics_ai.ai.schema import acquire as acquire_mod
from graph_analytics_ai.ai.schema.acquire import (
    DETECTED_PATTERN_TAGS,
    InMemorySchemaCache,
    SchemaAcquisitionBundle,
    SchemaCache,
    SchemaChangeReport,
    acquire_schema,
    build_heuristic_bundle,
    cache_key,
    describe_schema_change,
    invalidate_schema_cache,
    reset_default_cache,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_default_cache():
    """Every test starts with a clean L1 cache."""
    reset_default_cache()
    yield
    reset_default_cache()


def _make_db(
    *,
    name: str = "hr_demo",
    collections: Optional[List[Dict[str, Any]]] = None,
    samples: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    counts: Optional[Dict[str, int]] = None,
) -> MagicMock:
    """Build a minimal duck-typed StandardDatabase mock.

    ``collections`` is the list returned by ``db.collections()`` (each
    entry ``{"name": str, "type": "document"|"edge"}``). ``samples``
    maps collection names to the list of docs the AQL ``LIMIT`` query
    will return. ``counts`` maps collection names to ``count()``.
    """
    db = MagicMock()
    db.name = name
    db.collections.return_value = collections or []

    # ``db.aql.execute`` returns the sample list for the requested
    # collection (we only use one query shape).
    samples = samples or {}

    def _aql_execute(query: str, bind_vars: Dict[str, Any]):
        col = bind_vars.get("@col") or bind_vars.get("col")
        return iter(samples.get(col, []))

    db.aql.execute.side_effect = _aql_execute

    counts = counts or {}

    def _collection(name: str) -> MagicMock:
        col = MagicMock()
        col.count.return_value = counts.get(name, len(samples.get(name, [])))
        return col

    db.collection.side_effect = _collection
    return db


# ---------------------------------------------------------------------------
# Heuristic tier — schema kind classification
# ---------------------------------------------------------------------------


class TestHeuristicSchemaKind:
    """``build_heuristic_bundle`` classifies PG / LPG / hybrid correctly."""

    def test_pure_pg_database(self):
        db = _make_db(
            collections=[
                {"name": "Employee", "type": "document"},
                {"name": "Department", "type": "document"},
                {"name": "reports_to", "type": "edge"},
            ],
            samples={
                "Employee": [
                    {"_key": "e1", "name": "Alice"},
                    {"_key": "e2", "name": "Bob"},
                ],
                "Department": [{"_key": "d1", "name": "Eng"}],
                "reports_to": [
                    {"_from": "Employee/e1", "_to": "Employee/e2"},
                    {"_from": "Employee/e2", "_to": "Employee/e1"},
                ],
            },
        )
        bundle = build_heuristic_bundle(db, graph_name="hris")
        assert bundle.schema_kind == "pg"
        assert set(bundle.physical_mapping["entities"]) == {"Employee", "Department"}
        assert set(bundle.physical_mapping["relationships"]) == {"reports_to"}
        styles = {e["style"] for e in bundle.physical_mapping["entities"].values()}
        assert styles == {"COLLECTION"}
        assert bundle.analyzer_metadata["source"] == "heuristic"
        assert bundle.analyzer_metadata["review_required"] is True
        assert "PG_ENTITY_COLLECTION" in bundle.analyzer_metadata["detected_patterns"]
        assert "PG_DEDICATED_EDGE" in bundle.analyzer_metadata["detected_patterns"]

    def test_lpg_graphrag_knowledge_graph(self):
        """A GraphRAG-style KG: one Entities collection + one Relationships
        collection, both discriminated by ``type``. Should classify as LPG
        and emit one entity per type value, one relationship per type value.
        """
        entities_sample = [
            {"_key": "p1", "type": "Person", "name": "Alice"},
            {"_key": "p2", "type": "Person", "name": "Bob"},
            {"_key": "o1", "type": "Org", "name": "ACME"},
            {"_key": "s1", "type": "Skill", "name": "Python"},
            {"_key": "s2", "type": "Skill", "name": "Rust"},
        ]
        rels_sample = [
            {"_from": "Entities/p1", "_to": "Entities/o1", "type": "WORKS_FOR"},
            {"_from": "Entities/p1", "_to": "Entities/s1", "type": "HAS_SKILL"},
            {"_from": "Entities/p2", "_to": "Entities/s2", "type": "HAS_SKILL"},
        ]
        db = _make_db(
            collections=[
                {"name": "Entities", "type": "document"},
                {"name": "Relationships", "type": "edge"},
            ],
            samples={"Entities": entities_sample, "Relationships": rels_sample},
        )
        bundle = build_heuristic_bundle(db, graph_name="acme_kg")
        assert bundle.schema_kind == "lpg"
        # One entity per discriminator value.
        assert set(bundle.physical_mapping["entities"]) == {"Person", "Org", "Skill"}
        for spec in bundle.physical_mapping["entities"].values():
            assert spec["style"] == "LABEL"
            assert spec["collectionName"] == "Entities"
            assert spec["typeField"] == "type"
        # One relationship per discriminator value.
        assert set(bundle.physical_mapping["relationships"]) == {
            "WORKS_FOR",
            "HAS_SKILL",
        }
        for spec in bundle.physical_mapping["relationships"].values():
            assert spec["style"] == "GENERIC_WITH_TYPE"
            assert spec["edgeCollectionName"] == "Relationships"
            assert spec["typeField"] == "type"
        assert "LPG_LABEL" in bundle.analyzer_metadata["detected_patterns"]
        assert "LPG_GENERIC_EDGE" in bundle.analyzer_metadata["detected_patterns"]

    def test_hybrid_database(self):
        """One LPG collection + one PG collection + one dedicated edge."""
        db = _make_db(
            collections=[
                {"name": "Entities", "type": "document"},
                {"name": "Department", "type": "document"},
                {"name": "in_department", "type": "edge"},
            ],
            samples={
                "Entities": [
                    {"_key": "p1", "type": "Person", "name": "Alice"},
                    {"_key": "p2", "type": "Person", "name": "Bob"},
                    {"_key": "o1", "type": "Org", "name": "ACME"},
                ],
                "Department": [{"_key": "d1", "name": "Eng"}],
                "in_department": [{"_from": "Entities/p1", "_to": "Department/d1"}],
            },
        )
        bundle = build_heuristic_bundle(db)
        assert bundle.schema_kind == "hybrid"
        assert "Person" in bundle.physical_mapping["entities"]
        assert "Department" in bundle.physical_mapping["entities"]
        assert bundle.physical_mapping["entities"]["Person"]["style"] == "LABEL"
        assert (
            bundle.physical_mapping["entities"]["Department"]["style"] == "COLLECTION"
        )

    def test_empty_database_classifies_unknown(self):
        db = _make_db(collections=[])
        bundle = build_heuristic_bundle(db)
        assert bundle.schema_kind == "unknown"
        assert bundle.physical_mapping["entities"] == {}
        assert bundle.physical_mapping["relationships"] == {}

    def test_tier_2_label_field_with_class_like_values(self):
        """``label`` field with low-cardinality class-like values is accepted."""
        db = _make_db(
            collections=[{"name": "Mixed", "type": "document"}],
            samples={
                "Mixed": [
                    {"_key": "m1", "label": "Alpha"},
                    {"_key": "m2", "label": "Alpha"},
                    {"_key": "m3", "label": "Beta"},
                    {"_key": "m4", "label": "Beta"},
                    {"_key": "m5", "label": "Beta"},
                ],
            },
        )
        bundle = build_heuristic_bundle(db)
        # No edges → "lpg" (entity styles all LABEL, edge styles empty).
        assert bundle.schema_kind == "lpg"
        assert set(bundle.physical_mapping["entities"]) == {"Alpha", "Beta"}

    def test_tier_2_label_field_rejected_when_high_cardinality(self):
        """``label`` with too many distinct values must NOT promote to LABEL."""
        sample = [{"_key": f"r{i}", "label": f"Unique{i}"} for i in range(20)]
        db = _make_db(
            collections=[{"name": "Things", "type": "document"}],
            samples={"Things": sample},
        )
        bundle = build_heuristic_bundle(db)
        assert "Things" in bundle.physical_mapping["entities"]
        assert bundle.physical_mapping["entities"]["Things"]["style"] == "COLLECTION"


# ---------------------------------------------------------------------------
# Fingerprints
# ---------------------------------------------------------------------------


class TestFingerprints:
    def test_shape_fingerprint_stable_across_count_changes(self, monkeypatch):
        """When schema_analyzer is missing, the fallback fingerprint:
        - ``shape`` ignores counts (just collection names),
        - ``full`` includes counts.
        """
        # Force fallback path even if analyzer is installed.
        monkeypatch.setattr(
            acquire_mod,
            "_shape_fingerprint",
            lambda db: acquire_mod._fallback_fingerprint(db, include_counts=False),
        )
        monkeypatch.setattr(
            acquire_mod,
            "_full_fingerprint",
            lambda db: acquire_mod._fallback_fingerprint(db, include_counts=True),
        )
        db1 = _make_db(
            collections=[
                {"name": "A", "type": "document"},
                {"name": "B", "type": "edge"},
            ],
            counts={"A": 10, "B": 100},
        )
        db2 = _make_db(
            collections=[
                {"name": "A", "type": "document"},
                {"name": "B", "type": "edge"},
            ],
            counts={"A": 1000, "B": 100000},  # counts changed
        )
        assert acquire_mod._shape_fingerprint(db1) == acquire_mod._shape_fingerprint(
            db2
        )
        assert acquire_mod._full_fingerprint(db1) != acquire_mod._full_fingerprint(db2)

    def test_shape_fingerprint_changes_when_collection_added(self, monkeypatch):
        monkeypatch.setattr(
            acquire_mod,
            "_shape_fingerprint",
            lambda db: acquire_mod._fallback_fingerprint(db, include_counts=False),
        )
        db1 = _make_db(collections=[{"name": "A", "type": "document"}])
        db2 = _make_db(
            collections=[
                {"name": "A", "type": "document"},
                {"name": "B", "type": "document"},
            ]
        )
        assert acquire_mod._shape_fingerprint(db1) != acquire_mod._shape_fingerprint(
            db2
        )


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


class _RecordingCache:
    """L2 cache stub that records every call. Implements SchemaCache."""

    def __init__(self) -> None:
        self._store: Dict[str, SchemaAcquisitionBundle] = {}
        self.gets: List[str] = []
        self.sets: List[str] = []
        self.invalidates: List[str] = []

    def get(self, key: str) -> Optional[SchemaAcquisitionBundle]:
        self.gets.append(key)
        return self._store.get(key)

    def set(self, key: str, bundle: SchemaAcquisitionBundle) -> None:
        self.sets.append(key)
        self._store[key] = bundle

    def invalidate(self, key: str) -> None:
        self.invalidates.append(key)
        self._store.pop(key, None)


class TestCacheLayering:
    def _bundle(
        self, *, shape: str = "S1", full: str = "F1"
    ) -> SchemaAcquisitionBundle:
        return SchemaAcquisitionBundle(
            schema_kind="pg",
            conceptual_schema={"entities": [], "relationships": [], "properties": []},
            physical_mapping={"entities": {}, "relationships": {}},
            analyzer_metadata={"source": "heuristic", "warnings": []},
            shape_fingerprint=shape,
            full_fingerprint=full,
            database="hr_demo",
            graph_name="__db__",
        )

    def test_persistent_cache_hydrates_inmemory_cache(self):
        l2 = _RecordingCache()
        key = cache_key(database="hr_demo", graph_name="__db__")
        l2.set(key, self._bundle())
        l2.sets.clear()  # only count subsequent writes

        # First lookup should hit L2 and hydrate L1.
        first = acquire_mod._lookup_layered_cache(key, l2)
        assert first is not None
        assert l2.gets == [key]

        # Second lookup should hit L1 only — no further L2 read.
        l2.gets.clear()
        second = acquire_mod._lookup_layered_cache(key, l2)
        assert second is first
        assert l2.gets == []

    def test_invalidate_drops_both_tiers(self):
        l2 = _RecordingCache()
        key = cache_key(database="hr_demo", graph_name="__db__")
        l2.set(key, self._bundle())
        # Hydrate L1.
        acquire_mod._lookup_layered_cache(key, l2)

        invalidate_schema_cache(database="hr_demo", graph_name="__db__", cache=l2)
        assert l2.invalidates == [key]
        # L1 should now miss.
        assert acquire_mod._DEFAULT_L1_CACHE.get(key) is None


# ---------------------------------------------------------------------------
# acquire_schema strategy + cache integration
# ---------------------------------------------------------------------------


class TestAcquireSchema:
    def test_heuristic_strategy_skips_analyzer(self):
        db = _make_db(
            collections=[
                {"name": "Employee", "type": "document"},
                {"name": "reports_to", "type": "edge"},
            ],
            samples={
                "Employee": [{"_key": "e1", "name": "Alice"}],
                "reports_to": [{"_from": "Employee/e1", "_to": "Employee/e1"}],
            },
        )
        bundle = acquire_schema(db, strategy="heuristic", graph_name="hris")
        assert bundle.schema_kind == "pg"
        assert bundle.analyzer_metadata["source"] == "heuristic"
        assert bundle.graph_name == "hris"
        assert bundle.database == "hr_demo"

    def test_invalid_strategy_raises(self):
        db = _make_db()
        with pytest.raises(ValueError):
            acquire_schema(db, strategy="bogus")  # type: ignore[arg-type]

    def test_auto_strategy_falls_back_to_heuristic_when_analyzer_import_fails(
        self, monkeypatch
    ):
        """When AgenticSchemaAnalyzer raises ImportError, auto must fall back
        to the heuristic and attach an ANALYZER_NOT_INSTALLED warning.
        """

        def _analyzer_raises(db, *, graph_name, force_llm, review_threshold):
            raise ImportError("analyzer not installed (simulated)")

        monkeypatch.setattr(acquire_mod, "_build_analyzer_bundle", _analyzer_raises)

        db = _make_db(
            collections=[{"name": "Employee", "type": "document"}],
            samples={"Employee": [{"_key": "e1", "name": "Alice"}]},
        )
        bundle = acquire_schema(db, strategy="auto")
        assert bundle.analyzer_metadata["source"] == "heuristic"
        codes = [w.get("code") for w in bundle.analyzer_metadata.get("warnings", [])]
        assert "ANALYZER_NOT_INSTALLED" in codes
        assert bundle.analyzer_metadata["review_required"] is True

    def test_analyzer_strategy_propagates_import_error(self, monkeypatch):
        def _analyzer_raises(db, *, graph_name, force_llm, review_threshold):
            raise ImportError("analyzer missing")

        monkeypatch.setattr(acquire_mod, "_build_analyzer_bundle", _analyzer_raises)
        db = _make_db()
        with pytest.raises(ImportError):
            acquire_schema(db, strategy="analyzer")

    def test_cache_hit_returns_cached_bundle_without_rebuild(self, monkeypatch):
        """When fingerprints match, the cached bundle is returned and no
        rebuild path runs.
        """
        db = _make_db(
            collections=[{"name": "Employee", "type": "document"}],
            samples={"Employee": [{"_key": "e1", "name": "Alice"}]},
        )

        # Stable fingerprints.
        monkeypatch.setattr(acquire_mod, "_shape_fingerprint", lambda d: "SHAPE_X")
        monkeypatch.setattr(acquire_mod, "_full_fingerprint", lambda d: "FULL_X")

        # Build once → caches the bundle.
        first = acquire_schema(db, strategy="heuristic")

        # If the rebuild path ran again, this counter would tick.
        sentinel = {"rebuilds": 0}

        def _track(db, *, strategy, graph_name, force_llm, review_threshold):
            sentinel["rebuilds"] += 1
            raise AssertionError("should not rebuild on full cache hit")

        monkeypatch.setattr(acquire_mod, "_build_fresh_bundle", _track)

        second = acquire_schema(db, strategy="heuristic")
        assert second.shape_fingerprint == first.shape_fingerprint
        assert sentinel["rebuilds"] == 0

    def test_shape_stable_full_changed_triggers_stats_only_refresh(self, monkeypatch):
        """When ``shape`` matches but ``full`` differs, the cached mapping is
        reused and only ``analyzer_metadata.statistics`` refreshes.
        """
        db = _make_db(
            collections=[{"name": "Employee", "type": "document"}],
            samples={"Employee": [{"_key": "e1", "name": "Alice"}]},
            counts={"Employee": 1},
        )
        monkeypatch.setattr(acquire_mod, "_shape_fingerprint", lambda d: "SHAPE_X")
        monkeypatch.setattr(acquire_mod, "_full_fingerprint", lambda d: "FULL_INITIAL")
        first = acquire_schema(db, strategy="heuristic")
        assert first.full_fingerprint == "FULL_INITIAL"

        # Ensure the rebuild path is NOT taken on the next call.
        def _no_rebuild(db, *, strategy, graph_name, force_llm, review_threshold):
            raise AssertionError("must not full-rebuild on shape-stable refresh")

        monkeypatch.setattr(acquire_mod, "_build_fresh_bundle", _no_rebuild)

        # Counts changed.
        monkeypatch.setattr(acquire_mod, "_full_fingerprint", lambda d: "FULL_NEW")
        second = acquire_schema(db, strategy="heuristic")
        assert second.full_fingerprint == "FULL_NEW"
        assert second.shape_fingerprint == first.shape_fingerprint
        # Mapping was reused.
        assert second.physical_mapping == first.physical_mapping
        assert second.conceptual_schema == first.conceptual_schema
        # Statistics block refreshed.
        assert "statistics" in second.analyzer_metadata
        assert "last_stats_refreshed_at" in second.analyzer_metadata

    def test_shape_changed_triggers_full_rebuild(self, monkeypatch):
        db = _make_db(
            collections=[{"name": "Employee", "type": "document"}],
            samples={"Employee": [{"_key": "e1", "name": "Alice"}]},
        )
        monkeypatch.setattr(acquire_mod, "_shape_fingerprint", lambda d: "SHAPE_OLD")
        monkeypatch.setattr(acquire_mod, "_full_fingerprint", lambda d: "FULL_OLD")
        acquire_schema(db, strategy="heuristic")

        rebuilt = {"count": 0}
        original_build_fresh = acquire_mod._build_fresh_bundle

        def _counting(db, *, strategy, graph_name, force_llm, review_threshold):
            rebuilt["count"] += 1
            return original_build_fresh(
                db,
                strategy=strategy,
                graph_name=graph_name,
                force_llm=force_llm,
                review_threshold=review_threshold,
            )

        monkeypatch.setattr(acquire_mod, "_build_fresh_bundle", _counting)
        monkeypatch.setattr(acquire_mod, "_shape_fingerprint", lambda d: "SHAPE_NEW")
        acquire_schema(db, strategy="heuristic")
        assert rebuilt["count"] == 1

    def test_force_refresh_bypasses_cache(self, monkeypatch):
        db = _make_db(
            collections=[{"name": "Employee", "type": "document"}],
            samples={"Employee": [{"_key": "e1", "name": "Alice"}]},
        )
        monkeypatch.setattr(acquire_mod, "_shape_fingerprint", lambda d: "SHAPE_X")
        monkeypatch.setattr(acquire_mod, "_full_fingerprint", lambda d: "FULL_X")
        acquire_schema(db, strategy="heuristic")

        rebuilt = {"count": 0}
        original_build_fresh = acquire_mod._build_fresh_bundle

        def _counting(db, *, strategy, graph_name, force_llm, review_threshold):
            rebuilt["count"] += 1
            return original_build_fresh(
                db,
                strategy=strategy,
                graph_name=graph_name,
                force_llm=force_llm,
                review_threshold=review_threshold,
            )

        monkeypatch.setattr(acquire_mod, "_build_fresh_bundle", _counting)
        acquire_schema(db, strategy="heuristic", force_refresh=True)
        assert rebuilt["count"] == 1


# ---------------------------------------------------------------------------
# describe_schema_change
# ---------------------------------------------------------------------------


class TestDescribeSchemaChange:
    def test_no_cache_status(self, monkeypatch):
        monkeypatch.setattr(acquire_mod, "_shape_fingerprint", lambda d: "S")
        monkeypatch.setattr(acquire_mod, "_full_fingerprint", lambda d: "F")
        report = describe_schema_change(_make_db())
        assert report.status == "no_cache"
        assert report.cached_shape_fingerprint is None
        assert report.cached_full_fingerprint is None
        assert report.needs_full_rebuild is True

    def test_unchanged_status(self, monkeypatch):
        db = _make_db(
            collections=[{"name": "Employee", "type": "document"}],
            samples={"Employee": [{"_key": "e1", "name": "Alice"}]},
        )
        monkeypatch.setattr(acquire_mod, "_shape_fingerprint", lambda d: "S")
        monkeypatch.setattr(acquire_mod, "_full_fingerprint", lambda d: "F")
        acquire_schema(db, strategy="heuristic")

        report = describe_schema_change(db)
        assert report.status == "unchanged"
        assert report.unchanged is True
        assert report.cached_shape_fingerprint == "S"
        assert report.cached_full_fingerprint == "F"

    def test_stats_changed_status(self, monkeypatch):
        db = _make_db(
            collections=[{"name": "Employee", "type": "document"}],
            samples={"Employee": [{"_key": "e1", "name": "Alice"}]},
        )
        monkeypatch.setattr(acquire_mod, "_shape_fingerprint", lambda d: "S")
        monkeypatch.setattr(acquire_mod, "_full_fingerprint", lambda d: "F1")
        acquire_schema(db, strategy="heuristic")

        monkeypatch.setattr(acquire_mod, "_full_fingerprint", lambda d: "F2")
        report = describe_schema_change(db)
        assert report.status == "stats_changed"
        assert report.needs_full_rebuild is False

    def test_shape_changed_status(self, monkeypatch):
        db = _make_db(
            collections=[{"name": "Employee", "type": "document"}],
            samples={"Employee": [{"_key": "e1", "name": "Alice"}]},
        )
        monkeypatch.setattr(acquire_mod, "_shape_fingerprint", lambda d: "S1")
        monkeypatch.setattr(acquire_mod, "_full_fingerprint", lambda d: "F1")
        acquire_schema(db, strategy="heuristic")

        monkeypatch.setattr(acquire_mod, "_shape_fingerprint", lambda d: "S2")
        report = describe_schema_change(db)
        assert report.status == "shape_changed"
        assert report.needs_full_rebuild is True

    def test_describe_does_not_mutate_cache(self, monkeypatch):
        """The probe must be read-only — even on a cache miss it must not
        write a placeholder.
        """
        monkeypatch.setattr(acquire_mod, "_shape_fingerprint", lambda d: "S")
        monkeypatch.setattr(acquire_mod, "_full_fingerprint", lambda d: "F")
        l2 = _RecordingCache()
        describe_schema_change(_make_db(), cache=l2)
        assert l2.sets == []
        assert l2.invalidates == []


# ---------------------------------------------------------------------------
# Bundle round-trip
# ---------------------------------------------------------------------------


class TestBundleRoundTrip:
    def test_to_dict_from_dict(self):
        bundle = SchemaAcquisitionBundle(
            schema_kind="lpg",
            conceptual_schema={"entities": [{"name": "Person"}]},
            physical_mapping={"entities": {"Person": {"style": "LABEL"}}},
            analyzer_metadata={"source": "heuristic", "warnings": []},
            shape_fingerprint="abc",
            full_fingerprint="def",
            database="hr_demo",
            graph_name="acme_kg",
        )
        d = bundle.to_dict()
        round_tripped = SchemaAcquisitionBundle.from_dict(d)
        assert round_tripped == bundle


# ---------------------------------------------------------------------------
# DETECTED_PATTERN_TAGS contract
# ---------------------------------------------------------------------------


def test_detected_pattern_tags_closed_set():
    """The closed tag set must include all canonical PG / LPG / RPT entries."""
    assert "PG_ENTITY_COLLECTION" in DETECTED_PATTERN_TAGS
    assert "LPG_LABEL" in DETECTED_PATTERN_TAGS
    assert "RPT_TRIPLES" in DETECTED_PATTERN_TAGS
    assert "PG_DEDICATED_EDGE" in DETECTED_PATTERN_TAGS
    assert "LPG_GENERIC_EDGE" in DETECTED_PATTERN_TAGS
    assert "RPT_OBJECT_PROPERTY" in DETECTED_PATTERN_TAGS
