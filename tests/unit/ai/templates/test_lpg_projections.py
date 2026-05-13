"""Unit tests for LPG-aware TemplateGenerator (PRD v0.6 / FR-71)."""

from __future__ import annotations

from typing import Any, Dict

import pytest

from graph_analytics_ai.ai.documents.models import Priority
from graph_analytics_ai.ai.generation.use_cases import UseCase, UseCaseType
from graph_analytics_ai.ai.schema.acquire import SchemaAcquisitionBundle
from graph_analytics_ai.ai.schema.models import (
    CollectionSchema,
    CollectionType,
    GraphSchema,
)
from graph_analytics_ai.ai.templates.generator import TemplateGenerator
from graph_analytics_ai.ai.templates.models import (
    AnalysisTemplate,
    LpgProjection,
    TemplateConfig,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _lpg_bundle() -> SchemaAcquisitionBundle:
    """LPG bundle: ``nodes`` collection + ``edges`` collection mixing types."""
    return SchemaAcquisitionBundle(
        schema_kind="lpg",
        conceptual_schema={
            "entities": [
                {"name": "Person", "labels": ["Person"], "properties": []},
                {"name": "Company", "labels": ["Company"], "properties": []},
            ],
            "relationships": [
                {"type": "WORKS_FOR", "fromEntity": "Person", "toEntity": "Company"},
            ],
        },
        physical_mapping={
            "entities": {
                "Person": {
                    "style": "LABEL",
                    "collectionName": "nodes",
                    "typeField": "type",
                    "typeValue": "Person",
                },
                "Company": {
                    "style": "LABEL",
                    "collectionName": "nodes",
                    "typeField": "type",
                    "typeValue": "Company",
                },
            },
            "relationships": {
                "WORKS_FOR": {
                    "style": "GENERIC_WITH_TYPE",
                    "edgeCollectionName": "edges",
                    "typeField": "relType",
                    "typeValue": "WORKS_FOR",
                    "fromEntity": "Person",
                    "toEntity": "Company",
                },
                "KNOWS": {
                    "style": "GENERIC_WITH_TYPE",
                    "edgeCollectionName": "edges",
                    "typeField": "relType",
                    "typeValue": "KNOWS",
                    "fromEntity": "Person",
                    "toEntity": "Person",
                },
            },
        },
        analyzer_metadata={"source": "heuristic"},
        shape_fingerprint="shape",
        full_fingerprint="full",
        database="hr",
        graph_name="hr_graph",
    )


def _pg_bundle() -> SchemaAcquisitionBundle:
    """PG bundle: dedicated collection per type."""
    return SchemaAcquisitionBundle(
        schema_kind="pg",
        conceptual_schema={
            "entities": [
                {"name": "users", "labels": ["users"], "properties": []},
            ],
            "relationships": [],
        },
        physical_mapping={
            "entities": {
                "users": {"style": "COLLECTION", "collectionName": "users"},
            },
            "relationships": {
                "follows": {
                    "style": "DEDICATED_COLLECTION",
                    "edgeCollectionName": "follows",
                    "fromEntity": "Any",
                    "toEntity": "Any",
                },
            },
        },
        analyzer_metadata={"source": "heuristic"},
        shape_fingerprint="shape",
        full_fingerprint="full",
        database="db",
        graph_name="g",
    )


def _hybrid_bundle() -> SchemaAcquisitionBundle:
    """Hybrid: PG nodes (Org collection) + LPG edges (relations collection)."""
    return SchemaAcquisitionBundle(
        schema_kind="hybrid",
        conceptual_schema={"entities": [], "relationships": []},
        physical_mapping={
            "entities": {
                "Org": {"style": "COLLECTION", "collectionName": "Org"},
            },
            "relationships": {
                "EMPLOYED_BY": {
                    "style": "GENERIC_WITH_TYPE",
                    "edgeCollectionName": "relations",
                    "typeField": "relType",
                    "typeValue": "EMPLOYED_BY",
                    "fromEntity": "Any",
                    "toEntity": "Any",
                },
            },
        },
        analyzer_metadata={"source": "heuristic"},
        shape_fingerprint="shape",
        full_fingerprint="full",
        database="db",
        graph_name="g",
    )


def _use_case_for_nodes_edges() -> UseCase:
    return UseCase(
        id="UC-LPG-001",
        title="Influence In HR Graph",
        description="Find central employees",
        use_case_type=UseCaseType.CENTRALITY,
        priority=Priority.HIGH,
        related_requirements=[],
        graph_algorithms=["pagerank"],
        data_needs=["nodes", "edges"],
    )


def _lpg_schema() -> GraphSchema:
    """Schema where the only collections are the generic ``nodes`` / ``edges``."""
    return GraphSchema(
        database_name="hr",
        vertex_collections={
            "nodes": CollectionSchema(
                name="nodes", type=CollectionType.DOCUMENT, document_count=10000
            )
        },
        edge_collections={
            "edges": CollectionSchema(
                name="edges", type=CollectionType.EDGE, document_count=50000
            )
        },
    )


# ---------------------------------------------------------------------------
# _plan_lpg_projections — pure helper
# ---------------------------------------------------------------------------


class TestPlanLpgProjections:
    def test_no_bundle_returns_empty(self) -> None:
        gen = TemplateGenerator(graph_name="g")
        kind, plans = gen._plan_lpg_projections(
            schema_bundle=None,
            vertex_collections=["nodes"],
            edge_collections=["edges"],
        )
        assert kind is None
        assert plans == []

    def test_pg_bundle_returns_no_projections(self) -> None:
        gen = TemplateGenerator(graph_name="g")
        kind, plans = gen._plan_lpg_projections(
            schema_bundle=_pg_bundle(),
            vertex_collections=["users"],
            edge_collections=["follows"],
        )
        assert kind == "pg"
        assert plans == []

    def test_lpg_bundle_emits_one_projection_per_type(self) -> None:
        gen = TemplateGenerator(graph_name="g")
        kind, plans = gen._plan_lpg_projections(
            schema_bundle=_lpg_bundle(),
            vertex_collections=["nodes"],
            edge_collections=["edges"],
        )
        assert kind == "lpg"
        # 2 entity types (Person, Company) + 2 edge types (WORKS_FOR, KNOWS)
        assert len(plans) == 4
        assert all(isinstance(p, LpgProjection) for p in plans)

    def test_node_projection_carries_type_and_target(self) -> None:
        gen = TemplateGenerator(graph_name="g")
        _, plans = gen._plan_lpg_projections(
            schema_bundle=_lpg_bundle(),
            vertex_collections=["nodes"],
            edge_collections=["edges"],
        )
        person = next(p for p in plans if p.logical_type == "Person")
        assert person.kind == "node"
        assert person.source_collection == "nodes"
        assert person.discriminator_field == "type"
        assert person.discriminator_value == "Person"
        assert person.materialization_collection.startswith("_proj_nodes_type_Person")
        assert "FILTER doc.`type` == @value" in person.materialization_aql
        assert "UPSERT" in person.materialization_aql

    def test_edge_projection_preserves_from_and_to(self) -> None:
        gen = TemplateGenerator(graph_name="g")
        _, plans = gen._plan_lpg_projections(
            schema_bundle=_lpg_bundle(),
            vertex_collections=["nodes"],
            edge_collections=["edges"],
        )
        works_for = next(p for p in plans if p.logical_type == "WORKS_FOR")
        assert works_for.kind == "edge"
        assert works_for.source_collection == "edges"
        assert "_from: doc._from" in works_for.materialization_aql
        assert "_to: doc._to" in works_for.materialization_aql

    def test_projections_filtered_to_requested_collections(self) -> None:
        gen = TemplateGenerator(graph_name="g")
        # Caller asks only for vertex 'nodes' and a non-matching edge
        # collection: edges in the bundle live on 'edges', so they must
        # be filtered out of the plan.
        kind, plans = gen._plan_lpg_projections(
            schema_bundle=_lpg_bundle(),
            vertex_collections=["nodes"],
            edge_collections=["unrelated_edges"],
        )
        assert kind == "lpg"
        assert all(p.kind == "node" for p in plans)
        assert {p.logical_type for p in plans} == {"Person", "Company"}

    def test_empty_collection_lists_are_no_filter(self) -> None:
        # Empty lists follow legacy generator semantics: "no filter,
        # use everything available in the bundle".
        gen = TemplateGenerator(graph_name="g")
        kind, plans = gen._plan_lpg_projections(
            schema_bundle=_lpg_bundle(),
            vertex_collections=[],
            edge_collections=[],
        )
        assert kind == "lpg"
        assert len(plans) == 4

    def test_hybrid_bundle_emits_only_generic_edge_projections(self) -> None:
        gen = TemplateGenerator(graph_name="g")
        kind, plans = gen._plan_lpg_projections(
            schema_bundle=_hybrid_bundle(),
            vertex_collections=["Org"],
            edge_collections=["relations"],
        )
        assert kind == "hybrid"
        # Org is COLLECTION (no projection); EMPLOYED_BY is GENERIC_WITH_TYPE.
        assert len(plans) == 1
        plan = plans[0]
        assert plan.logical_type == "EMPLOYED_BY"
        assert plan.kind == "edge"

    def test_collection_name_sanitizes_special_characters(self) -> None:
        name = TemplateGenerator._projection_collection_name(
            "weird-coll", "rel.type", "Has Children"
        )
        # No hyphens, dots, or spaces survive.
        assert "-" not in name
        assert "." not in name
        assert " " not in name
        assert name.startswith("_proj_")

    def test_collection_name_is_truncated_to_64_chars(self) -> None:
        name = TemplateGenerator._projection_collection_name(
            "a" * 200, "f", "v"
        )
        assert len(name) <= 64


# ---------------------------------------------------------------------------
# generate_templates — end-to-end with bundle wiring
# ---------------------------------------------------------------------------


class TestGenerateTemplatesWithBundle:
    def test_lpg_bundle_attaches_projections_to_template_config(self) -> None:
        gen = TemplateGenerator(graph_name="hr_graph")
        templates = gen.generate_templates(
            use_cases=[_use_case_for_nodes_edges()],
            schema=_lpg_schema(),
            schema_bundle=_lpg_bundle(),
        )
        assert len(templates) == 1
        template = templates[0]
        assert isinstance(template, AnalysisTemplate)
        assert template.config.schema_kind == "lpg"
        assert len(template.config.lpg_projections) > 0

    def test_lpg_bundle_marks_template_metadata(self) -> None:
        gen = TemplateGenerator(graph_name="hr_graph")
        templates = gen.generate_templates(
            use_cases=[_use_case_for_nodes_edges()],
            schema=_lpg_schema(),
            schema_bundle=_lpg_bundle(),
        )
        meta = templates[0].metadata
        assert meta.get("schema_kind") == "lpg"
        assert meta.get("requires_typed_projection") is True
        assert isinstance(meta.get("lpg_projection_count"), int)
        assert meta["lpg_projection_count"] > 0

    def test_pg_bundle_yields_no_projections(self) -> None:
        gen = TemplateGenerator(graph_name="g")
        templates = gen.generate_templates(
            use_cases=[
                UseCase(
                    id="UC-PG-1",
                    title="Find users",
                    description="Find central users",
                    use_case_type=UseCaseType.CENTRALITY,
                    priority=Priority.HIGH,
                    related_requirements=[],
                    graph_algorithms=["pagerank"],
                    data_needs=["users"],
                )
            ],
            schema=GraphSchema(
                database_name="db",
                vertex_collections={
                    "users": CollectionSchema(
                        name="users",
                        type=CollectionType.DOCUMENT,
                        document_count=100,
                    )
                },
                edge_collections={
                    "follows": CollectionSchema(
                        name="follows",
                        type=CollectionType.EDGE,
                        document_count=200,
                    )
                },
            ),
            schema_bundle=_pg_bundle(),
        )
        template = templates[0]
        assert template.config.schema_kind == "pg"
        assert template.config.lpg_projections == []
        assert "requires_typed_projection" not in template.metadata

    def test_no_bundle_keeps_legacy_behavior(
        self, simple_use_case: UseCase, simple_schema: GraphSchema
    ) -> None:
        gen = TemplateGenerator(graph_name="g")
        templates = gen.generate_templates(
            use_cases=[simple_use_case],
            schema=simple_schema,
        )
        # No bundle → schema_kind is None and no projections emitted.
        assert templates[0].config.schema_kind is None
        assert templates[0].config.lpg_projections == []


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_lpg_projection_round_trip(self) -> None:
        plan = LpgProjection(
            logical_type="Person",
            source_collection="nodes",
            discriminator_field="type",
            discriminator_value="Person",
            kind="node",
            materialization_collection="_proj_nodes_type_Person",
            materialization_aql="FOR doc IN nodes FILTER ...",
        )
        as_dict = plan.to_dict()
        for key in (
            "logical_type",
            "source_collection",
            "discriminator_field",
            "discriminator_value",
            "kind",
            "materialization_collection",
            "materialization_aql",
        ):
            assert key in as_dict

    def test_template_config_to_dict_includes_lpg_fields(self) -> None:
        config = TemplateConfig(
            graph_name="g",
            vertex_collections=["nodes"],
            edge_collections=["edges"],
            schema_kind="lpg",
            lpg_projections=[
                LpgProjection(
                    logical_type="Person",
                    source_collection="nodes",
                    discriminator_field="type",
                    discriminator_value="Person",
                )
            ],
        )
        as_dict = config.to_dict()
        assert as_dict["schema_kind"] == "lpg"
        assert "lpg_projections" in as_dict
        assert len(as_dict["lpg_projections"]) == 1

    def test_template_config_to_dict_omits_lpg_keys_when_unset(self) -> None:
        config = TemplateConfig(graph_name="g")
        as_dict = config.to_dict()
        assert "schema_kind" not in as_dict
        assert "lpg_projections" not in as_dict

    def test_to_analysis_config_passes_through_lpg(self) -> None:
        from graph_analytics_ai.ai.templates.models import (
            AlgorithmParameters,
            AlgorithmType,
        )

        template = AnalysisTemplate(
            name="t",
            description="d",
            algorithm=AlgorithmParameters(algorithm=AlgorithmType.PAGERANK),
            config=TemplateConfig(
                graph_name="g",
                vertex_collections=["nodes"],
                edge_collections=["edges"],
                schema_kind="lpg",
                lpg_projections=[
                    LpgProjection(
                        logical_type="Person",
                        source_collection="nodes",
                        discriminator_field="type",
                        discriminator_value="Person",
                    )
                ],
            ),
        )
        cfg = template.to_analysis_config()
        assert cfg["schema_kind"] == "lpg"
        assert "lpg_projections" in cfg
