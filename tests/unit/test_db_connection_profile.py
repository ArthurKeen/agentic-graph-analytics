"""Tests for explicit ArangoDB connection helper."""

import pytest

from graph_analytics_ai.db_connection import connect_arango_database


class FakeDatabase:
    """Small fake python-arango database handle."""

    def __init__(self, name, databases=None, version_error=None, databases_error=None):
        self.name = name
        self._databases = databases or ["customer_graph"]
        self._version_error = version_error
        self._databases_error = databases_error

    def version(self):
        """Return version or raise configured error."""

        if self._version_error:
            raise self._version_error
        return "3.12.0"

    def databases(self):
        """Return databases or raise configured error."""

        if self._databases_error:
            raise self._databases_error
        return self._databases


class FakeClient:
    """Fake ArangoClient compatible with connect_arango_database."""

    calls = []
    sys_db = FakeDatabase("_system")

    def __init__(self, hosts):
        self.hosts = hosts

    def db(self, name, username, password, verify=True):
        """Record connection arguments and return a fake database."""

        self.calls.append(
            {
                "name": name,
                "username": username,
                "password": password,
                "verify": verify,
            }
        )
        if name == "_system":
            return self.sys_db
        return FakeDatabase(name)


def test_connect_arango_database_uses_explicit_descriptor():
    """Explicit descriptors connect without reading global environment."""

    FakeClient.calls = []
    FakeClient.sys_db = FakeDatabase("_system", databases=["customer_graph"])

    db = connect_arango_database(
        endpoint="https://example.com:8529",
        username="svc-user",
        password="resolved-secret",
        database="customer_graph",
        verify_ssl="false",
        client_factory=FakeClient,
    )

    assert db.name == "customer_graph"
    assert FakeClient.calls[0]["name"] == "_system"
    assert FakeClient.calls[0]["verify"] is False
    assert FakeClient.calls[1]["name"] == "customer_graph"


def test_connect_arango_database_can_skip_system_verification():
    """Limited users can connect directly to the target database."""

    FakeClient.calls = []

    db = connect_arango_database(
        endpoint="https://example.com:8529",
        username="limited-user",
        password="resolved-secret",
        database="customer_graph",
        verify_ssl=True,
        verify_system=False,
        client_factory=FakeClient,
    )

    assert db.name == "customer_graph"
    assert [call["name"] for call in FakeClient.calls] == ["customer_graph"]


def test_connect_arango_database_masks_password_in_errors():
    """Connection errors should not expose resolved secret values."""

    FakeClient.calls = []
    FakeClient.sys_db = FakeDatabase(
        "_system",
        version_error=Exception("bad password resolved-secret"),
    )

    with pytest.raises(ConnectionError) as exc_info:
        connect_arango_database(
            endpoint="https://example.com:8529",
            username="svc-user",
            password="resolved-secret",
            database="customer_graph",
            client_factory=FakeClient,
        )

    assert "resolved-secret" not in str(exc_info.value)
    assert "***MASKED***" in str(exc_info.value)

