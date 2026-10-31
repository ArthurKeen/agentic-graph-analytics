"""The autonomous planner decides what to run, so it is where a model's
output becomes an execution. These tests pin the two things that matter:
a plan is grounded in the real graph, and nothing the model invents reaches
the engine.
"""

import pytest

from graph_analytics_ai.ai.generation.autonomous_plan import (
    SUPPORTED_ALGORITHMS,
    build_planning_prompt,
    plan_use_cases,
    summarize_graph,
)


class _Collection:
    def __init__(self, count):
        self.document_count = count


class _Relationship:
    def __init__(self, name, from_collection, to_collection):
        self.name = name
        self.from_collection = from_collection
        self.to_collection = to_collection


class _Schema:
    database_name = "finreflect"

    def __init__(self, vertices=None, edges=None, relationships=()):
        self.vertex_collections = vertices or {}
        self.edge_collections = edges or {}
        self.relationships = list(relationships)


class _Analysis:
    def __init__(
        self, domain=None, key_entities=(), key_relationships=(), description=""
    ):
        self.domain = domain
        self.key_entities = list(key_entities)
        self.key_relationships = list(key_relationships)
        self.description = description


class _Provider:
    """An LLM stand-in that returns whatever the test hands it."""

    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error
        self.prompts = []

    def generate_structured(self, prompt, schema, **kwargs):
        self.prompts.append(prompt)
        if self._error is not None:
            raise self._error
        return self._response


def _schema():
    return _Schema(
        vertices={"ORG": _Collection(22_000), "Metric": _Collection(3_000_000)},
        edges={"relations": _Collection(17_500_000)},
        relationships=[_Relationship("reports", "ORG", "Metric")],
    )


def test_the_summary_measures_the_graph_rather_than_describing_it():
    """Average degree is the signal that separates a hub graph from a mesh."""

    summary = summarize_graph(_schema(), _Analysis(domain="finance"))

    assert summary["total_vertices"] == 3_022_000
    assert summary["total_edges"] == 17_500_000
    assert summary["average_degree"] == pytest.approx(5.79, abs=0.01)
    assert summary["domain"] == "finance"


def test_the_prompt_names_the_real_collections_and_scale():
    """A planner that cannot see the graph proposes the same thing every time."""

    prompt = build_planning_prompt(summarize_graph(_schema(), _Analysis()), 6)

    assert "ORG" in prompt
    assert "17,500,000" in prompt
    assert "reports" in prompt
    for algorithm in SUPPORTED_ALGORITHMS:
        assert algorithm in prompt, f"{algorithm} must be offered to the planner"


def test_a_planned_use_case_becomes_a_runnable_one():
    provider = _Provider(
        {
            "use_cases": [
                {
                    "title": "Most cited reporting entities",
                    "question": "Which organizations anchor the most metrics?",
                    "algorithm": "pagerank",
                    "rationale": "ORG is 0.7 percent of vertices but most edges.",
                    "report_focus": "Top organizations by weighted inbound links.",
                    "target_entities": ["ORG"],
                    "priority": "high",
                }
            ]
        }
    )

    use_cases = plan_use_cases(_schema(), _Analysis(), provider)

    assert len(use_cases) == 1
    assert use_cases[0].graph_algorithms == ["pagerank"]
    assert use_cases[0].data_needs == ["ORG"]
    assert "anchor the most metrics" in use_cases[0].description


@pytest.mark.parametrize(
    "algorithm",
    ["louvain", "node2vec", "PageRank2", "", "shortest_path"],
    ids=["louvain", "node2vec", "typo", "empty", "unimplemented"],
)
def test_an_algorithm_the_engine_does_not_have_is_dropped(algorithm):
    """The engine exposes five algorithms. A plan naming a sixth fails inside
    an execution, where it reads as a runtime error rather than a bad plan."""

    provider = _Provider(
        {
            "use_cases": [
                {
                    "title": "Invented",
                    "question": "q",
                    "algorithm": algorithm,
                    "rationale": "r",
                    "report_focus": "f",
                },
                {
                    "title": "Real one",
                    "question": "q",
                    "algorithm": "wcc",
                    "rationale": "r",
                    "report_focus": "f",
                },
            ]
        }
    )

    use_cases = plan_use_cases(_schema(), _Analysis(), provider)

    titles = [use_case.title for use_case in use_cases]
    assert "Invented" not in titles, "an unimplemented algorithm must not run"
    assert "Real one" in titles, "one bad entry must not lose the good ones"


def test_no_provider_falls_back_to_the_fixed_bundle():
    use_cases = plan_use_cases(_schema(), _Analysis(), None)

    assert use_cases, "autonomous mode must still produce something to run"
    for use_case in use_cases:
        for algorithm in use_case.graph_algorithms:
            assert algorithm in SUPPORTED_ALGORITHMS


def test_a_provider_failure_falls_back_instead_of_failing_the_run():
    """The fallback is why this can be on by default: the worst case is the
    behaviour that shipped before."""

    provider = _Provider(error=RuntimeError("rate limited"))

    use_cases = plan_use_cases(_schema(), _Analysis(), provider)

    assert use_cases


def test_a_plan_of_only_invalid_entries_falls_back():
    provider = _Provider(
        {"use_cases": [{"title": "x", "algorithm": "louvain", "question": "q"}]}
    )

    use_cases = plan_use_cases(_schema(), _Analysis(), provider)

    assert use_cases, "dropping every entry must not leave the run with nothing"
    for use_case in use_cases:
        for algorithm in use_case.graph_algorithms:
            assert algorithm in SUPPORTED_ALGORITHMS


def test_the_plan_is_capped():
    provider = _Provider(
        {
            "use_cases": [
                {
                    "title": f"Case {index}",
                    "question": "q",
                    "algorithm": "wcc",
                    "rationale": "r",
                    "report_focus": "f",
                }
                for index in range(20)
            ]
        }
    )

    assert len(plan_use_cases(_schema(), _Analysis(), provider, max_use_cases=4)) == 4
