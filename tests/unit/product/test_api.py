"""Unit tests for product API contract definitions."""

from graph_analytics_ai.product import PRODUCT_API_ENDPOINTS, list_product_api_endpoints


def test_product_api_contract_includes_core_ui_routes():
    """API contract includes the planned product UI route surface."""

    endpoints = list_product_api_endpoints()
    route_keys = {(endpoint["method"], endpoint["path"]) for endpoint in endpoints}

    assert ("GET", "/api/workspaces/{workspace_id}/overview") in route_keys
    assert (
        "POST",
        "/api/connection-profiles/{connection_profile_id}/verify",
    ) in route_keys
    assert ("GET", "/api/runs/{run_id}/workflow-dag") in route_keys
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
    assert "verify_connection_profile" in service_methods
    assert "discover_graph_profile" in service_methods
    assert "start_requirements_copilot" in service_methods
    assert "update_workflow_step" in service_methods
    assert "publish_report" in service_methods
    assert all(endpoint.service_method for endpoint in PRODUCT_API_ENDPOINTS)
