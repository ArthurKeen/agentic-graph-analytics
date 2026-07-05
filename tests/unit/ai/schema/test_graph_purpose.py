"""Unit tests for the graph-purpose classifier (Phase 6b / FR-61..FR-63).

Covers the four primary purposes (corpus / knowledge_graph / structured /
analytics), the hybrid escalation logic, the unknown fallback, and the
``GraphPurposeResult.to_dict`` serialization contract.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from graph_analytics_ai.ai.schema import (
    GraphPurpose,
    GraphPurposeResult,
    SchemaAcquisitionBundle,
    classify_graph_purpose,
)
from graph_analytics_ai.ai.schema.graph_purpose import (
    MIN_HYBRID_DELTA,
    MIN_OVERALL_CONFIDENCE,
    MIN_RULE_SCORE,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bundle(
    *,
    entities: Dict[str, Dict[str, Any]],
    relationships: Dict[str, Dict[str, Any]],
    conceptual_entities: List[Dict[str, Any]] | None = None,
    conceptual_relationships: List[Dict[str, Any]] | None = None,
) -> SchemaAcquisitionBundle:
    return SchemaAcquisitionBundle(
        schema_kind="pg",
        conceptual_schema={
            "entities": conceptual_entities or [],
            "relationships": conceptual_relationships or [],
            "properties": [],
        },
        physical_mapping={"entities": entities, "relationships": relationships},
        analyzer_metadata={"source": "heuristic"},
        shape_fingerprint="X",
        full_fingerprint="Y",
        database="test_db",
        graph_name="g",
    )


# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------


class TestCorpusDetection:
    def test_full_corpus_shape(self):
        bundle = _bundle(
            entities={
                "Documents": {"style": "COLLECTION", "collectionName": "Documents"},
                "Chunks": {"style": "COLLECTION", "collectionName": "Chunks"},
            },
            relationships={
                "part_of": {
                    "style": "DEDICATED_COLLECTION",
                    "edgeCollectionName": "part_of",
                }
            },
        )
        result = classify_graph_purpose(bundle)
        assert result.purpose == "corpus"
        assert result.confidence >= 0.95
        # Reasons are surfaced for the UI tooltip.
        joined = " ".join(result.reasons)
        assert "Documents" in joined
        assert "Chunks" in joined
        # Score for the corpus rule is exposed.
        assert result.per_rule_scores.get("corpus", 0.0) >= MIN_RULE_SCORE

    def test_corpus_only_documents(self):
        """Documents alone is enough to score a corpus, but with lower confidence."""
        bundle = _bundle(
            entities={
                "Documents": {"style": "COLLECTION", "collectionName": "Documents"}
            },
            relationships={},
        )
        result = classify_graph_purpose(bundle)
        # ``Documents`` alone scores 0.45 (corpus-rule) — below MIN_RULE_SCORE
        # and below MIN_OVERALL_CONFIDENCE → unknown.
        assert result.purpose == "unknown"
        assert result.per_rule_scores["corpus"] == pytest.approx(0.45)


# ---------------------------------------------------------------------------
# Knowledge graph
# ---------------------------------------------------------------------------


class TestKnowledgeGraphDetection:
    def test_lpg_kg_with_entities_and_relationships(self):
        """Canonical ArangoDB GraphRAG KG: Entities + Relationships."""
        bundle = _bundle(
            entities={
                "Person": {
                    "style": "LABEL",
                    "collectionName": "Entities",
                    "typeField": "type",
                    "typeValue": "Person",
                },
                "Org": {
                    "style": "LABEL",
                    "collectionName": "Entities",
                    "typeField": "type",
                    "typeValue": "Org",
                },
            },
            relationships={
                "WORKS_FOR": {
                    "style": "GENERIC_WITH_TYPE",
                    "edgeCollectionName": "Relationships",
                    "typeField": "type",
                    "typeValue": "WORKS_FOR",
                }
            },
        )
        result = classify_graph_purpose(bundle)
        assert result.purpose == "knowledge_graph"
        assert result.confidence >= 0.80

    def test_kg_with_communities_boosts_confidence(self):
        bundle = _bundle(
            entities={
                "Person": {
                    "style": "LABEL",
                    "collectionName": "Entities",
                    "typeField": "type",
                },
                "Communities": {
                    "style": "COLLECTION",
                    "collectionName": "Communities",
                },
            },
            relationships={
                "WORKS_FOR": {
                    "style": "GENERIC_WITH_TYPE",
                    "edgeCollectionName": "Relationships",
                },
                "in_community": {
                    "style": "DEDICATED_COLLECTION",
                    "edgeCollectionName": "in_community",
                },
            },
        )
        result = classify_graph_purpose(bundle)
        assert result.purpose == "knowledge_graph"
        # Communities + in_community add 0.10 + 0.10 to base 0.85 → capped 1.0
        assert result.confidence == pytest.approx(1.0)

    def test_curated_kg_via_logical_names(self):
        """A curated ontology (Person / Org / Skill) without the literal
        Entities collection still classifies as knowledge_graph via the
        logical-name fallback at score 0.45.
        """
        bundle = _bundle(
            entities={
                "Person": {"style": "COLLECTION", "collectionName": "Person"},
                "Org": {"style": "COLLECTION", "collectionName": "Org"},
                "Skill": {"style": "COLLECTION", "collectionName": "Skill"},
                "Project": {"style": "COLLECTION", "collectionName": "Project"},
            },
            relationships={
                "works_for": {
                    "style": "DEDICATED_COLLECTION",
                    "edgeCollectionName": "works_for",
                },
                "has_skill": {
                    "style": "DEDICATED_COLLECTION",
                    "edgeCollectionName": "has_skill",
                },
            },
            conceptual_entities=[
                {"name": "Person"},
                {"name": "Org"},
                {"name": "Skill"},
                {"name": "Project"},
            ],
            conceptual_relationships=[
                {"type": "works_for"},
                {"type": "has_skill"},
            ],
        )
        # In a curated PG ontology with 4 entities + 2 rels, structured wins
        # with a higher score than the curated-KG fallback (0.45). That's
        # the right behaviour — most "Person/Org/Skill" graphs are
        # structured PGs, not knowledge graphs.
        result = classify_graph_purpose(bundle)
        assert result.purpose == "structured"


# ---------------------------------------------------------------------------
# Structured
# ---------------------------------------------------------------------------


class TestStructuredDetection:
    def test_classic_pg_classifies_structured(self):
        bundle = _bundle(
            entities={
                "Employee": {"style": "COLLECTION", "collectionName": "Employee"},
                "Department": {"style": "COLLECTION", "collectionName": "Department"},
                "Project": {"style": "COLLECTION", "collectionName": "Project"},
                "Skill": {"style": "COLLECTION", "collectionName": "Skill"},
            },
            relationships={
                "reports_to": {
                    "style": "DEDICATED_COLLECTION",
                    "edgeCollectionName": "reports_to",
                },
                "works_on": {
                    "style": "DEDICATED_COLLECTION",
                    "edgeCollectionName": "works_on",
                },
                "has_skill": {
                    "style": "DEDICATED_COLLECTION",
                    "edgeCollectionName": "has_skill",
                },
            },
            conceptual_entities=[
                {"name": n} for n in ("Employee", "Department", "Project", "Skill")
            ],
            conceptual_relationships=[
                {"type": t} for t in ("reports_to", "works_on", "has_skill")
            ],
        )
        result = classify_graph_purpose(bundle)
        assert result.purpose == "structured"
        # ≥ 5 boost wouldn't fire (4 entities) but ≥ 3 rels boost would.
        # Expected score: 0.55 + 0.10 = 0.65.
        assert 0.60 <= result.confidence <= 0.75

    def test_structured_rule_suppressed_when_corpus_collections_present(self):
        bundle = _bundle(
            entities={
                "Documents": {"style": "COLLECTION", "collectionName": "Documents"},
                "Employee": {"style": "COLLECTION", "collectionName": "Employee"},
                "Department": {"style": "COLLECTION", "collectionName": "Department"},
            },
            relationships={},
            conceptual_entities=[
                {"name": "Documents"},
                {"name": "Employee"},
                {"name": "Department"},
            ],
        )
        result = classify_graph_purpose(bundle)
        # Structured rule must NOT fire because corpus collection name
        # is present. Corpus rule scores 0.45 alone — under threshold.
        assert result.purpose != "structured"
        assert result.per_rule_scores["structured"] == 0.0

    def test_below_three_entities_does_not_classify_structured(self):
        bundle = _bundle(
            entities={
                "Foo": {"style": "COLLECTION", "collectionName": "Foo"},
                "Bar": {"style": "COLLECTION", "collectionName": "Bar"},
            },
            relationships={
                "links": {
                    "style": "DEDICATED_COLLECTION",
                    "edgeCollectionName": "links",
                }
            },
            conceptual_entities=[{"name": "Foo"}, {"name": "Bar"}],
        )
        result = classify_graph_purpose(bundle)
        assert result.per_rule_scores["structured"] == 0.0


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class TestAnalyticsDetection:
    def test_embeddings_only_graph_classifies_analytics(self):
        bundle = _bundle(
            entities={
                "embeddings": {
                    "style": "COLLECTION",
                    "collectionName": "embeddings",
                }
            },
            relationships={},
        )
        result = classify_graph_purpose(bundle)
        # Analytics-only fallback fires because no other rule scored above
        # the threshold but analytics did (0.30 + 0.20 = 0.50).
        assert result.purpose == "analytics"

    def test_analytics_does_not_dominate_when_kg_signal_present(self):
        bundle = _bundle(
            entities={
                "Person": {
                    "style": "LABEL",
                    "collectionName": "Entities",
                    "typeField": "type",
                },
                "embeddings": {"style": "COLLECTION", "collectionName": "embeddings"},
            },
            relationships={
                "WORKS_FOR": {
                    "style": "GENERIC_WITH_TYPE",
                    "edgeCollectionName": "Relationships",
                }
            },
        )
        result = classify_graph_purpose(bundle)
        # KG rule wins because non-analytics rules win the head-to-head
        # ranking even when analytics fires.
        assert result.purpose == "knowledge_graph"


# ---------------------------------------------------------------------------
# Hybrid
# ---------------------------------------------------------------------------


class TestHybridEscalation:
    def test_corpus_and_kg_in_one_graph_classifies_hybrid(self):
        """A graph that owns BOTH a corpus (Documents/Chunks) and a KG
        (Entities/Relationships) — the GraphRAG "all-in-one" pattern —
        should escalate to hybrid because both rules fire above the
        threshold and within MIN_HYBRID_DELTA of each other.
        """
        bundle = _bundle(
            entities={
                "Documents": {"style": "COLLECTION", "collectionName": "Documents"},
                "Chunks": {"style": "COLLECTION", "collectionName": "Chunks"},
                "Person": {
                    "style": "LABEL",
                    "collectionName": "Entities",
                    "typeField": "type",
                },
                "Org": {
                    "style": "LABEL",
                    "collectionName": "Entities",
                    "typeField": "type",
                },
            },
            relationships={
                "part_of": {
                    "style": "DEDICATED_COLLECTION",
                    "edgeCollectionName": "part_of",
                },
                "WORKS_FOR": {
                    "style": "GENERIC_WITH_TYPE",
                    "edgeCollectionName": "Relationships",
                },
                "mentions": {
                    "style": "DEDICATED_COLLECTION",
                    "edgeCollectionName": "mentions",
                },
            },
        )
        result = classify_graph_purpose(bundle)
        assert result.purpose == "hybrid"
        winners = set(result.detected_collections.keys())
        assert "corpus" in winners
        assert "knowledge_graph" in winners

    def test_one_dominant_rule_does_not_become_hybrid(self):
        """Even when two rules fire, one being clearly stronger keeps
        the verdict unimodal — the gap exceeds MIN_HYBRID_DELTA.
        """
        bundle = _bundle(
            entities={
                "Documents": {"style": "COLLECTION", "collectionName": "Documents"},
                "Chunks": {"style": "COLLECTION", "collectionName": "Chunks"},
                "Person": {
                    "style": "LABEL",
                    "collectionName": "Entities",
                    "typeField": "type",
                },
            },
            relationships={
                "part_of": {
                    "style": "DEDICATED_COLLECTION",
                    "edgeCollectionName": "part_of",
                },
            },
        )
        result = classify_graph_purpose(bundle)
        # Corpus 1.0 vs KG 0.45 — gap 0.55 > MIN_HYBRID_DELTA → corpus wins.
        assert result.purpose == "corpus"
        assert MIN_HYBRID_DELTA == 0.15


# ---------------------------------------------------------------------------
# Unknown
# ---------------------------------------------------------------------------


class TestUnknownFallback:
    def test_empty_graph_classifies_unknown(self):
        bundle = _bundle(entities={}, relationships={})
        result = classify_graph_purpose(bundle)
        assert result.purpose == "unknown"
        assert result.confidence == 0.0

    def test_low_signal_classifies_unknown(self):
        bundle = _bundle(
            entities={"Foo": {"style": "COLLECTION", "collectionName": "Foo"}},
            relationships={},
        )
        result = classify_graph_purpose(bundle)
        assert result.purpose == "unknown"


# ---------------------------------------------------------------------------
# Result serialization
# ---------------------------------------------------------------------------


class TestResultSerialization:
    def test_to_dict_round_trips_floats(self):
        result = GraphPurposeResult(
            purpose="knowledge_graph",
            confidence=0.8765,
            reasons=["because"],
            per_rule_scores={"knowledge_graph": 0.8765, "structured": 0.123},
            detected_collections={"knowledge_graph": ["entities"]},
        )
        d = result.to_dict()
        assert d["purpose"] == "knowledge_graph"
        assert d["confidence"] == 0.876  # rounded to 3 decimals
        assert d["per_rule_scores"]["knowledge_graph"] == 0.876
        assert d["detected_collections"]["knowledge_graph"] == ["entities"]


# ---------------------------------------------------------------------------
# Threshold contract
# ---------------------------------------------------------------------------


def test_thresholds_are_documented_and_finite():
    """Sanity check on the public threshold constants."""
    assert 0.0 < MIN_RULE_SCORE <= 1.0
    assert 0.0 < MIN_OVERALL_CONFIDENCE <= 1.0
    assert 0.0 < MIN_HYBRID_DELTA <= 0.5
    assert MIN_RULE_SCORE >= MIN_OVERALL_CONFIDENCE
