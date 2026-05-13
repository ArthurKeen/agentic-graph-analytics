"""Graph-purpose classifier (PRD v0.6 / FR-61..FR-63).

Given an acquired :class:`~graph_analytics_ai.ai.schema.acquire.SchemaAcquisitionBundle`,
this module classifies a graph by its analytical *purpose* — the
semantic role it plays in a workspace — independent of how it is
physically encoded.

Purposes form a closed set:

- ``corpus`` — text-extraction substrate. The canonical ArangoDB
  GraphRAG corpus shape: Documents + Chunks + ``part_of`` edges.
  Often contains ``mentions`` edges that bridge into a knowledge
  graph.
- ``knowledge_graph`` — an LPG (or PG) of entities + relationships
  derived from a corpus. The ArangoDB GraphRAG KG: Entities,
  Relationships, optional Communities + ``in_community`` edges.
  Also matches hand-curated ontologies that share the same
  surface (any LPG with an ``Entities`` collection plus a
  ``Relationships`` edge collection discriminated by ``type``).
- ``structured`` — traditional collection-typed PG (one collection
  per entity type, dedicated edge collections). E-commerce,
  HR/HRIS, network/IT, supply-chain graphs all land here when
  modeled as a PG.
- ``analytics`` — a derived/output graph that exists only to serve
  GAE / vector / index workloads. Detected by names like
  ``communities``, ``embeddings``, ``recommendations``,
  ``pagerank_*``, ``louvain_*``.
- ``hybrid`` — multiple purposes coexist in a single named graph
  (a corpus that also stores its own KG, etc.). Returned when the
  detector fires more than one non-``analytics`` rule.
- ``unknown`` — no rule fired with sufficient confidence.

The classifier is deterministic and runs on the bundle alone — no
DB calls, no LLM. It is cheap to call from
``discover_graph_profile``, the GraphSet workbench, and the
schema-change probe so a UI badge can update on every reacquisition.

Outputs always include a numeric ``confidence`` and a
human-readable ``reasons`` list so the UI can render an
explainable badge ("knowledge_graph (0.86) — found Entities and
Relationships collections, with type field as discriminator").
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, FrozenSet, List, Literal, Optional, Tuple

if TYPE_CHECKING:
    from .acquire import SchemaAcquisitionBundle

logger = logging.getLogger(__name__)


GraphPurpose = Literal[
    "corpus",
    "knowledge_graph",
    "structured",
    "analytics",
    "hybrid",
    "unknown",
]


# Canonical detection cutoffs. A rule "fires" when its computed score
# meets MIN_RULE_SCORE; the final classification is the highest-scoring
# rule above MIN_OVERALL_CONFIDENCE. Two rules above MIN_RULE_SCORE
# both also above MIN_HYBRID_DELTA of each other escalate to "hybrid".
MIN_RULE_SCORE: float = 0.50
MIN_OVERALL_CONFIDENCE: float = 0.40
MIN_HYBRID_DELTA: float = 0.15


# Closed sets of name patterns the rules recognize. Case-insensitive
# match. Mirrors arangodb-schema-analyzer's docs and the published
# ArangoDB GraphRAG importer surface so a corpus generated with the
# default importer always classifies as "corpus".
_GRAPHRAG_CORPUS_COLLECTIONS: FrozenSet[str] = frozenset(
    {"documents", "document", "chunks", "chunk", "passages", "passage"}
)
_GRAPHRAG_CORPUS_EDGES: FrozenSet[str] = frozenset(
    {"part_of", "partof", "contains", "has_chunk", "haschunk"}
)
_GRAPHRAG_KG_ENTITY_COLLECTIONS: FrozenSet[str] = frozenset(
    {"entities", "entity", "nodes", "concepts"}
)
_GRAPHRAG_KG_REL_COLLECTIONS: FrozenSet[str] = frozenset(
    {"relationships", "relations", "relationship", "edges", "links"}
)
_GRAPHRAG_KG_COMMUNITY_COLLECTIONS: FrozenSet[str] = frozenset(
    {"communities", "community", "clusters", "cluster"}
)
_GRAPHRAG_KG_BRIDGE_EDGES: FrozenSet[str] = frozenset(
    {"mentions", "mention", "extracted_from", "in_community", "incommunity"}
)

_ANALYTICS_HINT_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"^embeddings?$", re.IGNORECASE),
    re.compile(r"^recommendations?$", re.IGNORECASE),
    re.compile(r"^pagerank.*$", re.IGNORECASE),
    re.compile(r"^louvain.*$", re.IGNORECASE),
    re.compile(r"^centrality.*$", re.IGNORECASE),
    re.compile(r"^similarity.*$", re.IGNORECASE),
    re.compile(r"^scores?$", re.IGNORECASE),
    re.compile(r"^projections?$", re.IGNORECASE),
)


@dataclass(frozen=True)
class GraphPurposeResult:
    """Outcome of :func:`classify_graph_purpose`.

    ``purpose`` is the rolled-up classification. ``confidence`` is the
    winning rule's score (or the average of the top two when
    ``purpose == "hybrid"``). ``reasons`` is an ordered list of
    human-readable evidence strings the UI can show in a tooltip.
    ``per_rule_scores`` exposes every rule's score so the
    workbench can render a small bar chart on demand.
    """

    purpose: GraphPurpose
    confidence: float
    reasons: List[str] = field(default_factory=list)
    per_rule_scores: Dict[str, float] = field(default_factory=dict)
    detected_collections: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        """Serialize for API / persistence."""
        return {
            "purpose": self.purpose,
            "confidence": round(self.confidence, 3),
            "reasons": list(self.reasons),
            "per_rule_scores": {k: round(v, 3) for k, v in self.per_rule_scores.items()},
            "detected_collections": {
                k: list(v) for k, v in self.detected_collections.items()
            },
        }


def classify_graph_purpose(
    bundle: "SchemaAcquisitionBundle",
    *,
    extra_collection_hints: Optional[Dict[str, str]] = None,
) -> GraphPurposeResult:
    """Classify a bundle's analytical purpose.

    ``extra_collection_hints`` lets callers feed in collection names
    that exist in the database but were not surfaced by the
    acquisition bundle (rare — typically only used by the GraphSet
    workbench when it wants to broaden the heuristic to cover
    sibling graphs in the same database). Each entry is treated as
    a synthetic collection of the named ``type`` ("vertex" or
    "edge"). Pass ``None`` for the common case.
    """

    collection_inventory = _build_inventory(bundle, extra_collection_hints)

    rule_scores: Dict[str, float] = {}
    rule_reasons: Dict[str, List[str]] = {}
    rule_collections: Dict[str, List[str]] = {}

    for rule_name, scorer in _RULES:
        score, reasons, hits = scorer(collection_inventory)
        rule_scores[rule_name] = score
        rule_reasons[rule_name] = reasons
        rule_collections[rule_name] = hits

    return _aggregate(rule_scores, rule_reasons, rule_collections)


# ---------------------------------------------------------------------------
# Internal: inventory
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Inventory:
    """Normalized view of a bundle's collection landscape."""

    document_collections: FrozenSet[str]
    edge_collections: FrozenSet[str]
    entity_logical_names: FrozenSet[str]
    relationship_logical_names: FrozenSet[str]


