"""Unit tests for product API contract definitions."""

import pytest
import re
from inspect import Parameter, signature

from graph_analytics_ai.product import (
    DeploymentMode,
    PRODUCT_API_ENDPOINTS,
    ProductAPIDispatcher,
    WorkflowMode,
    WorkflowStepStatus,
    list_product_api_endpoints,
)
from graph_analytics_ai.product.exceptions import ValidationError
from graph_analytics_ai.product.models import WorkflowDAGEdge, WorkflowStep


def test_every_get_route_can_supply_its_service_methods_required_args():
    """A GET route must carry every required service argument in its path.

    GET/DELETE requests have no body, so the dispatcher can only source
    arguments from path params (and optional query params, which by definition
    have defaults). A required service parameter that is not in the path
    template can therefore *never* be supplied, and the route 500s on every
    call with ``TypeError: missing 1 required positional argument``.

    This shipped once: ``GET /api/catalog/stats`` mapped to
    ``get_analysis_catalog_stats(workspace_id)`` with no ``{workspace_id}`` in
    the path. A route-existence assertion passed while the route was
    unconditionally broken, so assert invocability rather than presence.
    """

    from graph_analytics_ai.product.service import ProductService

    bodyless_methods = {"GET", "DELETE", "HEAD"}
    failures = []

    for endpoint in PRODUCT_API_ENDPOINTS:
        if endpoint.method not in bodyless_methods:
            continue
        service_method = getattr(ProductService, endpoint.service_method, None)
        if service_method is None:
            failures.append(
                f"{endpoint.method} {endpoint.path}: "
                f"ProductService has no method {endpoint.service_method!r}"
            )
            continue

        path_params = set(re.findall(r"{(\w+)}", endpoint.path))
        for name, parameter in signature(service_method).parameters.items():
            if name == "self":
                continue
            if parameter.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD):
                continue
            if parameter.default is not Parameter.empty:
                continue
            if name not in path_params:
                failures.append(
                    f"{endpoint.method} {endpoint.path} -> "
                    f"{endpoint.service_method}(): required argument {name!r} "
                    f"cannot be supplied (not in path params {sorted(path_params)})"
                )

    assert not failures, "Uninvocable routes:\n" + "\n".join(failures)


def test_product_api_contract_includes_core_ui_routes():
    """API contract includes the planned product UI route surface."""

    endpoints = list_product_api_endpoints()
    route_keys = {(endpoint["method"], endpoint["path"]) for endpoint in endpoints}

    assert ("POST", "/api/workspaces") in route_keys
    assert ("GET", "/api/workspaces/{workspace_id}/overview") in route_keys
    assert ("GET", "/api/workspaces/{workspace_id}/health") in route_keys
    assert (
        "POST",
        "/api/workspaces/{workspace_id}/connection-profiles",
    ) in route_keys
    assert (
        "POST",
        "/api/connection-profiles/{connection_profile_id}/verify",
    ) in route_keys
    assert (
        "GET",
        "/api/connection-profiles/{connection_profile_id}/graphs",
    ) in route_keys
    assert ("GET", "/api/runs/{run_id}/workflow-dag") in route_keys
    assert (
        "GET",
        "/api/workspaces/{workspace_id}/analysis-catalog",
    ) in route_keys
    assert (
        "GET",
        "/api/workspaces/{workspace_id}/analysis-executions",
    ) in route_keys
    assert (
        "POST",
        "/api/workspaces/{workspace_id}/analysis-executions/compare",
    ) in route_keys
    assert (
        "GET",
        "/api/analysis-executions/{analysis_execution_id}/lineage",
    ) in route_keys
    assert (
        "GET",
        "/api/workspaces/{workspace_id}/analysis-epochs",
    ) in route_keys
    assert ("GET", "/api/workspaces/{workspace_id}/catalog/stats") in route_keys
    # FR-19..FR-26: use cases and analysis templates as product records.
    assert ("POST", "/api/workspaces/{workspace_id}/use-cases") in route_keys
    assert ("GET", "/api/workspaces/{workspace_id}/use-cases") in route_keys
    assert ("PATCH", "/api/use-cases/{use_case_id}") in route_keys
    assert ("POST", "/api/use-cases/{use_case_id}/status") in route_keys
    assert ("POST", "/api/use-cases/{use_case_id}/priority") in route_keys
    assert (
        "POST",
        "/api/workspaces/{workspace_id}/analysis-templates",
    ) in route_keys
    assert (
        "POST",
        "/api/workspaces/{workspace_id}/analysis-templates/import",
    ) in route_keys
    assert (
        "PATCH",
        "/api/analysis-templates/{analysis_template_id}",
    ) in route_keys
    assert (
        "POST",
        "/api/analysis-templates/{analysis_template_id}/approve",
    ) in route_keys
    assert (
        "GET",
        "/api/analysis-templates/{analysis_template_id}/versions",
    ) in route_keys

    # Exactly one public URL per catalog operation. The earlier draft also
    # exposed /catalog/executions, /catalog/epochs, and
    # /catalog/executions/{id}/lineage as "compatibility" aliases, but these
    # were brand-new endpoints with no existing consumers — the duplicates
    # only doubled the surface that has to stay backward-compatible.
    for retired_alias in (
        "/api/workspaces/{workspace_id}/catalog/executions",
        "/api/workspaces/{workspace_id}/catalog/epochs",
        "/api/catalog/executions/{execution_id}/lineage",
    ):
        assert ("GET", retired_alias) not in route_keys
    assert (
        "POST",
        "/api/requirements-copilot/sessions/{requirement_interview_id}/generate-draft",
    ) in route_keys
    assert ("GET", "/api/reports/{report_id}") in route_keys
    assert ("POST", "/api/workspaces/import") in route_keys


