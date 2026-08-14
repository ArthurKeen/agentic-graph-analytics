"""Unit tests for product API contract definitions."""

from graph_analytics_ai.product import (
    DeploymentMode,
    PRODUCT_API_ENDPOINTS,
    ProductAPIDispatcher,
    WorkflowMode,
    WorkflowStepStatus,
    list_product_api_endpoints,
)
from graph_analytics_ai.product.models import WorkflowDAGEdge, WorkflowStep


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
    assert ("GET", "/api/catalog/stats") in route_keys
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
