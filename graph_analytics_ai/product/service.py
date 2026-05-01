"""Application services for product UI workflows.

The service layer exposes UI-ready read models and workflow operations without
coupling the core package to a web framework.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .constants import PRODUCT_SCHEMA_VERSION
from .models import (
    ConnectionProfile,
    ChartSpec,
    PublishedSnapshot,
    ReportManifest,
    ReportSection,
    ReportStatus,
    WorkflowDAGEdge,
    WorkflowStep,
    create_audit_event,
    create_published_snapshot,
)
from .repository import ProductRepository


@dataclass
class WorkspaceOverview:
    """Workspace summary for dashboard and API landing pages."""

    workspace: Dict[str, Any]
    counts: Dict[str, int]
    latest_workflow_runs: List[Dict[str, Any]] = field(default_factory=list)
    latest_reports: List[Dict[str, Any]] = field(default_factory=list)
    latest_audit_events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert overview to an API-friendly dictionary."""

        return {
            "workspace": self.workspace,
            "counts": self.counts,
            "latest_workflow_runs": self.latest_workflow_runs,
            "latest_reports": self.latest_reports,
            "latest_audit_events": self.latest_audit_events,
        }


@dataclass
class WorkflowDAGView:
    """Workflow run DAG shape for the operational visualizer."""

    run_id: str
    workspace_id: str
    status: str
    workflow_mode: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert DAG view to an API-friendly dictionary."""

        return {
            "run_id": self.run_id,
            "workspace_id": self.workspace_id,
            "status": self.status,
            "workflow_mode": self.workflow_mode,
            "nodes": self.nodes,
            "edges": self.edges,
            "warnings": self.warnings,
            "errors": self.errors,
        }


@dataclass
class ReportBundle:
    """Complete dynamic report payload for rendering or publication."""

    manifest: Dict[str, Any]
    sections: List[Dict[str, Any]]
    charts: List[Dict[str, Any]]
    snapshots: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report bundle to an API-friendly dictionary."""

        return {
            "manifest": self.manifest,
            "sections": self.sections,
            "charts": self.charts,
            "snapshots": self.snapshots,
        }