def test_product_api_contract_maps_to_service_methods():
    """Every endpoint declares a service method for future route wiring."""

    service_methods = {endpoint.service_method for endpoint in PRODUCT_API_ENDPOINTS}

    assert "get_workspace_overview" in service_methods
    assert "create_workspace" in service_methods
    assert "create_connection_profile" in service_methods
    assert "verify_connection_profile" in service_methods
    assert "list_connection_profile_graphs" in service_methods
    assert "discover_graph_profile" in service_methods
    assert "start_requirements_copilot" in service_methods
    assert "update_workflow_step" in service_methods
    assert "browse_analysis_catalog" in service_methods
    assert "compare_analysis_executions" in service_methods
    assert "get_analysis_lineage" in service_methods
    assert "get_analysis_catalog_stats" in service_methods
    assert "publish_report" in service_methods
    assert all(endpoint.service_method for endpoint in PRODUCT_API_ENDPOINTS)


def test_product_api_dispatcher_calls_service_method_and_serializes_response():
    """Dispatcher maps endpoint contracts to service calls."""

    class Response:
        def to_dict(self):
            return {"workspace_id": "workspace-1", "ok": True}

    class Service:
        def __init__(self):
            self.calls = []

        def get_workspace_overview(self, **kwargs):
            self.calls.append(kwargs)
            return Response()

    service = Service()
    response = ProductAPIDispatcher(service).dispatch(
        method="GET",
        path="/api/workspaces/{workspace_id}/overview",
        path_params={"workspace_id": "workspace-1"},
        query={"recent_limit": 3},
    )

    assert response == {"workspace_id": "workspace-1", "ok": True}
    assert service.calls == [{"workspace_id": "workspace-1", "recent_limit": 3}]


def test_product_api_dispatcher_rejects_unknown_endpoint():
    """Dispatcher fails clearly when no endpoint contract matches."""

    try:
        ProductAPIDispatcher(service=object()).dispatch(
            method="GET",
            path="/api/unknown",
        )
    except KeyError as exc:
        assert "/api/unknown" in str(exc)
    else:
        raise AssertionError("Expected KeyError for unknown endpoint")


def test_product_api_dispatcher_coerces_json_shapes_to_service_types():
    """Dispatcher converts API payload shapes into service-level types."""

    class Service:
        def __init__(self):
            self.workflow_call = None
            self.step_update_call = None
            self.connection_call = None

        def create_connection_profile(
            self, workspace_id, deployment_mode: DeploymentMode
        ):
            self.connection_call = {
                "workspace_id": workspace_id,
                "deployment_mode": deployment_mode,
            }
            return {"ok": True}

        def create_workflow_run_from_steps(
            self,
            workspace_id,
            workflow_mode: WorkflowMode,
            steps: list[WorkflowStep],
            dag_edges: list[WorkflowDAGEdge],
        ):
            self.workflow_call = {
                "workspace_id": workspace_id,
                "workflow_mode": workflow_mode,
                "steps": steps,
                "dag_edges": dag_edges,
            }
            return {"ok": True}

        def update_workflow_step(self, run_id, step_id, status: WorkflowStepStatus):
            self.step_update_call = {
                "run_id": run_id,
                "step_id": step_id,
                "status": status,
            }
            return {"ok": True}

    service = Service()
    dispatcher = ProductAPIDispatcher(service)
    dispatcher.dispatch(
        method="POST",
        path="/api/workspaces/{workspace_id}/connection-profiles",
        path_params={"workspace_id": "workspace-1"},
        body={"deployment_mode": "local"},
    )
    dispatcher.dispatch(
        method="POST",
        path="/api/runs",
        body={
            "workspace_id": "workspace-1",
            "workflow_mode": "agentic",
            "steps": [{"step_id": "step-1", "label": "Extract"}],
            "dag_edges": [
                {"from_step_id": "step-1", "to_step_id": "step-2"},
            ],
        },
    )
    dispatcher.dispatch(
        method="PATCH",
        path="/api/runs/{run_id}/steps/{step_id}",
        path_params={"run_id": "run-1", "step_id": "step-1"},
        body={"status": "completed"},
    )

    assert service.connection_call["deployment_mode"] == DeploymentMode.LOCAL
    assert service.workflow_call["workflow_mode"] == WorkflowMode.AGENTIC
    assert isinstance(service.workflow_call["steps"][0], WorkflowStep)
    assert isinstance(service.workflow_call["dag_edges"][0], WorkflowDAGEdge)
    assert service.step_update_call["status"] == WorkflowStepStatus.COMPLETED


