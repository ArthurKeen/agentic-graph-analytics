"""Three-tier schema acquisition for ArangoDB graphs (PRD v0.6 / FR-56..FR-60).

This module is the canonical entry point for "give me a typed
conceptual + physical mapping of this database/graph". It implements:

1. Analyzer tier (primary). Delegates to ``arangodb-schema-analyzer``
   (the ``schema_analyzer`` package) which runs an algorithmic
   baseline first (``infer_baseline_from_snapshot``) and escalates
   to LLM repair only when triggered (PRD FR-58). The analyzer
   handles PG, LPG, hybrid, and (via ``arango-sparql-py``) RPT
   schemas and emits ``style ∈ {COLLECTION, LABEL,
   DEDICATED_COLLECTION, GENERIC_WITH_TYPE}`` mapping styles plus
   confidence + warnings.

2. Heuristic tier (fallback). When the analyzer is not installed,
   :func:`build_heuristic_bundle` samples each non-system collection
   and applies tier-1 / tier-2 type-discriminator detection (the
   same rules used in ``arango-cypher-py.schema_acquire``) to
   produce a best-effort mapping. The result carries
   ``analyzer_metadata.warnings`` containing
   ``ANALYZER_NOT_INSTALLED`` so the UI can surface the degraded
   provenance.

3. Cache tier. Acquisition results are cached keyed by
   ``(database, graph_name)`` with two fingerprints:
   ``shape_fingerprint`` (collections + types + index digests) and
   ``full_fingerprint`` (shape + per-collection counts). When the
   shape matches but counts differ, only the cardinality
   statistics are refreshed (the "stats-only refresh" fast path).

This file is deliberately self-contained: it has no hard dependency
on any product collection. The persistent ``aga_schema_snapshots``
cache backend is wired in
:mod:`graph_analytics_ai.product.repository` and adapts to the
:class:`SchemaCache` Protocol defined here.

The public surface (:func:`acquire_schema`,
:func:`describe_schema_change`, :class:`SchemaAcquisitionBundle`,
:class:`SchemaChangeReport`, :class:`SchemaCache`,
:class:`InMemorySchemaCache`) is the one downstream code (the
:class:`~graph_analytics_ai.ai.agents.specialized.SchemaAnalysisAgent`,
the product service ``discover_graph_profile`` flow, and the
``GET /api/graph-profiles/{id}/schema-change`` endpoint) consumes.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Literal, Optional, Protocol

if TYPE_CHECKING:
    from arango.database import StandardDatabase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


SchemaStrategy = Literal["auto", "analyzer", "heuristic"]
SchemaKind = Literal["pg", "lpg", "hybrid", "rpt", "unknown"]
ChangeStatus = Literal["unchanged", "stats_changed", "shape_changed", "no_cache"]

# Closed tag set for ``analyzer_metadata.detected_patterns`` (PRD FR-64).
# Matches the upstream analyzer + arango-sparql-py heuristic detector so
# downstream consumers can treat the bundles uniformly.
DETECTED_PATTERN_TAGS: tuple[str, ...] = (
    "PG_ENTITY_COLLECTION",
    "LPG_LABEL",
    "RPT_TRIPLES",
    "PG_DEDICATED_EDGE",
    "LPG_GENERIC_EDGE",
    "RPT_OBJECT_PROPERTY",
)


@dataclass(frozen=True)
class SchemaAcquisitionBundle:
    """Result of a successful schema acquisition.

    The bundle is the storage shape of an ``aga_schema_snapshots``
    row and the input shape downstream consumers (``GraphProfile``
    enrichment, ``UseCaseGenerator``, ``TemplateGenerator``) read.

    ``conceptual_schema`` and ``physical_mapping`` follow the
    upstream ``schema_analyzer`` JSON contract so both the
    analyzer-produced and heuristic-produced bundles are structurally
    indistinguishable to consumers; only ``analyzer_metadata.source``
    distinguishes them.
    """

    schema_kind: SchemaKind
    conceptual_schema: Dict[str, Any]
    physical_mapping: Dict[str, Any]
    analyzer_metadata: Dict[str, Any]
    shape_fingerprint: str
    full_fingerprint: str
    database: str = ""
    graph_name: str = "__db__"

    def to_dict(self) -> Dict[str, Any]:
        """Return the JSON-serializable dict shape persisted in the cache."""
        return {
            "schema_kind": self.schema_kind,
            "conceptual_schema": self.conceptual_schema,
            "physical_mapping": self.physical_mapping,
            "analyzer_metadata": self.analyzer_metadata,
            "shape_fingerprint": self.shape_fingerprint,
            "full_fingerprint": self.full_fingerprint,
            "database": self.database,
            "graph_name": self.graph_name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SchemaAcquisitionBundle":
        """Round-trip from the dict shape produced by :meth:`to_dict`."""
        return cls(
            schema_kind=data.get("schema_kind", "unknown"),  # type: ignore[arg-type]
            conceptual_schema=dict(data.get("conceptual_schema") or {}),
            physical_mapping=dict(data.get("physical_mapping") or {}),
            analyzer_metadata=dict(data.get("analyzer_metadata") or {}),
            shape_fingerprint=str(data.get("shape_fingerprint") or ""),
            full_fingerprint=str(data.get("full_fingerprint") or ""),
            database=str(data.get("database") or ""),
            graph_name=str(data.get("graph_name") or "__db__"),
        )


@dataclass(frozen=True)
class SchemaChangeReport:
    """Result of a lightweight schema-change probe (PRD FR-60).

    Cheap: only inspects collection names + index digests + counts.
    Does not run sampling, AQL ``COLLECT``, or LLM. Returned by
    :func:`describe_schema_change` and exposed via
    ``GET /api/graph-profiles/{id}/schema-change``.
    """

    status: ChangeStatus
    current_shape_fingerprint: str
    current_full_fingerprint: str
    cached_shape_fingerprint: Optional[str]
    cached_full_fingerprint: Optional[str]

    @property
    def unchanged(self) -> bool:
        """True iff cached bundle is fully valid (shape + counts match)."""
        return self.status == "unchanged"

    @property
    def needs_full_rebuild(self) -> bool:
        """True iff next ``acquire_schema`` will re-run the analyzer."""
        return self.status in ("shape_changed", "no_cache")


class SchemaCache(Protocol):
    """Backend protocol for persistent acquisition caches.

    The in-memory cache (:class:`InMemorySchemaCache`) implements this
    directly; the persistent ``aga_schema_snapshots`` cache lives in
    :mod:`graph_analytics_ai.product.repository` and adapts the same
    surface so the acquisition module has zero product-package
    dependencies.
    """

    def get(self, key: str) -> Optional[SchemaAcquisitionBundle]: ...

    def set(self, key: str, bundle: SchemaAcquisitionBundle) -> None: ...

    def invalidate(self, key: str) -> None: ...


# ---------------------------------------------------------------------------
# Cache implementations
# ---------------------------------------------------------------------------


class InMemorySchemaCache:
    """Process-local cache. Used as the L1 cache in front of any
    persistent backend, and as the only cache in unit tests.
    """

    def __init__(self) -> None:
        self._store: Dict[str, tuple[SchemaAcquisitionBundle, float]] = {}

    def get(self, key: str) -> Optional[SchemaAcquisitionBundle]:
        entry = self._store.get(key)
        if entry is None:
            return None
        return entry[0]

    def set(self, key: str, bundle: SchemaAcquisitionBundle) -> None:
        self._store[key] = (bundle, time.time())

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        """Test-only convenience to drop everything."""
        self._store.clear()


# Module-singleton L1 cache. Callers pass an explicit ``cache=`` to
# bypass it (e.g. in tests). The L2 (persistent) cache, when present,
# is layered behind this one inside :func:`_lookup_layered_cache`.
_DEFAULT_L1_CACHE: InMemorySchemaCache = InMemorySchemaCache()


def reset_default_cache() -> None:
    """Test helper: drop the module-level L1 cache."""
    _DEFAULT_L1_CACHE.clear()


# ---------------------------------------------------------------------------
# Cache key + fingerprint helpers
# ---------------------------------------------------------------------------


def cache_key(*, database: str, graph_name: str = "__db__") -> str:
    """Deterministic cache key for a (database, graph_name) tuple.

    Hashed so it is safe to use as an ArangoDB ``_key`` (the
    persistent cache backend keys snapshots with this).
    """
    raw = f"{database}|{graph_name}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _shape_fingerprint(db: "StandardDatabase") -> str:
    """Hash of the schema *shape*: collection set, types, index digests.

    Delegates to ``schema_analyzer.fingerprint_physical_shape`` when
    the analyzer is installed (so the digest matches what
    ``arango-cypher-py`` and ``arango-sparql-py`` produce). Falls back
    to a coarse local fingerprint that only notices collection set
    + type changes when the analyzer is missing.

    Excludes row counts so ordinary writes (INSERT / UPDATE / REMOVE
    without a schema shape change) do not invalidate the cache.
    """
    try:
        from schema_analyzer import fingerprint_physical_shape  # type: ignore

        return fingerprint_physical_shape(db)
    except ImportError:
        return _fallback_fingerprint(db, include_counts=False)
    except Exception:  # pragma: no cover — defensive: never crash on probe
        logger.warning("schema_analyzer.fingerprint_physical_shape failed; using fallback", exc_info=True)
        return _fallback_fingerprint(db, include_counts=False)


def _full_fingerprint(db: "StandardDatabase") -> str:
    """Shape fingerprint + per-collection row counts.

    Delegates to ``schema_analyzer.fingerprint_physical_counts`` when
    the analyzer is installed; falls back to a coarse local
    fingerprint that includes counts otherwise.
    """
    try:
        from schema_analyzer import fingerprint_physical_counts  # type: ignore

        return fingerprint_physical_counts(db)
    except ImportError:
        return _fallback_fingerprint(db, include_counts=True)
    except Exception:  # pragma: no cover — defensive
        logger.warning("schema_analyzer.fingerprint_physical_counts failed; using fallback", exc_info=True)
        return _fallback_fingerprint(db, include_counts=True)


def _fallback_fingerprint(db: "StandardDatabase", *, include_counts: bool) -> str:
    """Coarse fingerprint used when ``schema_analyzer`` is unavailable.

    Notices collection-set changes always; row-count changes when
    ``include_counts=True``. Cheap (one ``db.collections()`` call
    plus optionally one ``count()`` per collection).
    """
    try:
        cols = db.collections() or []
    except Exception:
        cols = []
    names = sorted(
        c.get("name", "")
        for c in cols
        if isinstance(c, dict) and isinstance(c.get("name"), str) and not c["name"].startswith("_")
    )
    parts: List[str] = [getattr(db, "name", ""), *names]
    if include_counts:
        for name in names:
            try:
                parts.append(f"{name}:{db.collection(name).count()}")
            except Exception:
                parts.append(f"{name}:-1")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def acquire_schema(
    db: "StandardDatabase",
    *,
    strategy: SchemaStrategy = "auto",
    graph_name: str = "__db__",
    force_refresh: bool = False,
    force_llm: bool = False,
    cache: Optional[SchemaCache] = None,
    review_threshold: float = 0.7,
) -> SchemaAcquisitionBundle:
    """Acquire a schema bundle for ``db``, optionally scoped to ``graph_name``.

    Strategy contract (PRD FR-57):

    - ``analyzer`` — always call the analyzer; raise ``ImportError``
      if it is not installed.
    - ``heuristic`` — never call the analyzer; build the bundle from
      sampling + tier classification.
    - ``auto`` — analyzer first; on ``ImportError`` fall back to
      heuristic and attach an ``ANALYZER_NOT_INSTALLED`` warning.

    Caching contract (PRD FR-59):

    - ``shape`` matches → reuse cached conceptual + physical mapping.
    - ``shape`` matches but ``full`` differs → reuse mapping, refresh
      statistics on top.
    - ``shape`` differs → full re-introspection.
    - ``force_refresh=True`` bypasses caches entirely.

    LLM-on-difficulty escalation (PRD FR-58) is handled inside the
    analyzer; this function passes ``force_llm`` through as a
    metadata hint that the analyzer's prompt-version selection
    respects.
    """
    if strategy not in ("auto", "analyzer", "heuristic"):
        raise ValueError(f"Invalid strategy: {strategy!r}. Must be 'auto', 'analyzer', or 'heuristic'.")

    database = getattr(db, "name", "")
    key = cache_key(database=database, graph_name=graph_name)

    if not force_refresh:
        cached = _lookup_layered_cache(key, cache)
        if cached is not None:
            shape_now = _shape_fingerprint(db)
            if cached.shape_fingerprint == shape_now:
                full_now = _full_fingerprint(db)
                if cached.full_fingerprint == full_now:
                    logger.debug("acquire_schema cache hit (full): %s/%s", database, graph_name)
                    return cached
                logger.info(
                    "acquire_schema shape stable for %s/%s; refreshing cardinality only",
                    database,
                    graph_name,
                )
                refreshed = _refresh_statistics(db, cached, full_fingerprint=full_now)
                _persist_layered(key, refreshed, cache)
                return refreshed
            logger.info("acquire_schema shape changed for %s/%s; full re-introspection", database, graph_name)

    bundle = _build_fresh_bundle(
        db,
        strategy=strategy,
        graph_name=graph_name,
        force_llm=force_llm,
        review_threshold=review_threshold,
    )
    _persist_layered(key, bundle, cache)
    return bundle


def describe_schema_change(
    db: "StandardDatabase",
    *,
    graph_name: str = "__db__",
    cache: Optional[SchemaCache] = None,
) -> SchemaChangeReport:
    """Lightweight schema-change probe (PRD FR-60).

    Cheap: ``db.collections()`` + per-collection ``count()`` +
    ``indexes()``. No sampling, no AQL ``COLLECT``, no LLM call.
    Inspects caches read-only — never mutates them. Typical cost is
    well under 200ms for a 50-collection database.
    """
    shape_now = _shape_fingerprint(db)
    full_now = _full_fingerprint(db)
    database = getattr(db, "name", "")
    key = cache_key(database=database, graph_name=graph_name)

    cached = _lookup_layered_cache(key, cache)
    if cached is None:
        return SchemaChangeReport(
            status="no_cache",
            current_shape_fingerprint=shape_now,
            current_full_fingerprint=full_now,
            cached_shape_fingerprint=None,
            cached_full_fingerprint=None,
        )

    if cached.shape_fingerprint != shape_now:
        status: ChangeStatus = "shape_changed"
    elif cached.full_fingerprint != full_now:
        status = "stats_changed"
    else:
        status = "unchanged"

    return SchemaChangeReport(
        status=status,
        current_shape_fingerprint=shape_now,
        current_full_fingerprint=full_now,
        cached_shape_fingerprint=cached.shape_fingerprint,
        cached_full_fingerprint=cached.full_fingerprint,
    )


# ---------------------------------------------------------------------------
# Internal: cache layering
# ---------------------------------------------------------------------------


def _lookup_layered_cache(
    key: str,
    persistent: Optional[SchemaCache],
) -> Optional[SchemaAcquisitionBundle]:
    """L1 (in-memory) → L2 (persistent if provided). Hydrates L1 on L2 hit."""
    hit = _DEFAULT_L1_CACHE.get(key)
    if hit is not None:
        return hit
    if persistent is None:
        return None
    hit = persistent.get(key)
    if hit is None:
        return None
    _DEFAULT_L1_CACHE.set(key, hit)
    return hit


def _persist_layered(
    key: str,
    bundle: SchemaAcquisitionBundle,
    persistent: Optional[SchemaCache],
) -> None:
    """Write to both cache tiers. Persistent failure is non-fatal."""
    _DEFAULT_L1_CACHE.set(key, bundle)
    if persistent is None:
        return
    try:
        persistent.set(key, bundle)
    except Exception:  # pragma: no cover — defensive
        logger.warning("Persistent schema cache write failed for key %s", key, exc_info=True)


def invalidate_schema_cache(
    *,
    database: str,
    graph_name: str = "__db__",
    cache: Optional[SchemaCache] = None,
) -> None:
    """Drop both L1 and L2 entries for a (database, graph_name) tuple.

    Use after a manual schema migration or when the next acquisition
    must re-introspect unconditionally.
    """
    key = cache_key(database=database, graph_name=graph_name)
    _DEFAULT_L1_CACHE.invalidate(key)
    if cache is not None:
        try:
            cache.invalidate(key)
        except Exception:  # pragma: no cover — defensive
            logger.warning("Persistent cache invalidate failed for key %s", key, exc_info=True)


# ---------------------------------------------------------------------------
# Internal: tier dispatch
# ---------------------------------------------------------------------------


def _build_fresh_bundle(
    db: "StandardDatabase",
    *,
    strategy: SchemaStrategy,
    graph_name: str,
    force_llm: bool,
    review_threshold: float,
) -> SchemaAcquisitionBundle:
    """Run the chosen acquisition strategy and stamp common metadata."""
    if strategy == "analyzer":
        bundle = _build_analyzer_bundle(
            db, graph_name=graph_name, force_llm=force_llm, review_threshold=review_threshold
        )
    elif strategy == "heuristic":
        bundle = build_heuristic_bundle(db, graph_name=graph_name)
    else:
        try:
            bundle = _build_analyzer_bundle(
                db, graph_name=graph_name, force_llm=force_llm, review_threshold=review_threshold
            )
        except ImportError:
            logger.warning(
                "arangodb-schema-analyzer not installed; using heuristic fallback. "
                "Install with: pip install 'arangodb-schema-analyzer>=0.6.1,<0.7'"
            )
            bundle = build_heuristic_bundle(db, graph_name=graph_name)
            bundle = _attach_warning(
                bundle,
                code="ANALYZER_NOT_INSTALLED",
                message=(
                    "arangodb-schema-analyzer is not installed; the bundle was built "
                    "by the heuristic fallback and may misclassify hybrid or RPT schemas."
                ),
                install_hint="pip install 'arangodb-schema-analyzer>=0.6.1,<0.7'",
            )
    return bundle


# ---------------------------------------------------------------------------
# Internal: analyzer tier
# ---------------------------------------------------------------------------


def _build_analyzer_bundle(
    db: "StandardDatabase",
    *,
    graph_name: str,
    force_llm: bool,
    review_threshold: float,
) -> SchemaAcquisitionBundle:
    """Call the upstream ``schema_analyzer`` and translate to a bundle.

    Always raises :class:`ImportError` (not silently degraded) when
    the analyzer is missing — the caller (:func:`_build_fresh_bundle`)
    is the only place we decide to fall back, and only under
    ``strategy == "auto"``.
    """
    try:
        from schema_analyzer import AgenticSchemaAnalyzer  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "arangodb-schema-analyzer is not installed; install with: "
            "pip install 'arangodb-schema-analyzer>=0.6.1,<0.7'"
        ) from exc

    analyzer = AgenticSchemaAnalyzer(review_threshold=review_threshold)
    result = analyzer.analyze_physical_schema(db)
    md = result.metadata.model_dump(by_alias=True)
    md["source"] = _analyzer_source_from_metadata(md)
    md["analyzer_version"] = _analyzer_version_string()
    if force_llm:
        md["force_llm_requested"] = True

    schema_kind = _classify_schema_kind(result.physical_mapping)

    return SchemaAcquisitionBundle(
        schema_kind=schema_kind,
        conceptual_schema=dict(result.conceptual_schema),
        physical_mapping=dict(result.physical_mapping),
        analyzer_metadata=md,
        shape_fingerprint=_shape_fingerprint(db),
        full_fingerprint=_full_fingerprint(db),
        database=getattr(db, "name", ""),
        graph_name=graph_name,
    )


def _analyzer_source_from_metadata(md: Dict[str, Any]) -> str:
    """Translate the upstream analyzer's flags into ``analyzer_metadata.source``."""
    if md.get("usedBaseline") or md.get("used_baseline"):
        return "analyzer_baseline"
    return "analyzer_llm"