@dataclass
class WorkspaceBundle:
    """Portable workspace export payload."""

    schema_version: str
    workspace: Dict[str, Any]
    connection_profiles: List[Dict[str, Any]]
    graph_profiles: List[Dict[str, Any]]
    source_documents: List[Dict[str, Any]]
    requirement_interviews: List[Dict[str, Any]]
    requirement_versions: List[Dict[str, Any]]
    workflow_runs: List[Dict[str, Any]]
    reports: List[Dict[str, Any]]
    audit_events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert bundle to an API-friendly dictionary."""

        return {
            "schema_version": self.schema_version,
            "workspace": self.workspace,
            "connection_profiles": self.connection_profiles,
            "graph_profiles": self.graph_profiles,
            "source_documents": self.source_documents,
            "requirement_interviews": self.requirement_interviews,
            "requirement_versions": self.requirement_versions,
            "workflow_runs": self.workflow_runs,
            "reports": self.reports,
            "audit_events": self.audit_events,
        }


class ProductService:
    """Use-case oriented product operations for the future UI API."""

    def __init__(self, repository: ProductRepository):
        """Initialize service."""

        self.repository = repository

    def get_workspace_overview(
        self,
        workspace_id: str,
        recent_limit: int = 5,
    ) -> WorkspaceOverview:
        """Build a workspace dashboard summary."""

        workspace = self.repository.get_workspace(workspace_id)
        connection_profiles = self.repository.list_connection_profiles(workspace_id)
        graph_profiles = self.repository.list_graph_profiles(workspace_id)
        source_documents = self.repository.list_source_documents(workspace_id)
        requirement_versions = self.repository.list_requirement_versions(workspace_id)
        workflow_runs = self.repository.list_workflow_runs(workspace_id)
        reports = self.repository.list_report_manifests(workspace_id)
        audit_events = self.repository.list_audit_events(
            workspace_id,
            limit=recent_limit,
        )

        counts = {
            "connection_profiles": len(connection_profiles),
            "graph_profiles": len(graph_profiles),
            "source_documents": len(source_documents),
            "requirement_versions": len(requirement_versions),
            "workflow_runs": len(workflow_runs),
            "reports": len(reports),
        }

        return WorkspaceOverview(
            workspace=workspace.to_dict(),
            counts=counts,
            latest_workflow_runs=[
                run.to_dict() for run in workflow_runs[:recent_limit]
            ],
            latest_reports=[report.to_dict() for report in reports[:recent_limit]],
            latest_audit_events=[event.to_dict() for event in audit_events],
        )

    def get_workflow_dag_view(self, run_id: str) -> WorkflowDAGView:
        """Build the run-level operational DAG for visualization."""

        run = self.repository.get_workflow_run(run_id)
        return WorkflowDAGView(
            run_id=run.run_id,
            workspace_id=run.workspace_id,
            status=run.status.value,
            workflow_mode=run.workflow_mode.value,
            nodes=[self._workflow_step_node(step) for step in run.steps],
            edges=[self._workflow_edge(edge) for edge in run.dag_edges],
            warnings=run.warnings,
            errors=run.errors,
        )

    def get_report_bundle(self, report_id: str) -> ReportBundle:
        """Load a full dynamic report payload."""

        manifest = self.repository.get_report_manifest(report_id)
        sections = self.repository.list_report_sections(report_id)
        charts = self.repository.list_chart_specs(report_id)
        snapshots = self.repository.list_published_snapshots(report_id)

        return self._report_bundle(manifest, sections, charts, snapshots)

    def export_workspace_bundle(
        self,
        workspace_id: str,
        include_audit_events: bool = True,
        audit_limit: int = 1000,
    ) -> WorkspaceBundle:
        """Export workspace metadata without resolved secrets or secret refs."""

        workspace = self.repository.get_workspace(workspace_id)
        connection_profiles = self.repository.list_connection_profiles(workspace_id)
        graph_profiles = self.repository.list_graph_profiles(workspace_id)
        source_documents = self.repository.list_source_documents(workspace_id)
        requirement_interviews = self.repository.list_requirement_interviews(workspace_id)
        requirement_versions = self.repository.list_requirement_versions(workspace_id)
        workflow_runs = self.repository.list_workflow_runs(workspace_id)
        report_manifests = self.repository.list_report_manifests(workspace_id)

        reports = [
            self.get_report_bundle(report.report_id).to_dict()
            for report in report_manifests
        ]
        audit_events = (
            [
                event.to_dict()
                for event in self.repository.list_audit_events(
                    workspace_id,
                    limit=audit_limit,
                )
            ]
            if include_audit_events
            else []
        )

        return WorkspaceBundle(
            schema_version=PRODUCT_SCHEMA_VERSION,
            workspace=workspace.to_dict(),
            connection_profiles=[
                self._export_connection_profile(profile)
                for profile in connection_profiles
            ],
            graph_profiles=[profile.to_dict() for profile in graph_profiles],
            source_documents=[document.to_dict() for document in source_documents],
            requirement_interviews=[
                interview.to_dict() for interview in requirement_interviews
            ],
            requirement_versions=[
                version.to_dict() for version in requirement_versions
            ],
            workflow_runs=[run.to_dict() for run in workflow_runs],
            reports=reports,
            audit_events=audit_events,
        )

    def publish_report(self, report_id: str, actor: str) -> ReportBundle:
        """Publish a report and record an immutable snapshot plus audit event."""

        manifest = self.repository.get_report_manifest(report_id)
        sections = self.repository.list_report_sections(report_id)
        charts = self.repository.list_chart_specs(report_id)
        rendered_snapshot = {
            "manifest": manifest.to_dict(),
            "sections": [section.to_dict() for section in sections],
            "charts": [chart.to_dict() for chart in charts],
        }
        content_hash = self._content_hash(rendered_snapshot)

        snapshot = create_published_snapshot(
            workspace_id=manifest.workspace_id,
            report_id=manifest.report_id,
            title=manifest.title,
            published_by=actor,
            content_hash=content_hash,
            rendered_snapshot=rendered_snapshot,
        )
        self.repository.create_published_snapshot(snapshot)

        manifest.status = ReportStatus.PUBLISHED
        manifest.published_snapshot_id = snapshot.published_snapshot_id
        self.repository.update_report_manifest(manifest)

        audit_event = create_audit_event(
            workspace_id=manifest.workspace_id,
            actor=actor,
            action="publish_report",
            target_type="report",
            target_id=manifest.report_id,
            details={"published_snapshot_id": snapshot.published_snapshot_id},
        )
        self.repository.create_audit_event(audit_event)

        return self._report_bundle(manifest, sections, charts, [snapshot])

    def _report_bundle(
        self,
        manifest: ReportManifest,
        sections: List[ReportSection],
        charts: List[ChartSpec],
        snapshots: List[PublishedSnapshot],
    ) -> ReportBundle:
        return ReportBundle(
            manifest=manifest.to_dict(),
            sections=[section.to_dict() for section in sections],
            charts=[chart.to_dict() for chart in charts],
            snapshots=[snapshot.to_dict() for snapshot in snapshots],
        )

    def _workflow_step_node(self, step: WorkflowStep) -> Dict[str, Any]:
        node = step.to_dict()
        node["id"] = step.step_id
        return node

    def _workflow_edge(self, edge: WorkflowDAGEdge) -> Dict[str, Any]:
        return {
            "from": edge.from_step_id,
            "to": edge.to_step_id,
            **edge.to_dict(),
        }

    def _export_connection_profile(
        self,
        profile: ConnectionProfile,
    ) -> Dict[str, Any]:
        doc = profile.to_dict()
        secret_ref_keys = sorted(doc.get("secret_refs", {}).keys())
        doc.pop("secret_refs", None)
        doc["secret_ref_keys"] = secret_ref_keys
        return doc

    def _content_hash(self, payload: Dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
