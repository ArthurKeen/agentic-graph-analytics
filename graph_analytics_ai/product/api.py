"""Framework-neutral API contract for the product UI.

The actual HTTP layer can be implemented with FastAPI later. This module keeps
the route surface explicit and testable without adding a hard web dependency to
the core package.
"""

from dataclasses import dataclass, field
from enum import Enum
from inspect import Parameter, signature
from types import UnionType
from typing import Any, Dict, List, Optional, Union, get_args, get_origin


@dataclass(frozen=True)
class ProductAPIEndpoint:
    """Product UI API endpoint contract."""

    method: str
    path: str
    service_method: str
    summary: str
    tags: List[str] = field(default_factory=list)
    request_model: Optional[str] = None
    response_model: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert endpoint contract to a serializable dictionary."""

        return {
            "method": self.method,
            "path": self.path,
            "service_method": self.service_method,
            "summary": self.summary,
            "tags": self.tags,
            "request_model": self.request_model,
            "response_model": self.response_model,
        }


PRODUCT_API_ENDPOINTS = [
    ProductAPIEndpoint(
        method="POST",
        path="/api/workspaces",
        service_method="create_workspace",
        summary="Create a customer/project workspace",
        tags=["workspaces"],
        request_model="CreateWorkspaceRequest",
        response_model="Workspace",
    ),
    ProductAPIEndpoint(
        method="GET",
        path="/api/workspaces",
        service_method="list_workspaces",
        summary="List workspaces",
        tags=["workspaces"],
        response_model="List[Workspace]",
    ),
    ProductAPIEndpoint(
        method="GET",
        path="/api/workspaces/{workspace_id}/overview",
        service_method="get_workspace_overview",
        summary="Get workspace dashboard overview",
        tags=["workspaces"],
        response_model="WorkspaceOverview",
    ),
    ProductAPIEndpoint(
        method="PATCH",
        path="/api/workspaces/{workspace_id}",
        service_method="update_workspace",
        summary="Update editable workspace metadata",
        tags=["workspaces"],
        request_model="UpdateWorkspaceRequest",
        response_model="Workspace",
    ),
    ProductAPIEndpoint(
        method="POST",
        path="/api/workspaces/{workspace_id}/archive",
        service_method="archive_workspace",
        summary="Archive (soft-delete) a workspace",
        tags=["workspaces"],
        request_model="ArchiveWorkspaceRequest",
        response_model="Workspace",
    ),
    ProductAPIEndpoint(
        method="GET",
        path="/api/workspaces/{workspace_id}/health",
        service_method="check_workspace_health",
        summary="Check workspace product metadata health",
        tags=["workspaces", "administration"],
        response_model="WorkspaceHealthResult",
    ),
    ProductAPIEndpoint(
        method="POST",
        path="/api/workspaces/{workspace_id}/connection-profiles",
        service_method="create_connection_profile",
        summary="Create an ArangoDB connection profile",
        tags=["connection-profiles"],
        request_model="CreateConnectionProfileRequest",
        response_model="ConnectionProfile",
    ),
    ProductAPIEndpoint(
        method="POST",
        path="/api/connection-profiles/{connection_profile_id}/verify",
        service_method="verify_connection_profile",
        summary="Verify an ArangoDB connection profile",
        tags=["connection-profiles"],
        request_model="ConnectionVerificationRequest",
        response_model="ConnectionVerificationResult",
    ),
    ProductAPIEndpoint(
        method="GET",
        path="/api/connection-profiles/{connection_profile_id}/graphs",
        service_method="list_connection_profile_graphs",
        summary="List named graphs visible on a connection profile",
        tags=["connection-profiles", "graph-profiles"],
        response_model="ConnectionGraphsResult",
    ),
    ProductAPIEndpoint(
        method="POST",
        path="/api/connection-profiles/{connection_profile_id}/discover-graph",
        service_method="discover_graph_profile",
        summary="Discover graph schema and persist a graph profile",
        tags=["graph-profiles"],
        request_model="GraphDiscoveryRequest",
        response_model="GraphDiscoveryResult",
    ),
    ProductAPIEndpoint(
        method="POST",
        path="/api/graph-profiles/{graph_profile_id}/requirements-copilot/sessions",
        service_method="start_requirements_copilot",
        summary="Start a schema-aware Requirements Copilot session",
        tags=["requirements-copilot"],
        request_model="StartRequirementsCopilotRequest",
        response_model="RequirementInterview",
    ),
    ProductAPIEndpoint(
        method="POST",
        path="/api/requirements-copilot/sessions/{requirement_interview_id}/answer",
        service_method="answer_requirements_copilot_question",
        summary="Record a Requirements Copilot answer",
        tags=["requirements-copilot"],
        request_model="RequirementsCopilotAnswerRequest",
        response_model="RequirementInterview",
    ),
    ProductAPIEndpoint(
        method="POST",
        path="/api/requirements-copilot/sessions/{requirement_interview_id}/generate-draft",
        service_method="generate_requirements_copilot_draft",
        summary="Generate a Requirements Copilot BRD draft",
        tags=["requirements-copilot"],
        response_model="RequirementsDraftResult",
    ),
    ProductAPIEndpoint(
        method="POST",
        path="/api/requirements-copilot/sessions/{requirement_interview_id}/approve",
        service_method="approve_requirements_copilot_draft",
        summary="Approve a Requirements Copilot draft into a requirement version",
        tags=["requirements-copilot"],
        request_model="ApproveRequirementsCopilotRequest",
        response_model="RequirementVersion",
    ),
    ProductAPIEndpoint(
        method="GET",
        path="/api/runs/{run_id}/workflow-dag",
        service_method="get_workflow_dag_view",
        summary="Get visual workflow DAG for a run",
        tags=["workflow-runs"],
        response_model="WorkflowDAGView",
    ),
    ProductAPIEndpoint(
        method="POST",
        path="/api/runs",
        service_method="create_workflow_run_from_steps",
        summary="Create a visualizable workflow run",
        tags=["workflow-runs"],
        request_model="CreateWorkflowRunRequest",
        response_model="WorkflowRun",
    ),
    ProductAPIEndpoint(
        method="POST",
        path="/api/runs/{run_id}/start",
        service_method="start_workflow_run",
        summary="Start a queued workflow run",
        tags=["workflow-runs"],
        response_model="WorkflowRun",
    ),
    ProductAPIEndpoint(
        method="PATCH",
        path="/api/runs/{run_id}/steps/{step_id}",
        service_method="update_workflow_step",
        summary="Update workflow step status and artifacts",
        tags=["workflow-runs"],
        request_model="WorkflowStepUpdateRequest",
        response_model="WorkflowStepUpdateResult",
    ),
    ProductAPIEndpoint(
        method="GET",
        path="/api/runs/{run_id}/recovery-actions",
        service_method="supported_workflow_recovery_actions",
        summary="List supported workflow recovery actions by step",
        tags=["workflow-runs"],
    ),
    ProductAPIEndpoint(
        method="GET",
        path="/api/reports/{report_id}",
        service_method="get_report_bundle",
        summary="Get a dynamic report bundle",
        tags=["reports"],
        response_model="ReportBundle",
    ),
    ProductAPIEndpoint(
        method="POST",
        path="/api/reports/{report_id}/publish",
        service_method="publish_report",
        summary="Publish an immutable report snapshot",
        tags=["reports"],
        request_model="PublishReportRequest",
        response_model="ReportBundle",
    ),
    ProductAPIEndpoint(
        method="GET",
        path="/api/reports/{report_id}/export",
        service_method="export_report",
        summary="Export a report to HTML or Markdown",
        tags=["reports"],
        response_model="ReportExportResult",
    ),
    ProductAPIEndpoint(
        method="GET",
        path="/api/workspaces/{workspace_id}/export",
        service_method="export_workspace_bundle",
        summary="Export a workspace metadata bundle",
        tags=["workspaces"],
        response_model="WorkspaceBundle",
    ),
    ProductAPIEndpoint(
        method="POST",
        path="/api/workspaces/import",
        service_method="import_workspace_bundle",
        summary="Import a workspace metadata bundle",
        tags=["workspaces"],
        request_model="WorkspaceBundle",
        response_model="WorkspaceImportResult",
    ),
]


def list_product_api_endpoints() -> List[Dict[str, Any]]:
    """List product API endpoint contracts."""

    return [endpoint.to_dict() for endpoint in PRODUCT_API_ENDPOINTS]


class ProductAPIDispatcher:
    """Framework-neutral dispatcher from API contract to service methods."""

    def __init__(
        self,
        service: Any,
        endpoints: Optional[List[ProductAPIEndpoint]] = None,
    ):
        """Initialize dispatcher."""

        self.service = service
        self.endpoints = endpoints or PRODUCT_API_ENDPOINTS

    def dispatch(
        self,
        method: str,
        path: str,
        path_params: Optional[Dict[str, Any]] = None,
        query: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Dispatch a request-shaped call to the matching service method."""

        endpoint = self.get_endpoint(method, path)
        kwargs: Dict[str, Any] = {}
        kwargs.update(path_params or {})
        kwargs.update(query or {})
        kwargs.update(body or {})

        service_method = getattr(self.service, endpoint.service_method)
        kwargs = self._coerce_kwargs(service_method, kwargs)
        return self._serialize_response(service_method(**kwargs))

    def get_endpoint(self, method: str, path: str) -> ProductAPIEndpoint:
        """Find an API endpoint by method and path template."""

        normalized_method = method.upper()
        for endpoint in self.endpoints:
            if endpoint.method == normalized_method and endpoint.path == path:
                return endpoint
        raise KeyError(f"Product API endpoint not found: {normalized_method} {path}")

    def _coerce_kwargs(self, service_method: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        method_signature = signature(service_method)
        coerced = dict(kwargs)
        for name, parameter in method_signature.parameters.items():
            if name not in coerced or parameter.annotation is Parameter.empty:
                continue
            coerced[name] = self._coerce_value(coerced[name], parameter.annotation)
        return coerced

    def _coerce_value(self, value: Any, annotation: Any) -> Any:
        if annotation is Any or value is None:
            return value

        origin = get_origin(annotation)
        args = get_args(annotation)

        if origin in {Union, UnionType}:
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) == 1:
                return self._coerce_value(value, non_none_args[0])
            return value

        if origin in {list, List} and args and isinstance(value, list):
            return [self._coerce_value(item, args[0]) for item in value]

        if origin in {dict, Dict}:
            return value

        if annotation is bool and isinstance(value, str):
            return value.lower() in {"1", "true", "yes", "on"}

        if annotation is int and isinstance(value, str):
            return int(value)

        if annotation is float and isinstance(value, str):
            return float(value)

        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return value if isinstance(value, annotation) else annotation(value)

        if isinstance(annotation, type) and hasattr(annotation, "from_dict") and isinstance(value, dict):
            return annotation.from_dict(value)

        return value

    def _serialize_response(self, value: Any) -> Any:
        if hasattr(value, "to_dict"):
            return value.to_dict()
        if isinstance(value, list):
            return [self._serialize_response(item) for item in value]
        if isinstance(value, dict):
            return {
                key: self._serialize_response(item)
                for key, item in value.items()
            }
        return value
