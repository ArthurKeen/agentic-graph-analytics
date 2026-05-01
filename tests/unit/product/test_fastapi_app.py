"""Unit tests for the optional FastAPI product adapter."""

import asyncio
import sys
import types

import pytest

from graph_analytics_ai.product.api import PRODUCT_API_ENDPOINTS
from graph_analytics_ai.product.fastapi_app import create_product_fastapi_app


class FakeFastAPI:
    def __init__(self, title, version):
        self.title = title
        self.version = version
        self.routes = []

    def add_api_route(self, path, endpoint, methods, summary, tags):
        self.routes.append(
            {
                "path": path,
                "endpoint": endpoint,
                "methods": methods,
                "summary": summary,
                "tags": tags,
            }
        )


class FakeRequest:
    def __init__(self, method, path_params=None, query_params=None, body=None):
        self.method = method
        self.path_params = path_params or {}
        self.query_params = query_params or {}
        self.body = body or {}

    async def json(self):
        return self.body


@pytest.fixture
def fake_fastapi_module(monkeypatch):
    module = types.ModuleType("fastapi")
    module.FastAPI = FakeFastAPI
    module.Request = FakeRequest
    monkeypatch.setitem(sys.modules, "fastapi", module)
    return module


def test_create_product_fastapi_app_registers_contract_routes(fake_fastapi_module):
    """FastAPI adapter registers every product API contract endpoint."""

    app = create_product_fastapi_app(service=object(), title="Product API", version="1")

    route_keys = {
        (route["methods"][0], route["path"])
        for route in app.routes
    }
    contract_keys = {
        (endpoint.method, endpoint.path)
        for endpoint in PRODUCT_API_ENDPOINTS
    }

    assert app.title == "Product API"
    assert app.version == "1"
    assert route_keys == contract_keys


def test_create_product_fastapi_app_can_bootstrap_default_service(fake_fastapi_module):
    """FastAPI adapter can build the product service from a database connector."""

    database = object()
    app = create_product_fastapi_app(
        db_connector=lambda: database,
        auto_initialize=False,
    )

    assert app.routes


def test_product_fastapi_route_dispatches_request(fake_fastapi_module):
    """Generated route handler delegates to the service dispatcher."""

    class Service:
        def get_workspace_overview(self, workspace_id, recent_limit):
            return {
                "workspace_id": workspace_id,
                "recent_limit": recent_limit,
            }

    app = create_product_fastapi_app(service=Service())
    route = next(
        route
        for route in app.routes
        if route["path"] == "/api/workspaces/{workspace_id}/overview"
    )
    request = FakeRequest(
        method="GET",
        path_params={"workspace_id": "workspace-1"},
        query_params={"recent_limit": "3"},
    )

    response = asyncio.run(route["endpoint"](request))

    assert response == {"workspace_id": "workspace-1", "recent_limit": "3"}


def test_create_product_fastapi_app_explains_missing_dependency(monkeypatch):
    """FastAPI adapter gives a clear message when the optional extra is absent."""

    monkeypatch.delitem(sys.modules, "fastapi", raising=False)

    class MissingFastAPIBlocker:
        def find_spec(self, fullname, path=None, target=None):
            if fullname == "fastapi":
                raise ImportError("blocked fastapi import")
            return None

    blocker = MissingFastAPIBlocker()
    monkeypatch.setattr(sys, "meta_path", [blocker])

    with pytest.raises(ImportError, match="graph-analytics-ai\\[api\\]"):
        create_product_fastapi_app(service=object())
