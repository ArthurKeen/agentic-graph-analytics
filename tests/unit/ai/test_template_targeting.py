"""A use case's stated collections must reach the template (FR-75).

The autonomous planner chooses which entity types an analysis is about, and
until this was wired the choice was discarded: ``CollectionSelector``
overrode it on every path, and the one branch taking ``use_case_context``
(``_select_custom``) ignores the argument and is unreachable for all five
supported algorithms anyway. Two use cases differing only in their targets
produced byte-identical configs, so a report scoped to one collection was
answered from the whole graph.
"""

import io
from contextlib import redirect_stdout

import pytest

from graph_analytics_ai.ai.documents.models import Priority
from graph_analytics_ai.ai.generation.use_cases import UseCase, UseCaseType
from graph_analytics_ai.ai.schema.models import (
    CollectionSchema,
    CollectionType,
    GraphSchema,
)
from graph_analytics_ai.ai.templates.generator import TemplateGenerator


def _collection(name, count, *, edge=False, sources=(), targets=()):
    return CollectionSchema(
        name=name,
        type=CollectionType.EDGE if edge else CollectionType.VERTEX,
        document_count=count,
        from_collections=set(sources),
        to_collections=set(targets),
    )


@pytest.fixture
def schema():
    """A graph that is deliberately not the AdTech demo.

    ``_extract_collections`` matches literal AdTech names (Device, IP,
    Site...), so any other schema exercises the real path rather than the
    one branch that happens to be hardcoded.
    """

    return GraphSchema(
        database_name="research",
        vertex_collections={
            "Author": _collection("Author", 5_000),
            "Paper": _collection("Paper", 40_000),
            "Venue": _collection("Venue", 300),
        },
        edge_collections={
            "WROTE": _collection(
                "WROTE", 90_000, edge=True, sources=["Author"], targets=["Paper"]
            ),
            "CITES": _collection(
                "CITES", 600_000, edge=True, sources=["Paper"], targets=["Paper"]
            ),
            "PUBLISHED_IN": _collection(
                "PUBLISHED_IN",
                40_000,
                edge=True,
                sources=["Paper"],
                targets=["Venue"],
            ),
        },
    )


def _use_case(uid, data_needs, algorithm="pagerank"):
    return UseCase(
        id=uid,
        title=f"{uid} study",
        description="influence",
        use_case_type=UseCaseType.CENTRALITY,
        priority=Priority.HIGH,
        graph_algorithms=[algorithm],
        data_needs=data_needs,
        expected_outputs=["ranking"],
        success_metrics=[],
    )


def _templates(use_cases, schema):
    generator = TemplateGenerator(graph_name="research")
    # The generator narrates itself to stdout at some length.
    with redirect_stdout(io.StringIO()):
        return generator.generate_templates(use_cases, schema=schema)


def test_two_use_cases_with_different_targets_get_different_collections(schema):
    """The regression. Same algorithm, different targets, same graph."""

    authors = _use_case("UC-A01", ["Author", "WROTE"])
    venues = _use_case("UC-A02", ["Venue", "PUBLISHED_IN"])

    first, second = _templates([authors, venues], schema)

    assert first.config.vertex_collections == ["Author"]
    assert first.config.edge_collections == ["WROTE"]
    assert second.config.vertex_collections == ["Venue"]
    assert second.config.edge_collections == ["PUBLISHED_IN"]


def test_a_target_the_graph_does_not_have_narrows_nothing(schema):
    """An invented collection is dropped, not obeyed and not fatal.

    Same treatment an unimplemented algorithm gets in the planner: a plan
    naming something the graph lacks should fall back to the default
    selection rather than fail inside an execution.
    """

    invented = _use_case("UC-A03", ["Customer", "PURCHASED"])

    (template,) = _templates([invented], schema)

    assert set(template.config.vertex_collections) == {"Author", "Paper", "Venue"}


def test_the_fixed_bundle_s_comma_packed_data_needs_resolve(schema):
    """``generate_discovery_use_cases`` packs several names into one entry.

    Its edge line is labelled ``"Edges: A, B"``, and the label is not a
    collection name.
    """

    packed = _use_case("UC-D01", ["Author, Paper", "Edges: WROTE, CITES"])

    (template,) = _templates([packed], schema)

    assert template.config.vertex_collections == ["Author", "Paper"]
    assert template.config.edge_collections == ["WROTE", "CITES"]


def test_naming_only_entities_keeps_edges_that_stay_inside_them(schema):
    """An edge leaving the chosen set would restore what was excluded.

    Naming Author and Paper admits WROTE and CITES; PUBLISHED_IN ends at
    Venue, which this use case did not ask for.
    """

    entities_only = _use_case("UC-A04", ["Author", "Paper"])

    (template,) = _templates([entities_only], schema)

    assert template.config.vertex_collections == ["Author", "Paper"]
    assert set(template.config.edge_collections) == {"WROTE", "CITES"}


def test_an_unscoped_use_case_is_left_alone(schema):
    """Prose that names no collection must not narrow anything."""

    prose = _use_case("UC-A05", ["whatever is most connected"])

    (template,) = _templates([prose], schema)

    assert set(template.config.vertex_collections) == {"Author", "Paper", "Venue"}
