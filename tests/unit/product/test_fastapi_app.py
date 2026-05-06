"""Unit tests for the optional FastAPI product adapter."""

import asyncio
import sys
import types

import pytest

from graph_analytics_ai.product.api import PRODUCT_API_ENDPOINTS
from graph_analytics_ai.product.fastapi_app import create_product_fastapi_app


class FakeFastAPI:
    def __init__(self, title, version, lifespan=None):
        # Accept ``lifespan`` so the fixture stays compatible with the
        # FR-31a app factory which passes one to register the agentic
        # supervisor's startup-sweep / shutdown-drain hooks.
        self.title = title
        self.version = version
        self.lifespan = lifespan
        self.routes = []
        self.middlewares = []

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

    def add_middleware(self, middleware_class, **kwargs):
        # The factory unconditionally adds CORSMiddleware. Recording
        # rather than ignoring lets future tests assert on it.
        self.middlewares.append({"class": middleware_class, "kwargs": kwargs})


class FakeRequest:
    def __init__(self, method, path_params=None, query_params=None, body=None):
        self.method = method
        self.path_params = path_params or {}
        self.query_params = query_params or {}
        self.body = body or {}

    async def json(self):
        return self.body


class _FakeCORSMiddleware:
    """Stand-in for ``fastapi.middleware.cors.CORSMiddleware``.

    The factory only references the class — never instantiates it
    itself — so an empty placeholder is sufficient for the fake
    ``add_middleware`` to record.
    """


@pytest.fixture
def fake_fastapi_module(monkeypatch):
    fastapi_module = types.ModuleType("fastapi")
    fastapi_module.FastAPI = FakeFastAPI
    fastapi_module.Request = FakeRequest
    # The factory imports ``fastapi.Response`` from the route-handler
    # closure. A minimal placeholder keeps the import resolvable.
    fastapi_module.Response = type("FakeResponse", (), {})
    monkeypatch.setitem(sys.modules, "fastapi", fastapi_module)

    # The real ``from fastapi.middleware.cors import CORSMiddleware``
    # resolves through fastapi.middleware.cors. Build that submodule
    # tree on the fake so the import succeeds without pulling real
    # FastAPI into the test process.
    middleware_module = types.ModuleType("fastapi.middleware")
    cors_module = types.ModuleType("fastapi.middleware.cors")
    cors_module.CORSMiddleware = _FakeCORSMiddleware
    middleware_module.cors = cors_module
    fastapi_module.middleware = middleware_module
    monkeypatch.setitem(sys.modules, "fastapi.middleware", middleware_module)
    monkeypatch.setitem(sys.modules, "fastapi.middleware.cors", cors_module)

    return fastapi_module


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


def test_create_product_fastapi_app_wires_supervisor_when_explicitly_enabled(
    fake_fastapi_module,
):
    """``enable_agentic_supervisor=True`` injects a supervisor + lifespan hooks."""

    class _Service:
        """Minimal service stub — the factory only assigns the supervisor on it."""

        _agentic_run_supervisor = None

    service = _Service()
    app = create_product_fastapi_app(service=service, enable_agentic_supervisor=True)

    # Supervisor must be assigned to the service so start_workflow_run /
    # cancel_workflow_run / get_workflow_run_status route through it.
    assert service._agentic_run_supervisor is not None
    supervisor = service._agentic_run_supervisor

    # Lifespan must be registered. We exercise it end-to-end so the
    # startup-sweep + shutdown-drain hooks are pinned, not just present.
    assert app.lifespan is not None
    sweep_calls: list = []
    shutdown_calls: list = []
    monkey_supervisor_orig_sweep = supervisor.sweep_orphan_runs
    monkey_supervisor_orig_shutdown = supervisor.shutdown

    def record_sweep(*args, **kwargs):
        sweep_calls.append((args, kwargs))
        return []

    def record_shutdown(*args, **kwargs):
        shutdown_calls.append((args, kwargs))
        return monkey_supervisor_orig_shutdown(*args, **kwargs)

    supervisor.sweep_orphan_runs = record_sweep
    supervisor.shutdown = record_shutdown

    async def drive():
        async with app.lifespan(app):
            pass

    asyncio.run(drive())

    assert sweep_calls, "lifespan startup must call sweep_orphan_runs"
    assert shutdown_calls, "lifespan shutdown must drain the supervisor pool"
    assert shutdown_calls[0][1].get("wait") is False, (
        "shutdown should be non-blocking so the API process exits "
        "promptly even if a worker is mid-step"
    )


def test_create_product_fastapi_app_skips_supervisor_when_disabled(fake_fastapi_module):
    """When the supervisor is off, no hook is registered and the service is untouched."""

    class _Service:
        _agentic_run_supervisor = None

    service = _Service()
    app = create_product_fastapi_app(service=service, enable_agentic_supervisor=False)

    assert service._agentic_run_supervisor is None
    # Lifespan still exists (it's always passed) but exercising it must
    # be a no-op — no sweep, no shutdown — when the supervisor was not
    # constructed.
    assert app.lifespan is not None

    async def drive():
        async with app.lifespan(app):
            pass

    asyncio.run(drive())  # would raise if the lifespan tried to call None.sweep


def test_create_product_fastapi_app_resolves_supervisor_from_env(
    fake_fastapi_module, monkeypatch
):
    """``AGA_ENABLE_AGENTIC_SUPERVISOR=1`` enables the supervisor without an arg."""

    monkeypatch.setenv("AGA_ENABLE_AGENTIC_SUPERVISOR", "1")

    class _Service:
        _agentic_run_supervisor = None

    service = _Service()
    app = create_product_fastapi_app(service=service)

    assert service._agentic_run_supervisor is not None

    # Drain so the worker pool doesn't leak between tests.
    service._agentic_run_supervisor.shutdown(wait=False)
    # Reference ``app`` so the linter sees the test's intent of asserting the
    # factory didn't raise even when the arg is left to env-resolution.
    assert app.lifespan is not None


def test_create_product_fastapi_app_env_off_keeps_supervisor_disabled(
    fake_fastapi_module, monkeypatch
):
    """Falsy env values (``""``, ``"0"``, ``"off"``) leave the supervisor disabled."""

    monkeypatch.setenv("AGA_ENABLE_AGENTIC_SUPERVISOR", "0")

    class _Service:
        _agentic_run_supervisor = None

    service = _Service()
    app = create_product_fastapi_app(service=service)

    assert service._agentic_run_supervisor is None
    assert app.lifespan is not None


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