def _analyzer_version_string() -> str:
    try:
        from importlib.metadata import version

        return version("arangodb-schema-analyzer")
    except Exception:  # pragma: no cover
        return "unknown"


def _refresh_statistics(
    db: "StandardDatabase",
    cached: SchemaAcquisitionBundle,
    *,
    full_fingerprint: str,
) -> SchemaAcquisitionBundle:
    """Re-run cardinality stats only — shape was unchanged.

    When the analyzer is installed and exposes a stats helper we use
    it so the new ``analyzer_metadata.statistics`` block is
    byte-identical to a fresh acquisition's. Otherwise we just rebuild
    the heuristic counts. The conceptual + physical mapping is
    reused unchanged.
    """
    new_stats = _compute_collection_counts(db)
    new_md = dict(cached.analyzer_metadata)
    new_md.setdefault("statistics", {})
    if isinstance(new_md["statistics"], dict):
        new_md["statistics"]["collection_counts"] = new_stats
    new_md["last_stats_refreshed_at"] = _utc_now_iso()
    return SchemaAcquisitionBundle(
        schema_kind=cached.schema_kind,
        conceptual_schema=cached.conceptual_schema,
        physical_mapping=cached.physical_mapping,
        analyzer_metadata=new_md,
        shape_fingerprint=cached.shape_fingerprint,
        full_fingerprint=full_fingerprint,
        database=cached.database,
        graph_name=cached.graph_name,
    )


