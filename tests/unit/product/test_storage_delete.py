"""`delete_document_by_key` must tell "already gone" apart from "it broke".

The FR-54 retention sweep reads a False return as "nothing to delete" and
counts it as a clean skip. The helper used to catch every exception and return
False, so an unreachable server, a dropped collection or a permission change
produced removed=0, an audit event claiming a successful sweep, and an advanced
last_applied_at -- after which the expired records were never revisited.
"""

import pytest

from graph_analytics_ai.product.exceptions import StorageError
from graph_analytics_ai.product.storage.arangodb import ProductArangoStorage


class _Collection:
    def __init__(self, error=None, missing=False):
        self._error = error
        self._missing = missing
        self.deleted = []

    def delete(self, key, ignore_missing=False):
        if self._error is not None:
            raise self._error
        if self._missing:
            if not ignore_missing:
                raise RuntimeError("document not found")
            return False
        self.deleted.append(key)
        return {"_key": key}


class _DB:
    def __init__(self, collection):
        self._collection = collection

    def collection(self, name):
        return self._collection


def _storage(collection):
    return ProductArangoStorage(_DB(collection), auto_initialize=False)


def test_deleting_a_present_document_reports_a_deletion():
    collection = _Collection()

    assert _storage(collection).delete_document_by_key("aga_documents", "d1") is True
    assert collection.deleted == ["d1"]


def test_an_already_absent_document_is_not_an_error():
    """The one case the sweep is entitled to shrug at."""

    assert (
        _storage(_Collection(missing=True)).delete_document_by_key(
            "aga_documents", "gone"
        )
        is False
    )


@pytest.mark.parametrize(
    "error",
    [
        ConnectionError("[Errno 8] nodename nor servname provided"),
        RuntimeError("collection or view not found"),
        PermissionError("insufficient rights to execute this request"),
    ],
    ids=["unreachable", "missing-collection", "forbidden"],
)
def test_a_real_failure_is_raised_not_reported_as_already_gone(error):
    """The regression: any of these used to return False, i.e. "clean skip"."""

    with pytest.raises(StorageError) as raised:
        _storage(_Collection(error=error)).delete_document_by_key("aga_documents", "d1")

    assert "aga_documents" in str(raised.value)
    assert raised.value.__cause__ is error
