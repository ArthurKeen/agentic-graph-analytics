"""Index creation must actually create indexes.

`add_hash_index` and `add_skiplist_index` were removed in python-arango 8. All
50 call sites survived the major-version upgrade because no test ever asserted
that an index existed -- the methods were called inside one broad try/except
that logged a warning and moved on. On a fresh deployment that meant ZERO
secondary indexes while the log claimed "some" had failed (issue #25).

These tests pin the two things that failed: the driver API actually exists, and
one bad spec cannot take the rest of the batch down with it.
"""

import logging

import pytest

from graph_analytics_ai.arango_index import IndexSpec, ensure_persistent_indexes


class _Collection:
    def __init__(self, fail: bool = False):
        self.calls = []
        self._fail = fail

    def add_index(self, data):
        if self._fail:
            raise RuntimeError("index creation refused")
        self.calls.append(data)
        return data


class _DB:
    def __init__(self, failing=()):
        self._cols = {}
        self._failing = set(failing)

    def collection(self, name):
        if name not in self._cols:
            self._cols[name] = _Collection(fail=name in self._failing)
        return self._cols[name]


def _logger():
    return logging.getLogger("test.arango_index")


def test_the_driver_api_this_module_calls_actually_exists():
    """The regression itself: the method must exist on the installed driver.

    This is what was missing. `add_hash_index` passed review and CI for a whole
    major version because nothing asserted the driver still had it.
    """
    from arango.collection import StandardCollection

    assert hasattr(StandardCollection, "add_index"), (
        "python-arango no longer exposes add_index; arango_index.py must be "
        "updated, and this test is the thing that tells you so"
    )
    # The methods this module exists to replace are gone. If a future driver
    # restores them, that is fine -- but persistent is still the right choice.
    assert not hasattr(StandardCollection, "add_hash_index")
    assert not hasattr(StandardCollection, "add_skiplist_index")


def test_creates_a_persistent_index_per_spec():
    db = _DB()
    specs = [
        IndexSpec("aga_workspaces", ["status"]),
        IndexSpec("aga_epochs", ["name"], unique=True),
    ]

    created, failures = ensure_persistent_indexes(db, specs, logger=_logger())

    assert (created, failures) == (2, [])
    assert db.collection("aga_workspaces").calls == [
        {"type": "persistent", "fields": ["status"], "unique": False}
    ]
    # uniqueness must survive the translation -- it is the only thing enforcing
    # epoch-name uniqueness
    assert db.collection("aga_epochs").calls == [
        {"type": "persistent", "fields": ["name"], "unique": True}
    ]


def test_one_failure_does_not_skip_the_remaining_indexes():
    """The defect's real shape: a single try block lost every later index."""
    db = _DB(failing={"broken"})
    specs = [
        IndexSpec("broken", ["a"]),
        IndexSpec("fine_one", ["b"]),
        IndexSpec("fine_two", ["c"]),
    ]

    created, failures = ensure_persistent_indexes(db, specs, logger=_logger())

    assert created == 2, "indexes after the failing one must still be created"
    assert len(failures) == 1
    assert "broken(a, non-unique)" in failures[0]
    assert db.collection("fine_two").calls, "the last spec must still run"


def test_failures_are_reported_specifically_not_as_some(caplog):
    """The old message said 'some' when none had been created."""
    db = _DB(failing={"broken"})
    with caplog.at_level(logging.WARNING):
        ensure_persistent_indexes(
            db, [IndexSpec("broken", ["a"])], logger=_logger(), context="ctx"
        )

    message = caplog.text
    assert "broken(a, non-unique)" in message, "must name the index that failed"
    assert "RuntimeError" in message, "must name the cause"
    assert "created 0, failed 1" in message, "must report counts, not 'some'"


@pytest.mark.parametrize(
    "storage_module,method",
    [
        ("graph_analytics_ai.product.storage.arangodb", "_create_indexes"),
        ("graph_analytics_ai.catalog.storage.arangodb", "_create_indexes"),
    ],
)
def test_storage_backends_route_through_this_module(storage_module, method):
    """Neither backend may reintroduce a removed driver call."""
    import importlib
    import inspect

    mod = importlib.import_module(storage_module)
    source = inspect.getsource(mod)
    for dead in ("add_hash_index(", "add_skiplist_index(", "add_persistent_index("):
        assert dead not in source, f"{storage_module} still calls {dead}"
    assert "ensure_persistent_indexes(" in source
