"""Unit tests for product API CLI."""

import sys
import types

from click.testing import CliRunner

from graph_analytics_ai.product import cli as product_cli


def test_product_cli_serve_runs_uvicorn(monkeypatch):
    """Product CLI starts uvicorn with the generated FastAPI app."""

    calls = {}
    fake_uvicorn = types.ModuleType("uvicorn")

    def run(app, **kwargs):
        calls["app"] = app
        calls["kwargs"] = kwargs

    fake_uvicorn.run = run
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)
    monkeypatch.setattr(
        product_cli,
        "create_product_fastapi_app",
        lambda: "app",
    )

    result = CliRunner().invoke(
        product_cli.cli,
        ["serve", "--host", "0.0.0.0", "--port", "9000", "--reload"],
    )

    assert result.exit_code == 0
    assert calls["app"] == "app"
    assert calls["kwargs"] == {
        "host": "0.0.0.0",
        "port": 9000,
        "reload": True,
        "log_level": "info",
    }


def test_product_cli_serve_explains_missing_api_extra(monkeypatch):
    """Product CLI gives a clear error when uvicorn is unavailable."""

    monkeypatch.delitem(sys.modules, "uvicorn", raising=False)

    class MissingUvicornBlocker:
        def find_spec(self, fullname, path=None, target=None):
            if fullname == "uvicorn":
                raise ImportError("blocked uvicorn import")
            return None

    monkeypatch.setattr(sys, "meta_path", [MissingUvicornBlocker()])

    result = CliRunner().invoke(product_cli.cli, ["serve"])

    assert result.exit_code != 0
    assert "graph-analytics-ai[api]" in result.output