def _compute_collection_counts(db: "StandardDatabase") -> Dict[str, int]:
    counts: Dict[str, int] = {}
    try:
        cols = db.collections() or []
    except Exception:
        return counts
    for c in cols:
        if not isinstance(c, dict):
            continue
        name = c.get("name", "")
        if not isinstance(name, str) or not name or name.startswith("_"):
            continue
        try:
            counts[name] = int(db.collection(name).count())
        except Exception:
            counts[name] = -1
    return counts


# ---------------------------------------------------------------------------
# Internal: heuristic tier
# ---------------------------------------------------------------------------


# Tier-1 type-discriminator candidates for documents (always-trusted on the
# 80% coverage rule). Mirrors arango-cypher-py and arango-sparql-py to keep
# bundles structurally indistinguishable across libraries.
_TIER_1_DOC_TYPE_FIELDS: tuple[str, ...] = ("type", "_type", "entityType")
# Tier-2 candidates require additional class-like value validation.
_TIER_2_DOC_TYPE_FIELDS: tuple[str, ...] = ("label", "labels", "kind")
# Edge candidates: all treated as tier-1 (relationship-level discriminators
# are far less likely to be free text than entity-level ones).
_EDGE_TYPE_FIELDS: tuple[str, ...] = ("type", "relation", "relType", "_type")
_HEURISTIC_SAMPLE_SIZE: int = 20
_COVERAGE_THRESHOLD: float = 0.80
_TIER_2_MAX_DISTINCT: int = 32
_TIER_2_MAX_RATIO: float = 0.5
_CLASS_LIKE_VALUE_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def build_heuristic_bundle(
    db: "StandardDatabase",
    *,
    graph_name: str = "__db__",
    sample_size: int = _HEURISTIC_SAMPLE_SIZE,
    now: Optional[datetime] = None,
) -> SchemaAcquisitionBundle:
    """Heuristic fallback (PRD FR-57 tier 2).

    Samples each non-system collection and applies the tier-1 / tier-2
    discriminator rules to classify each as ``COLLECTION``,
    ``LABEL``, ``DEDICATED_COLLECTION``, or ``GENERIC_WITH_TYPE``.
    Aggregates per-collection styles into the overall
    ``schema_kind``. Always emits a low-confidence bundle (0.4) with
    ``review_required = True``.
    """
    classifications = _classify_collections(db, sample_size=sample_size)
    physical_entities, physical_relationships = _emit_physical(classifications)
    conceptual = _emit_conceptual(physical_entities, physical_relationships)
    schema_kind = _aggregate_schema_kind(classifications)
    detected = _detected_pattern_tags(classifications)
    timestamp = (now if now is not None else datetime.now(timezone.utc)).isoformat()

    doc_count = sum(1 for c in classifications if not c.is_edge)
    edge_count = sum(1 for c in classifications if c.is_edge)

    metadata: Dict[str, Any] = {
        "source": "heuristic",
        "confidence": 0.4,
        "review_required": True,
        "used_baseline": True,
        "timestamp": timestamp,
        "detected_patterns": detected,
        "analyzed_collection_counts": {
            "documentCollections": doc_count,
            "edgeCollections": edge_count,
        },
        "warnings": [],
        "assumptions": [
            (
                f"Heuristic detector — physical mapping inferred from "
                f"{sample_size}-doc per-collection samples, not from an "
                "OWL ontology. Cross-collection relationship endpoints are "
                "left as fromEntity/toEntity = 'Any'."
            )
        ],
    }

    return SchemaAcquisitionBundle(
        schema_kind=schema_kind,
        conceptual_schema=conceptual,
        physical_mapping={
            "entities": physical_entities,
            "relationships": physical_relationships,
        },
        analyzer_metadata=metadata,
        shape_fingerprint=_shape_fingerprint(db),
        full_fingerprint=_full_fingerprint(db),
        database=getattr(db, "name", ""),
        graph_name=graph_name,
    )


