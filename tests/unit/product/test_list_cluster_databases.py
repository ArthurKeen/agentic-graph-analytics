"""Unit tests for the two-step-connect database enumeration
(ProductService.list_cluster_databases)."""

import pytest

from graph_analytics_ai.product import MappingSecretResolver, ProductService
from graph_analytics_ai.product.exceptions import ValidationError


class _FakeDB:
    def __init__(self, names):
        self._names = names

    def databases(self):
        return self._names


def _service(db_names=None, raise_on_connect=False):
    calls = {}

    def fake_connector(**kwargs):
        calls.update(kwargs)
        if raise_on_connect:
            raise RuntimeError("auth failed for pw=secret-pw")
        return _FakeDB(db_names or [])

    service = ProductService(
        repository=object(),
        secret_resolver=MappingSecretResolver({"ARANGO_PASSWORD": "secret-pw"}),
        db_connector=fake_connector,
    )
    return service, calls


def test_list_cluster_databases_returns_sorted_non_system():
    service, calls = _service(
        db_names=["_system", "FinReflectKG", "addtech-knowledge-graph"]
    )

    result = service.list_cluster_databases(
        endpoint="https://cluster:8529",
        username="root",
        password_secret_env_var="ARANGO_PASSWORD",
    )

    assert result["endpoint"] == "https://cluster:8529"
    assert result["databases"] == ["FinReflectKG", "addtech-knowledge-graph"]
    # Connects to _system to enumerate, with the resolved password.
    assert calls["database"] == "_system"
    assert calls["password"] == "secret-pw"
    assert calls["username"] == "root"


def test_list_cluster_databases_can_include_system():
    service, _ = _service(db_names=["_system", "FinReflectKG"])
    result = service.list_cluster_databases(
        endpoint="https://cluster:8529",
        username="root",
        password_secret_env_var="ARANGO_PASSWORD",
        include_system=True,
    )
    assert result["databases"] == ["FinReflectKG", "_system"]


@pytest.mark.parametrize(
    "endpoint,username,env",
    [
        ("", "root", "ARANGO_PASSWORD"),
        ("https://cluster:8529", "", "ARANGO_PASSWORD"),
        ("https://cluster:8529", "root", ""),
    ],
)
def test_list_cluster_databases_validates_required_fields(endpoint, username, env):
    service, _ = _service(db_names=["FinReflectKG"])
    with pytest.raises(ValidationError):
        service.list_cluster_databases(
            endpoint=endpoint, username=username, password_secret_env_var=env
        )


def test_list_cluster_databases_masks_secret_on_failure():
    service, _ = _service(raise_on_connect=True)
    with pytest.raises(ValidationError) as excinfo:
        service.list_cluster_databases(
            endpoint="https://cluster:8529",
            username="root",
            password_secret_env_var="ARANGO_PASSWORD",
        )
    # The resolved password must not leak in the error message.
    assert "secret-pw" not in str(excinfo.value)
