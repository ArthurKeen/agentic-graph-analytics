"""Unit tests for ProductService.get_connection_defaults.

The connection form prefills from the deployment environment. These tests
pin the contract: non-secret fields come through, deployment mode is
normalised, unset variables degrade to empty strings, and the password
value is NEVER returned (only the env-var name is referenced).
"""

from graph_analytics_ai.product import MappingSecretResolver, ProductService


def _service():
    return ProductService(
        repository=object(),
        secret_resolver=MappingSecretResolver({"ARANGO_PASSWORD": "secret-pw"}),
        db_connector=lambda **_: None,
    )


def test_get_connection_defaults_reads_env(monkeypatch):
    monkeypatch.setenv("ARANGO_ENDPOINT", "https://cluster:8529")
    monkeypatch.setenv("ARANGO_USER", "root")
    monkeypatch.setenv("ARANGO_DATABASE", "FinReflectKG")
    monkeypatch.setenv("ARANGO_VERIFY_SSL", "true")
    monkeypatch.setenv("GAE_DEPLOYMENT_MODE", "self_managed")

    result = _service().get_connection_defaults()

    assert result["endpoint"] == "https://cluster:8529"
    assert result["username"] == "root"
    assert result["database"] == "FinReflectKG"
    assert result["verify_ssl"] is True
    assert result["deployment_mode"] == "self_managed"
    # Only the env-var *name* — never the password value.
    assert result["password_secret_env_var"] == "ARANGO_PASSWORD"
    assert "secret-pw" not in str(result)


def test_get_connection_defaults_maps_amp_aliases(monkeypatch):
    monkeypatch.setenv("GAE_DEPLOYMENT_MODE", "arangograph")
    assert _service().get_connection_defaults()["deployment_mode"] == "amp"


def test_get_connection_defaults_defaults_when_unset(monkeypatch):
    for var in (
        "ARANGO_ENDPOINT",
        "ARANGO_DATABASE",
        "ARANGO_VERIFY_SSL",
        "GAE_DEPLOYMENT_MODE",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("ARANGO_USER", raising=False)

    result = _service().get_connection_defaults()

    assert result["endpoint"] == ""
    assert result["database"] == ""
    # No mode configured -> empty so the form keeps its own default.
    assert result["deployment_mode"] == ""
    # Username falls back to the conventional root.
    assert result["username"] == "root"
    # Verify defaults to True (safe) when unset.
    assert result["verify_ssl"] is True


def test_get_connection_defaults_respects_verify_ssl_false(monkeypatch):
    monkeypatch.setenv("ARANGO_VERIFY_SSL", "false")
    assert _service().get_connection_defaults()["verify_ssl"] is False