def _build_inventory(
    bundle: "SchemaAcquisitionBundle",
    extra_collection_hints: Optional[Dict[str, str]],
) -> _Inventory:
    docs: set[str] = set()
    edges: set[str] = set()

    for spec in (bundle.physical_mapping.get("entities") or {}).values():
        if isinstance(spec, dict):
            name = spec.get("collectionName")
            if isinstance(name, str) and name:
                docs.add(name.lower())
    for spec in (bundle.physical_mapping.get("relationships") or {}).values():
        if isinstance(spec, dict):
            name = spec.get("edgeCollectionName")
            if isinstance(name, str) and name:
                edges.add(name.lower())

    if extra_collection_hints:
        for name, kind in extra_collection_hints.items():
            if not name:
                continue
            if kind == "edge":
                edges.add(name.lower())
            else:
                docs.add(name.lower())

    entity_names: set[str] = set()
    for entity in bundle.conceptual_schema.get("entities") or []:
        if isinstance(entity, dict) and isinstance(entity.get("name"), str):
            entity_names.add(entity["name"].lower())
    rel_names: set[str] = set()
    for rel in bundle.conceptual_schema.get("relationships") or []:
        if isinstance(rel, dict) and isinstance(rel.get("type"), str):
            rel_names.add(rel["type"].lower())

    return _Inventory(
        document_collections=frozenset(docs),
        edge_collections=frozenset(edges),
        entity_logical_names=frozenset(entity_names),
        relationship_logical_names=frozenset(rel_names),
    )


# ---------------------------------------------------------------------------
# Internal: scoring rules
# ---------------------------------------------------------------------------