def test_dispatch_missing_required_argument_is_a_validation_error():
    """A call that cannot bind is a 400, not a crash.

    Path params, query and body are merged by name, so an endpoint whose path
    omits an argument the service requires reached ``service_method(**kwargs)``
    and raised TypeError — surfacing as a 500 for what is a malformed request.
    Two endpoints shipped that way (``/api/catalog/stats`` was an unconditional
    500; ``/api/connections/list-databases`` 500'd on an empty body).
    """

    class _Service:
        def list_cluster_databases(
            self, endpoint, username, password_secret_env_var, verify_ssl=True
        ):
            raise AssertionError("should not be reached")

    with pytest.raises(ValidationError) as excinfo:
        ProductAPIDispatcher(service=_Service()).dispatch(
            method="POST",
            path="/api/connections/list-databases",
            body={},
        )

    message = str(excinfo.value)
    assert "endpoint" in message
    assert "username" in message
    assert "password_secret_env_var" in message
    # Arguments that have defaults are not required.
    assert "verify_ssl" not in message


def test_dispatch_allows_arguments_that_have_defaults():
    """Optional parameters stay optional — the guard only checks required ones."""

    class _Service:
        def list_default_cluster_databases(self, include_system=False):
            return {"databases": [], "include_system": include_system}

    result = ProductAPIDispatcher(service=_Service()).dispatch(
        method="POST",
        path="/api/connections/default-cluster/databases",
        body={},
    )

    assert result["include_system"] is False


# --------------------------------------------------------------------------- #
# Build identity: /healthz and the reported version (BYOC deploy verification)  #
# --------------------------------------------------------------------------- #


def _app_with_storage(storage):
    from unittest.mock import MagicMock

    from graph_analytics_ai.product.fastapi_app import create_product_fastapi_app

    service = MagicMock()
    service.repository.storage = storage
    return create_product_fastapi_app(service=service)


def _storage(list_workspaces_result=None, error=None, db_name="aga_workspace"):
    from unittest.mock import MagicMock

    storage = MagicMock()
    storage.db.name = db_name
    if error is not None:
        storage.list_workspaces.side_effect = error
    else:
        storage.list_workspaces.return_value = list_workspaces_result or []
    return storage


def test_reported_version_comes_from_the_package_not_a_literal():
    """A deployed build is identified by the version it reports.

    The factory used to default to a hardcoded "0.1.0", so every build claimed
    the same version and the live BYOC service could not be told apart from the
    one it replaced. The default must track the package.
    """

    # FastAPI is an optional extra ([api]); CI installs the package without it.
    pytest.importorskip("fastapi", reason="optional 'api' extra is not installed")
    from fastapi.testclient import TestClient

    from graph_analytics_ai import __version__

    client = TestClient(_app_with_storage(_storage()))

    assert client.get("/openapi.json").json()["info"]["version"] == __version__
    assert client.get("/healthz").json()["version"] == __version__


def test_healthz_reports_the_version_even_when_the_database_is_unreachable():
    """The degraded case is the one the endpoint exists for.

    Routing /healthz through the dispatcher would make a dead database a 500,
    which reports nothing — and an outage is exactly when someone needs to know
    which build is running.
    """

    pytest.importorskip("fastapi", reason="optional 'api' extra is not installed")
    from fastapi.testclient import TestClient

    from graph_analytics_ai import __version__

    client = TestClient(
        _app_with_storage(_storage(error=RuntimeError("connection refused")))
    )
    response = client.get("/healthz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == __version__
    assert payload["database"]["reachable"] is False
    assert "connection refused" in payload["database"]["error"]


def test_setup_py_and_package_version_agree():
    """setup.py derives its version rather than duplicating the literal.

    A packaged version that drifts from the one the service reports makes the
    deploy verifier meaningless.
    """

    import re
    from pathlib import Path

    from graph_analytics_ai import __version__

    setup_src = (Path(__file__).resolve().parents[3] / "setup.py").read_text()
    assert "version=VERSION" in setup_src, "setup.py should not hardcode a version"
    assert not re.search(r'version\s*=\s*"\d+\.\d+\.\d+"', setup_src)
    assert __version__