@dataclass(frozen=True)
class _CollectionClassification:
    name: str
    is_edge: bool
    style: Literal["COLLECTION", "LABEL", "DEDICATED_COLLECTION", "GENERIC_WITH_TYPE"]
    type_field: Optional[str] = None
    type_values: tuple[str, ...] = field(default_factory=tuple)
    sampled_docs: int = 0


def _classify_collections(
    db: "StandardDatabase",
    *,
    sample_size: int,
) -> List[_CollectionClassification]:
    """Per-collection LPG/PG classification using the tier rules."""
    out: List[_CollectionClassification] = []
    for name, is_edge in _list_user_collections(db):
        sample = _sample_collection(db, name, sample_size)
        out.append(_classify_collection(name, is_edge=is_edge, sample=sample))
    return out


def _list_user_collections(db: "StandardDatabase") -> List[tuple[str, bool]]:
    try:
        rows = db.collections() or []
    except Exception:
        return []
    out: List[tuple[str, bool]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        if not isinstance(name, str) or not name or name.startswith("_"):
            continue
        ctype = row.get("type")
        is_edge = ctype == "edge" or ctype == 3
        out.append((name, bool(is_edge)))
    out.sort(key=lambda pair: pair[0])
    return out


def _sample_collection(db: "StandardDatabase", name: str, sample_size: int) -> List[Dict[str, Any]]:
    if sample_size <= 0:
        return []
    try:
        cursor = db.aql.execute(
            "FOR doc IN @@col LIMIT @n RETURN doc",
            bind_vars={"@col": name, "n": int(sample_size)},
        )
        return [doc for doc in cursor if isinstance(doc, dict)]
    except Exception:
        return []


def _classify_collection(
    name: str,
    *,
    is_edge: bool,
    sample: List[Dict[str, Any]],
) -> _CollectionClassification:
    sampled = len(sample)

    if not is_edge:
        disc = _detect_discriminator(
            sample,
            tier_1_fields=_TIER_1_DOC_TYPE_FIELDS,
            tier_2_fields=_TIER_2_DOC_TYPE_FIELDS,
        )
        if disc is not None:
            return _CollectionClassification(
                name=name,
                is_edge=False,
                style="LABEL",
                type_field=disc[0],
                type_values=tuple(sorted(disc[1])),
                sampled_docs=sampled,
            )
        return _CollectionClassification(name=name, is_edge=False, style="COLLECTION", sampled_docs=sampled)

    disc = _detect_discriminator(sample, tier_1_fields=_EDGE_TYPE_FIELDS, tier_2_fields=())
    if disc is not None:
        return _CollectionClassification(
            name=name,
            is_edge=True,
            style="GENERIC_WITH_TYPE",
            type_field=disc[0],
            type_values=tuple(sorted(disc[1])),
            sampled_docs=sampled,
        )
    return _CollectionClassification(name=name, is_edge=True, style="DEDICATED_COLLECTION", sampled_docs=sampled)


def _detect_discriminator(
    sample: List[Dict[str, Any]],
    *,
    tier_1_fields: tuple[str, ...],
    tier_2_fields: tuple[str, ...],
) -> Optional[tuple[str, set[str]]]:
    if not sample:
        return None
    n = len(sample)

    for field_name in tier_1_fields:
        present = [d[field_name] for d in sample if field_name in d]
        if len(present) / n < _COVERAGE_THRESHOLD:
            continue
        distinct = set(_flatten_values(present))
        if not distinct:
            continue
        return field_name, distinct

    for field_name in tier_2_fields:
        present = [d[field_name] for d in sample if field_name in d]
        if len(present) / n < _COVERAGE_THRESHOLD:
            continue
        distinct = set(_flatten_values(present))
        if not distinct:
            continue
        # Cardinality checks operate on DISTINCT values, not the flat
        # value list — otherwise a 5-doc sample with values
        # ["Alpha", "Alpha", "Beta", "Beta", "Beta"] would compute
        # 5/5 == 1.0 > 0.5 and reject a perfectly good discriminator.
        if len(distinct) > _TIER_2_MAX_DISTINCT:
            continue
        if len(distinct) / n > _TIER_2_MAX_RATIO:
            continue
        if not all(_CLASS_LIKE_VALUE_RE.match(v) for v in distinct):
            continue
        return field_name, distinct

    return None


def _flatten_values(raw: List[Any]) -> List[str]:
    out: List[str] = []
    for v in raw:
        if isinstance(v, list):
            for item in v:
                if isinstance(item, str) and item:
                    out.append(item)
        elif isinstance(v, str) and v:
            out.append(v)
    return out


def _emit_physical(
    classifications: List[_CollectionClassification],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    entities: Dict[str, Any] = {}
    relationships: Dict[str, Any] = {}
    for c in classifications:
        if c.is_edge:
            if c.style == "GENERIC_WITH_TYPE":
                for tv in c.type_values:
                    if not tv:
                        continue
                    relationships[tv] = {
                        "style": "GENERIC_WITH_TYPE",
                        "edgeCollectionName": c.name,
                        "typeField": c.type_field,
                        "typeValue": tv,
                        "fromEntity": "Any",
                        "toEntity": "Any",
                    }
            else:
                relationships[c.name] = {
                    "style": "DEDICATED_COLLECTION",
                    "edgeCollectionName": c.name,
                    "fromEntity": "Any",
                    "toEntity": "Any",
                }
        else:
            if c.style == "LABEL":
                for tv in c.type_values:
                    if not tv:
                        continue
                    entities[tv] = {
                        "style": "LABEL",
                        "collectionName": c.name,
                        "typeField": c.type_field,
                        "typeValue": tv,
                    }
            else:
                entities[c.name] = {"style": "COLLECTION", "collectionName": c.name}
    return entities, relationships


def _emit_conceptual(
    entities: Dict[str, Any],
    relationships: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "entities": [
            {"name": name, "labels": [name], "properties": []}
            for name in sorted(entities)
        ],
        "relationships": [
            {
                "type": rt,
                "fromEntity": spec.get("fromEntity", "Any"),
                "toEntity": spec.get("toEntity", "Any"),
                "properties": [],
            }
            for rt, spec in sorted(relationships.items())
        ],
        "properties": [],
    }


def _aggregate_schema_kind(
    classifications: List[_CollectionClassification],
) -> SchemaKind:
    if not classifications:
        return "unknown"
    entity_styles = {c.style for c in classifications if not c.is_edge}
    edge_styles = {c.style for c in classifications if c.is_edge}
    is_pg = entity_styles <= {"COLLECTION"} and edge_styles <= {"DEDICATED_COLLECTION"}
    is_lpg = entity_styles <= {"LABEL"} and edge_styles <= {"GENERIC_WITH_TYPE"}
    if is_pg and entity_styles:
        return "pg"
    if is_lpg and entity_styles:
        return "lpg"
    if not entity_styles and not edge_styles:
        return "unknown"
    return "hybrid"


def _detected_pattern_tags(classifications: List[_CollectionClassification]) -> List[str]:
    tags: set[str] = set()
    for c in classifications:
        if c.is_edge:
            tags.add("LPG_GENERIC_EDGE" if c.style == "GENERIC_WITH_TYPE" else "PG_DEDICATED_EDGE")
        else:
            tags.add("LPG_LABEL" if c.style == "LABEL" else "PG_ENTITY_COLLECTION")
    return [t for t in DETECTED_PATTERN_TAGS if t in tags]


# ---------------------------------------------------------------------------
# Internal: classification of analyzer-built bundles
# ---------------------------------------------------------------------------


def _classify_schema_kind(physical_mapping: Dict[str, Any]) -> SchemaKind:
    """Roll-up the analyzer's per-entity / per-relationship styles to a single tag."""
    entities = physical_mapping.get("entities") or {}
    relationships = physical_mapping.get("relationships") or {}

    entity_styles = {
        spec.get("style") for spec in entities.values() if isinstance(spec, dict) and spec.get("style")
    }
    rel_styles = {
        spec.get("style") for spec in relationships.values() if isinstance(spec, dict) and spec.get("style")
    }

    if "RPT" in entity_styles and not (entity_styles - {"RPT"}):
        return "rpt"

    is_pg = entity_styles <= {"COLLECTION"} and rel_styles <= {"DEDICATED_COLLECTION"}
    is_lpg = entity_styles <= {"LABEL"} and rel_styles <= {"GENERIC_WITH_TYPE"}

    if is_pg and entity_styles:
        return "pg"
    if is_lpg and entity_styles:
        return "lpg"
    if not entity_styles and not rel_styles:
        return "unknown"
    return "hybrid"


# ---------------------------------------------------------------------------
# Internal: warnings
# ---------------------------------------------------------------------------


def _attach_warning(
    bundle: SchemaAcquisitionBundle,
    *,
    code: str,
    message: str,
    install_hint: Optional[str] = None,
) -> SchemaAcquisitionBundle:
    """Return a copy of ``bundle`` with one extra structured warning.

    Warnings live at ``analyzer_metadata.warnings`` as a list of
    dicts. Existing warnings are preserved.
    """
    md = dict(bundle.analyzer_metadata)
    warnings = list(md.get("warnings") or [])
    warning: Dict[str, Any] = {"code": code, "message": message}
    if install_hint:
        warning["install_hint"] = install_hint
    warnings.append(warning)
    md["warnings"] = warnings
    md["review_required"] = True
    return SchemaAcquisitionBundle(
        schema_kind=bundle.schema_kind,
        conceptual_schema=bundle.conceptual_schema,
        physical_mapping=bundle.physical_mapping,
        analyzer_metadata=md,
        shape_fingerprint=bundle.shape_fingerprint,
        full_fingerprint=bundle.full_fingerprint,
        database=bundle.database,
        graph_name=bundle.graph_name,
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


__all__ = [
    "SchemaStrategy",
    "SchemaKind",
    "ChangeStatus",
    "SchemaAcquisitionBundle",
    "SchemaChangeReport",
    "SchemaCache",
    "InMemorySchemaCache",
    "DETECTED_PATTERN_TAGS",
    "acquire_schema",
    "describe_schema_change",
    "build_heuristic_bundle",
    "cache_key",
    "invalidate_schema_cache",
    "reset_default_cache",
]