def _score_corpus(inv: _Inventory) -> Tuple[float, List[str], List[str]]:
    """Detects the GraphRAG corpus shape: Documents + Chunks + part_of."""
    hits = inv.document_collections & _GRAPHRAG_CORPUS_COLLECTIONS
    edge_hits = inv.edge_collections & _GRAPHRAG_CORPUS_EDGES
    if not hits:
        return 0.0, [], []

    score = 0.0
    reasons: List[str] = []
    if {"documents", "document"} & hits:
        score += 0.45
        reasons.append("found Documents collection (corpus root)")
    if {"chunks", "chunk", "passages", "passage"} & hits:
        score += 0.40
        reasons.append("found Chunks collection (corpus subdivision)")
    if edge_hits:
        score += 0.20
        reasons.append(
            f"found corpus structural edge(s): {sorted(edge_hits)}"
        )
    if score > 1.0:
        score = 1.0
    detected = sorted(hits | edge_hits)
    return score, reasons, detected


def _score_knowledge_graph(inv: _Inventory) -> Tuple[float, List[str], List[str]]:
    """Detects an LPG/PG knowledge graph (ArangoDB GraphRAG KG or curated)."""
    entity_hits = inv.document_collections & _GRAPHRAG_KG_ENTITY_COLLECTIONS
    rel_hits = inv.edge_collections & _GRAPHRAG_KG_REL_COLLECTIONS
    community_hits = inv.document_collections & _GRAPHRAG_KG_COMMUNITY_COLLECTIONS
    bridge_hits = inv.edge_collections & _GRAPHRAG_KG_BRIDGE_EDGES

    if not entity_hits and not rel_hits:
        # Fall back to logical-name match so a curated ontology that uses
        # collection names like ``Person``, ``Org``, ``Skill`` and
        # discriminator-style edges still scores.
        if len(inv.entity_logical_names) >= 3 and len(inv.relationship_logical_names) >= 2:
            return (
                0.45,
                [
                    f"{len(inv.entity_logical_names)} logical entities and "
                    f"{len(inv.relationship_logical_names)} relationship types — "
                    "matches a curated KG shape"
                ],
                [],
            )
        return 0.0, [], []

    score = 0.0
    reasons: List[str] = []
    if entity_hits:
        score += 0.45
        reasons.append(
            f"found Entities-style collection(s): {sorted(entity_hits)}"
        )
    if rel_hits:
        score += 0.40
        reasons.append(
            f"found Relationships-style collection(s): {sorted(rel_hits)}"
        )
    if community_hits:
        score += 0.10
        reasons.append(
            f"found Communities collection(s): {sorted(community_hits)}"
        )
    if bridge_hits:
        score += 0.10
        reasons.append(
            f"found KG bridge edge(s): {sorted(bridge_hits)}"
        )
    if score > 1.0:
        score = 1.0
    detected = sorted(entity_hits | rel_hits | community_hits | bridge_hits)
    return score, reasons, detected


def _score_structured(inv: _Inventory) -> Tuple[float, List[str], List[str]]:
    """Detects a traditional collection-typed PG.

    The signal is *negative*: many distinct entity collections that
    don't match the corpus or KG name sets, with dedicated edge
    collections (no ``Entities`` / ``Relationships`` generic
    collections). We additionally require at least three entities so
    a tiny test graph doesn't accidentally satisfy the rule.
    """
    if (
        inv.document_collections & _GRAPHRAG_CORPUS_COLLECTIONS
        or inv.document_collections & _GRAPHRAG_KG_ENTITY_COLLECTIONS
        or inv.edge_collections & _GRAPHRAG_KG_REL_COLLECTIONS
    ):
        return 0.0, [], []

    n_entities = len(inv.entity_logical_names) or len(inv.document_collections)
    n_rels = len(inv.relationship_logical_names) or len(inv.edge_collections)

    if n_entities < 3:
        return 0.0, [], []

    score = 0.55
    reasons = [
        f"{n_entities} dedicated entity collections, "
        f"{n_rels} dedicated edge collections — classic PG shape"
    ]
    if n_entities >= 5:
        score += 0.15
        reasons.append("entity-collection count ≥ 5 raises PG confidence")
    if n_rels >= 3:
        score += 0.10
        reasons.append("dedicated edge-collection count ≥ 3 raises PG confidence")
    score = min(score, 1.0)
    return score, reasons, sorted(inv.document_collections)


