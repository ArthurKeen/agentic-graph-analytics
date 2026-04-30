"""High-level product metadata repository."""

from typing import List, Optional

from .models import (
    AuditEvent,
    ChartSpec,
    ConnectionProfile,
    GraphProfile,
    PublishedSnapshot,
    ReportManifest,
    ReportSection,
    RequirementInterview,
    RequirementVersion,
    SourceDocument,
    Workspace,
    WorkflowRun,
)
from .storage import ProductArangoStorage


class ProductRepository:
    """Small façade over product metadata storage.

    The repository provides a stable API for future FastAPI routes without
    exposing storage-specific details to callers.
    """

    def __init__(self, storage: ProductArangoStorage):
        """Initialize repository."""

        self.storage = storage

    def create_workspace(self, workspace: Workspace) -> str:
        """Create a workspace."""

        return self.storage.insert_workspace(workspace)

    def get_workspace(self, workspace_id: str) -> Workspace:
        """Get a workspace."""

        return self.storage.get_workspace(workspace_id)

    def update_workspace(self, workspace: Workspace) -> str:
        """Update a workspace."""

        return self.storage.update_workspace(workspace)

    def list_workspaces(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[Workspace]:
        """List workspaces."""

        return self.storage.list_workspaces(status=status, limit=limit)

    def create_connection_profile(self, profile: ConnectionProfile) -> str:
        """Create a connection profile."""

        return self.storage.insert_connection_profile(profile)

    def get_connection_profile(self, connection_profile_id: str) -> ConnectionProfile:
        """Get a connection profile."""

        return self.storage.get_connection_profile(connection_profile_id)

    def update_connection_profile(self, profile: ConnectionProfile) -> str:
        """Update a connection profile."""

        return self.storage.update_connection_profile(profile)

    def list_connection_profiles(self, workspace_id: str) -> List[ConnectionProfile]:
        """List connection profiles for a workspace."""

        return self.storage.list_connection_profiles(workspace_id)

    def create_graph_profile(self, profile: GraphProfile) -> str:
        """Create a graph profile."""

        return self.storage.insert_graph_profile(profile)

    def get_graph_profile(self, graph_profile_id: str) -> GraphProfile:
        """Get a graph profile."""

        return self.storage.get_graph_profile(graph_profile_id)

    def update_graph_profile(self, profile: GraphProfile) -> str:
        """Update a graph profile."""

        return self.storage.update_graph_profile(profile)

    def list_graph_profiles(self, workspace_id: str) -> List[GraphProfile]:
        """List graph profiles for a workspace."""

        return self.storage.list_graph_profiles(workspace_id)

    def create_source_document(self, document: SourceDocument) -> str:
        """Create a source document."""

        return self.storage.insert_source_document(document)

    def get_source_document(self, document_id: str) -> SourceDocument:
        """Get a source document."""

        return self.storage.get_source_document(document_id)

    def list_source_documents(self, workspace_id: str) -> List[SourceDocument]:
        """List source documents for a workspace."""

        return self.storage.list_source_documents(workspace_id)

    def create_requirement_interview(self, interview: RequirementInterview) -> str:
        """Create a Requirements Copilot interview."""

        return self.storage.insert_requirement_interview(interview)

    def get_requirement_interview(
        self, requirement_interview_id: str
    ) -> RequirementInterview:
        """Get a Requirements Copilot interview."""

        return self.storage.get_requirement_interview(requirement_interview_id)

    def update_requirement_interview(self, interview: RequirementInterview) -> str:
        """Update a Requirements Copilot interview."""

        return self.storage.update_requirement_interview(interview)

    def list_requirement_interviews(
        self, workspace_id: str
    ) -> List[RequirementInterview]:
        """List Requirements Copilot interviews for a workspace."""

        return self.storage.list_requirement_interviews(workspace_id)

    def create_requirement_version(self, version: RequirementVersion) -> str:
        """Create a requirement version."""

        return self.storage.insert_requirement_version(version)

    def get_requirement_version(self, requirement_version_id: str) -> RequirementVersion:
        """Get a requirement version."""

        return self.storage.get_requirement_version(requirement_version_id)

    def update_requirement_version(self, version: RequirementVersion) -> str:
        """Update a requirement version."""

        return self.storage.update_requirement_version(version)

    def list_requirement_versions(self, workspace_id: str) -> List[RequirementVersion]:
        """List requirement versions for a workspace."""

        return self.storage.list_requirement_versions(workspace_id)

    def create_workflow_run(self, run: WorkflowRun) -> str:
        """Create a workflow run."""

        return self.storage.insert_workflow_run(run)

    def get_workflow_run(self, run_id: str) -> WorkflowRun:
        """Get a workflow run."""

        return self.storage.get_workflow_run(run_id)

    def update_workflow_run(self, run: WorkflowRun) -> str:
        """Update a workflow run."""

        return self.storage.update_workflow_run(run)

    def list_workflow_runs(self, workspace_id: str) -> List[WorkflowRun]:
        """List workflow runs for a workspace."""

        return self.storage.list_workflow_runs(workspace_id)

    def create_report_manifest(self, manifest: ReportManifest) -> str:
        """Create a report manifest."""

        return self.storage.insert_report_manifest(manifest)

    def get_report_manifest(self, report_id: str) -> ReportManifest:
        """Get a report manifest."""

        return self.storage.get_report_manifest(report_id)

    def update_report_manifest(self, manifest: ReportManifest) -> str:
        """Update a report manifest."""

        return self.storage.update_report_manifest(manifest)

    def list_report_manifests(self, workspace_id: str) -> List[ReportManifest]:
        """List report manifests for a workspace."""

        return self.storage.list_report_manifests(workspace_id)

    def create_report_section(self, section: ReportSection) -> str:
        """Create a report section."""

        return self.storage.insert_report_section(section)

    def get_report_section(self, section_id: str) -> ReportSection:
        """Get a report section."""

        return self.storage.get_report_section(section_id)

    def list_report_sections(self, report_id: str) -> List[ReportSection]:
        """List report sections for a report."""

        return self.storage.list_report_sections(report_id)

    def create_chart_spec(self, chart: ChartSpec) -> str:
        """Create a chart spec."""

        return self.storage.insert_chart_spec(chart)

    def get_chart_spec(self, chart_id: str) -> ChartSpec:
        """Get a chart spec."""

        return self.storage.get_chart_spec(chart_id)

    def list_chart_specs(self, report_id: str) -> List[ChartSpec]:
        """List chart specs for a report."""

        return self.storage.list_chart_specs(report_id)

    def create_published_snapshot(self, snapshot: PublishedSnapshot) -> str:
        """Create a published snapshot."""

        return self.storage.insert_published_snapshot(snapshot)

    def get_published_snapshot(self, published_snapshot_id: str) -> PublishedSnapshot:
        """Get a published snapshot."""

        return self.storage.get_published_snapshot(published_snapshot_id)

    def list_published_snapshots(self, report_id: str) -> List[PublishedSnapshot]:
        """List published snapshots for a report."""

        return self.storage.list_published_snapshots(report_id)

    def create_audit_event(self, event: AuditEvent) -> str:
        """Create an audit event."""

        return self.storage.insert_audit_event(event)

    def list_audit_events(self, workspace_id: str, limit: int = 100) -> List[AuditEvent]:
        """List audit events for a workspace."""

        return self.storage.list_audit_events(workspace_id, limit=limit)

