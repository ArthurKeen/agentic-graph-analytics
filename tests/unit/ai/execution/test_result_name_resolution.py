"""Result rows must carry the names of the entities they describe.

GAE returns identifiers only -- {"id": "Node/ab12", "rank": 0.0016} -- so a
report built from raw rows describes a distribution without naming anything in
it. A FinReflectKG PageRank report read "the top-ranked node (0.00157)" when the
top two were `net income` and `revenue`, and the absent names invited invention:
one insight attributed the finding to "multiple GICS sectors", a dimension the
graph does not contain.
"""

from typing import Any, Dict, List

import pytest

from graph_analytics_ai.ai.execution.executor import AnalysisExecutor


class _StubDB:
    """Resolves DOCUMENT(id) for a fixed vertex set."""

    def __init__(self, docs: Dict[str, Dict[str, Any]], fail: bool = False):
        self._docs = docs
        self._fail = fail
        self.aql = self

    def execute(self, query: str, bind_vars: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self._fail:
            raise RuntimeError("AQL unavailable")
        return [
            {"id": i, "doc": self._docs[i]} for i in bind_vars["ids"] if i in self._docs
        ]


DOCS = {
    "Node/a": {"name": "net income", "type": "FIN_METRIC"},
    "Node/b": {"name": "revenue", "type": "FIN_METRIC"},
    "Node/c": {"title": "Acme Corp", "type": "ORG"},  # label under `title`
    "Node/d": {"type": "CONCEPT"},  # typed, unnamed
}


def _executor():
    return AnalysisExecutor.__new__(AnalysisExecutor)


def test_pagerank_rows_gain_entity_names():
    rows = [{"id": "Node/a", "rank": 0.00157}, {"id": "Node/b", "rank": 0.00098}]
    out = _executor()._attach_source_attributes(_StubDB(DOCS), rows)

    assert [r["source_name"] for r in out] == ["net income", "revenue"]
    assert all(r["source_type"] == "FIN_METRIC" for r in out)
    # original fields survive untouched
    assert out[0]["rank"] == 0.00157


def test_component_representative_is_named_too():
    """A component reads as 'anchored on net income', not 'Node/a'."""
    rows = [{"id": "Node/b", "component": "Node/a"}]
    out = _executor()._attach_source_attributes(_StubDB(DOCS), rows)

    assert out[0]["source_name"] == "revenue"
    assert out[0]["component_name"] == "net income"


def test_alternate_label_attribute_is_found():
    rows = [{"id": "Node/c", "rank": 0.5}]
    out = _executor()._attach_source_attributes(_StubDB(DOCS), rows)
    assert out[0]["source_name"] == "Acme Corp"


def test_unnamed_vertex_still_gets_its_type():
    """A vertex with no label contributes type rather than a fabricated name."""
    rows = [{"id": "Node/d", "rank": 0.1}]
    out = _executor()._attach_source_attributes(_StubDB(DOCS), rows)
    assert "source_name" not in out[0]
    assert out[0]["source_type"] == "CONCEPT"


def test_unresolvable_id_is_left_alone():
    rows = [{"id": "Node/missing", "rank": 0.1}]
    out = _executor()._attach_source_attributes(_StubDB(DOCS), rows)
    assert out == rows


@pytest.mark.parametrize("rows", [[], [{"component": 7, "rank": 0.1}]])
def test_nothing_to_resolve_is_a_no_op(rows):
    assert _executor()._attach_source_attributes(_StubDB(DOCS), rows) == rows


def test_resolution_failure_never_loses_results():
    """Losing names degrades a report; losing rows destroys it."""
    rows = [{"id": "Node/a", "rank": 0.00157}]
    out = _executor()._attach_source_attributes(_StubDB(DOCS, fail=True), rows)
    assert out == rows