def _score_analytics(inv: _Inventory) -> Tuple[float, List[str], List[str]]:
    """Detects derived/output graphs serving GAE/vector workloads."""
    matches: List[str] = []
    for name in inv.document_collections | inv.edge_collections:
        for pattern in _ANALYTICS_HINT_PATTERNS:
            if pattern.match(name):
                matches.append(name)
                break

    if not matches:
        return 0.0, [], []

    score = min(0.30 + 0.20 * len(matches), 1.0)
    reasons = [
        f"matched analytics naming pattern(s) in: {sorted(matches)}"
    ]
    return score, reasons, sorted(matches)


# Order is presentation-only. Aggregation picks the highest score.
_RULES: Tuple[
    Tuple[GraphPurpose, "_Scorer"],
    ...,
] = (
    ("corpus", _score_corpus),
    ("knowledge_graph", _score_knowledge_graph),
    ("structured", _score_structured),
    ("analytics", _score_analytics),
)


# Type alias: a scorer takes the inventory, returns
# (score, reasons, detected-collection-list).
_Scorer = "callable[[_Inventory], Tuple[float, List[str], List[str]]]"


# ---------------------------------------------------------------------------
# Internal: aggregation
# ---------------------------------------------------------------------------


def _aggregate(
    rule_scores: Dict[str, float],
    rule_reasons: Dict[str, List[str]],
    rule_collections: Dict[str, List[str]],
) -> GraphPurposeResult:
    """Pick the winning purpose (or hybrid / unknown).

    Aggregation rules:

    - If no rule scored ≥ MIN_OVERALL_CONFIDENCE → ``unknown``.
    - If exactly one rule (excluding analytics) scored ≥ MIN_RULE_SCORE
      → that rule wins. Analytics is allowed as a stand-alone winner
      when nothing else fired.
    - If two or more *non-analytics* rules scored ≥ MIN_RULE_SCORE and
      are within MIN_HYBRID_DELTA of each other → ``hybrid`` with
      confidence equal to their average.
    - Otherwise the single highest-scoring rule wins.
    """

    non_analytics_above = {
        name: score
        for name, score in rule_scores.items()
        if name != "analytics" and score >= MIN_RULE_SCORE
    }

    # Sort non-analytics rules by score descending for the top-2 check.
    ranked = sorted(non_analytics_above.items(), key=lambda kv: kv[1], reverse=True)

    if len(ranked) >= 2 and abs(ranked[0][1] - ranked[1][1]) <= MIN_HYBRID_DELTA:
        top_two = ranked[:2]
        avg = sum(score for _, score in top_two) / 2.0
        winners = [name for name, _ in top_two]
        reasons: List[str] = [
            f"hybrid graph — both {winners[0]} and {winners[1]} signals fired"
        ]
        for name, _ in top_two:
            reasons.extend(rule_reasons.get(name, []))
        detected: Dict[str, List[str]] = {
            name: rule_collections.get(name, []) for name, _ in top_two
        }
        return GraphPurposeResult(
            purpose="hybrid",
            confidence=avg,
            reasons=reasons,
            per_rule_scores=rule_scores,
            detected_collections=detected,
        )

    if ranked:
        winner_name, winner_score = ranked[0]
        return GraphPurposeResult(
            purpose=winner_name,  # type: ignore[arg-type]
            confidence=winner_score,
            reasons=list(rule_reasons.get(winner_name, [])),
            per_rule_scores=rule_scores,
            detected_collections={winner_name: rule_collections.get(winner_name, [])},
        )

    # Analytics-only fallback: when nothing else fired but analytics
    # did. Treated separately because a graph that *only* contains
    # an embeddings collection is genuinely an analytics output.
    analytics_score = rule_scores.get("analytics", 0.0)
    if analytics_score >= MIN_OVERALL_CONFIDENCE:
        return GraphPurposeResult(
            purpose="analytics",
            confidence=analytics_score,
            reasons=list(rule_reasons.get("analytics", [])),
            per_rule_scores=rule_scores,
            detected_collections={
                "analytics": rule_collections.get("analytics", []),
            },
        )

    return GraphPurposeResult(
        purpose="unknown",
        confidence=max(rule_scores.values()) if rule_scores else 0.0,
        reasons=["no detection rule scored above the minimum confidence"],
        per_rule_scores=rule_scores,
        detected_collections={},
    )


__all__ = [
    "GraphPurpose",
    "GraphPurposeResult",
    "MIN_HYBRID_DELTA",
    "MIN_OVERALL_CONFIDENCE",
    "MIN_RULE_SCORE",
    "classify_graph_purpose",
]
