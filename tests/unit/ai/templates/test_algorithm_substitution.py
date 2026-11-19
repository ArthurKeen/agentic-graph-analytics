"""FR-18a: a template may not store a planned algorithm that contradicts the
one it will run.

``UseCaseGenerator._use_case_from_suggestion`` copies the schema analyzer's
free-form ``suggestion["type"]`` into ``graph_algorithms`` unchecked, so a use
case can name something the engine has no implementation of. Selection then
falls back to the use-case-type mapping and a different algorithm runs. The
template used to keep both values and say nothing.
"""

import logging

from graph_analytics_ai.ai.generation.use_cases import Priority, UseCase, UseCaseType
from graph_analytics_ai.ai.schema.models import (
    CollectionSchema,
    CollectionType,
    GraphSchema,
)
from graph_analytics_ai.ai.templates.generator import (
    TemplateGenerator,
    resolve_algorithm_name,
)
from graph_analytics_ai.ai.templates.models import AlgorithmType


def _schema() -> GraphSchema:
    return GraphSchema(
        database_name="demo",
        vertex_collections={
            "Person": CollectionSchema(
                name="Person", type=CollectionType.VERTEX, document_count=100
            )
        },
        edge_collections={
            "KNOWS": CollectionSchema(
                name="KNOWS",
                type=CollectionType.EDGE,
                document_count=500,
                from_collections=["Person"],
                to_collections=["Person"],
            )
        },
    )


def _use_case(algorithms, use_case_type=UseCaseType.COMMUNITY) -> UseCase:
    return UseCase(
        id="UC-S01",
        title="Household resolution",
        description="Group accounts into households.",
        use_case_type=use_case_type,
        priority=Priority.MEDIUM,
        graph_algorithms=list(algorithms),
        data_needs=["Person"],
    )


def _template(use_case):
    return TemplateGenerator(graph_name="demo").generate_templates(
        [use_case], _schema()
    )[0]


def test_an_unrunnable_planned_algorithm_is_recorded_as_a_substitution():
    template = _template(_use_case(["centrality"]))

    assert template.algorithm.algorithm is AlgorithmType.WCC
    assert template.metadata["algorithm_substituted_from"] == ["centrality"]
    reason = template.metadata["algorithm_substitution_reason"]
    assert "centrality" in reason
    assert "wcc" in reason


def test_a_junk_name_beside_a_runnable_one_is_still_flagged():
    """The gap the first version of this check had.

    ``graph_algorithms`` is a list. If any entry resolved to the chosen
    algorithm the whole list passed, so a template could still store
    "centrality" — a name that is neither what ran nor an algorithm the
    engine has — and say nothing.
    """

    template = _template(_use_case(["centrality", "wcc"]))

    assert template.algorithm.algorithm is AlgorithmType.WCC
    assert template.metadata["algorithm_substituted_from"] == ["centrality", "wcc"]
    assert template.metadata["algorithm_unrunnable_names"] == ["centrality"]


def test_order_does_not_decide_whether_a_junk_name_is_flagged():
    template = _template(_use_case(["wcc", "centrality"]))

    assert template.metadata["algorithm_unrunnable_names"] == ["centrality"]


def test_the_reason_separates_substitution_from_an_unrunnable_name():
    """They are different facts and a list can carry both."""

    reason = _template(_use_case(["centrality"])).metadata[
        "algorithm_substitution_reason"
    ]

    assert "name no algorithm the engine implements" in reason
    assert "Running wcc" in reason


def test_a_planned_algorithm_the_engine_has_is_not_flagged():
    template = _template(_use_case(["wcc"]))

    assert template.algorithm.algorithm is AlgorithmType.WCC
    assert "algorithm_substituted_from" not in template.metadata


def test_an_alias_counts_as_agreement():
    """`page-rank` resolves to pagerank, so nothing was substituted."""

    template = _template(_use_case(["page-rank"], UseCaseType.CENTRALITY))

    assert template.algorithm.algorithm is AlgorithmType.PAGERANK
    assert "algorithm_substituted_from" not in template.metadata


def test_a_use_case_naming_no_algorithm_is_not_a_substitution():
    """Nothing was planned, so nothing was overridden."""

    template = _template(_use_case([]))

    assert "algorithm_substituted_from" not in template.metadata


def test_the_substitution_is_logged_as_a_warning(caplog):
    with caplog.at_level(
        logging.WARNING, logger="graph_analytics_ai.ai.templates.generator"
    ):
        _template(_use_case(["centrality"]))

    assert any(
        "runs wcc; planned ['centrality']" in r.getMessage().lower()
        for r in caplog.records
    )


def test_the_resolver_is_the_one_selection_uses():
    """The check and the selection must agree on what counts as a match."""

    assert resolve_algorithm_name("page-rank") is AlgorithmType.PAGERANK
    assert resolve_algorithm_name("betweeness") is AlgorithmType.BETWEENNESS_CENTRALITY
    assert resolve_algorithm_name("centrality") is None
    assert resolve_algorithm_name("") is None
