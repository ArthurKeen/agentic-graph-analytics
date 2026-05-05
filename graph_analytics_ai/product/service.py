"""Application services for product UI workflows.

The service layer exposes UI-ready read models and workflow operations without
coupling the core package to a web framework.
"""

import hashlib
import html
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..ai.schema.extractor import SchemaExtractor
from ..ai.schema.models import GraphSchema
from ..db_connection import connect_arango_database
from .constants import PRODUCT_SCHEMA_VERSION
from .exceptions import ValidationError
from .models import (
    AuditEvent,
    ChartSpec,
    ConnectionProfile,
    ConnectionVerificationStatus,
    DeploymentMode,
    GraphProfile,
    PublishedSnapshot,
    ReportManifest,
    ReportSection,
    ReportStatus,
    RequirementInterview,
    RequirementInterviewStatus,
    RequirementVersion,
    RequirementVersionStatus,
    SourceDocument,
    Workspace,
    WorkflowDAGEdge,
    WorkflowMode,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowStep,
    WorkflowStepStatus,
    create_audit_event,
    create_connection_profile,
    create_graph_profile,
    create_published_snapshot,
    create_requirement_interview,
    create_requirement_version,
    create_workspace,
    create_workflow_run,
    current_timestamp,
)
from .repository import ProductRepository
from .secrets import EnvironmentSecretResolver, SecretResolver


@dataclass
class WorkspaceOverview:
    """Workspace summary for dashboard and API landing pages."""

    workspace: Dict[str, Any]
    counts: Dict[str, int]
    latest_connection_profiles: List[Dict[str, Any]] = field(default_factory=list)
    latest_graph_profiles: List[Dict[str, Any]] = field(default_factory=list)
    latest_source_documents: List[Dict[str, Any]] = field(default_factory=list)
    latest_requirement_versions: List[Dict[str, Any]] = field(default_factory=list)
    latest_workflow_runs: List[Dict[str, Any]] = field(default_factory=list)
    latest_reports: List[Dict[str, Any]] = field(default_factory=list)
    latest_audit_events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert overview to an API-friendly dictionary."""

        return {
            "workspace": self.workspace,
            "counts": self.counts,
            "latest_connection_profiles": self.latest_connection_profiles,
            "latest_graph_profiles": self.latest_graph_profiles,
            "latest_source_documents": self.latest_source_documents,
            "latest_requirement_versions": self.latest_requirement_versions,
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
class ReportExportResult:
    """Renderable export of a report (HTML or Markdown).

    Deliberately has NO ``to_dict`` method. The framework-neutral dispatcher
    (``ProductAPIDispatcher._serialize_response``) only auto-serializes
    objects with ``to_dict``, so by leaving it off we get pass-through
    behavior. The FastAPI adapter (``fastapi_app.py``) detects this type
    after dispatch and converts it to a non-JSON HTTP ``Response`` with the
    correct ``Content-Type`` and ``Content-Disposition`` headers, so the
    browser triggers a file download.
    """

    content: str
    media_type: str
    filename: str
    fmt: str


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


@dataclass
class WorkspaceImportResult:
    """Result summary for a workspace bundle import."""

    workspace_id: str
    counts: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        """Convert import result to an API-friendly dictionary."""

        return {
            "workspace_id": self.workspace_id,
            "counts": self.counts,
        }


@dataclass
class ConnectionVerificationResult:
    """Result of testing a connection profile."""

    connection_profile_id: str
    workspace_id: str
    status: str
    verified_at: str
    endpoint: str
    database: str
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert verification result to an API-friendly dictionary."""

        return {
            "connection_profile_id": self.connection_profile_id,
            "workspace_id": self.workspace_id,
            "status": self.status,
            "verified_at": self.verified_at,
            "endpoint": self.endpoint,
            "database": self.database,
            "error_message": self.error_message,
        }


@dataclass
class GraphDiscoveryResult:
    """Result of discovering and persisting a graph profile."""

    graph_profile: Dict[str, Any]
    schema_summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert discovery result to an API-friendly dictionary."""

        return {
            "graph_profile": self.graph_profile,
            "schema_summary": self.schema_summary,
        }


@dataclass
class ConnectionGraphSummary:
    """Lightweight named-graph descriptor for a connection profile."""

    name: str
    is_system: bool
    vertex_collections: List[str]
    edge_collections: List[str]
    orphan_collections: List[str]
    edge_definitions: List[Dict[str, Any]]
    vertex_count: Optional[int] = None
    edge_count: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to an API-friendly dictionary."""

        return {
            "name": self.name,
            "is_system": self.is_system,
            "vertex_collections": self.vertex_collections,
            "edge_collections": self.edge_collections,
            "orphan_collections": self.orphan_collections,
            "edge_definitions": self.edge_definitions,
            "vertex_count": self.vertex_count,
            "edge_count": self.edge_count,
        }


@dataclass
class ConnectionGraphsResult:
    """Result of enumerating named graphs for a connection profile."""

    connection_profile_id: str
    workspace_id: str
    database: str
    graphs: List[ConnectionGraphSummary]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_profile_id": self.connection_profile_id,
            "workspace_id": self.workspace_id,
            "database": self.database,
            "graphs": [graph.to_dict() for graph in self.graphs],
        }


@dataclass
class RequirementsDraftResult:
    """Result of generating a Requirements Copilot draft."""

    requirement_interview: Dict[str, Any]
    draft_brd: str
    provenance_labels: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert draft result to an API-friendly dictionary."""

        return {
            "requirement_interview": self.requirement_interview,
            "draft_brd": self.draft_brd,
            "provenance_labels": self.provenance_labels,
        }


@dataclass
class WorkflowStepUpdateResult:
    """Result of updating workflow run step state."""

    workflow_run: Dict[str, Any]
    dag_view: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert update result to an API-friendly dictionary."""

        return {
            "workflow_run": self.workflow_run,
            "dag_view": self.dag_view,
        }


@dataclass
class WorkspaceHealthResult:
    """Workspace product metadata health summary."""

    workspace_id: str
    status: str
    counts: Dict[str, int]
    issues: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert health result to an API-friendly dictionary."""

        return {
            "workspace_id": self.workspace_id,
            "status": self.status,
            "counts": self.counts,
            "issues": self.issues,
        }


def _collections_from_edge_definitions(
    edge_definitions: List[Dict[str, Any]],
    orphan_collections: List[str],
) -> tuple[List[str], List[str]]:
    """Derive deduplicated vertex/edge collection lists from edge definitions."""

    vertex: Dict[str, None] = {}
    edge: Dict[str, None] = {}
    for definition in edge_definitions:
        name = definition.get("edge_collection") or definition.get("collection")
        if name:
            edge[str(name)] = None
        for source in definition.get("from_vertex_collections") or []:
            vertex[str(source)] = None
        for source in definition.get("from") or []:
            vertex[str(source)] = None
        for target in definition.get("to_vertex_collections") or []:
            vertex[str(target)] = None
        for target in definition.get("to") or []:
            vertex[str(target)] = None
    for orphan in orphan_collections or []:
        vertex[str(orphan)] = None
    return list(vertex.keys()), list(edge.keys())


def _safe_collection_total(db: Any, collection_names: List[str]) -> Optional[int]:
    """Sum LENGTH() over the named collections, returning None on failure."""

    if not collection_names:
        return 0
    total = 0
    try:
        for name in collection_names:
            try:
                collection = db.collection(name)
                count = collection.count()
            except Exception:
                cursor = db.aql.execute(
                    "RETURN LENGTH(@@col)",
                    bind_vars={"@col": name},
                )
                count = next(iter(cursor), 0)
            total += int(count or 0)
    except Exception:
        return None
    return total


class ProductService:
    """Use-case oriented product operations for the future UI API."""

    def __init__(
        self,
        repository: ProductRepository,
        secret_resolver: Optional[SecretResolver] = None,
        db_connector: Optional[Callable[..., Any]] = None,
        schema_extractor_factory: Optional[Callable[..., Any]] = None,
    ):
        """Initialize service."""

        self.repository = repository
        self.secret_resolver = secret_resolver or EnvironmentSecretResolver()
        self.db_connector = db_connector or connect_arango_database
        self.schema_extractor_factory = schema_extractor_factory or SchemaExtractor

    def create_workspace(
        self,
        customer_name: str,
        project_name: str,
        environment: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        actor: Optional[str] = None,
    ) -> Workspace:
        """Create customer/project workspace metadata."""

        if not customer_name.strip():
            raise ValidationError("Customer name is required")
        if not project_name.strip():
            raise ValidationError("Project name is required")
        if not environment.strip():
            raise ValidationError("Environment is required")

        workspace = create_workspace(
            customer_name=customer_name.strip(),
            project_name=project_name.strip(),
            environment=environment.strip(),
            description=description.strip(),
            tags=[tag.strip() for tag in tags or [] if tag.strip()],
        )
        self.repository.create_workspace(workspace)
        self.repository.create_audit_event(
            create_audit_event(
                workspace_id=workspace.workspace_id,
                actor=actor or "system",
                action="create_workspace",
                target_type="workspace",
                target_id=workspace.workspace_id,
            )
        )
        return workspace

    def list_workspaces(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Workspace]:
        """List workspaces visible to the caller."""

        return self.repository.list_workspaces(status=status, limit=limit)

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

        # FR-17c requires that "all historical versions remain queryable and
        # individually addressable". The Assets panel surfaces ONE consolidated
        # Requirements row whose canvas-side dropdown is populated from
        # `latest_requirement_versions`, so capping this list silently hides
        # older versions from the UI. Return the full set (sorted desc by
        # version for convenience; the frontend re-sorts) and keep the
        # `recent_limit` cap on the other latest_* fields where it is
        # appropriate.
        sorted_requirement_versions = sorted(
            requirement_versions,
            key=lambda v: (v.version, v.created_at),
            reverse=True,
        )
        return WorkspaceOverview(
            workspace=workspace.to_dict(),
            counts=counts,
            latest_connection_profiles=[
                profile.to_dict() for profile in connection_profiles[:recent_limit]
            ],
            latest_graph_profiles=[
                profile.to_dict() for profile in graph_profiles[:recent_limit]
            ],
            latest_source_documents=[
                document.to_dict() for document in source_documents[:recent_limit]
            ],
            latest_requirement_versions=[
                version.to_dict() for version in sorted_requirement_versions
            ],
            latest_workflow_runs=[
                run.to_dict() for run in workflow_runs[:recent_limit]
            ],
            latest_reports=[report.to_dict() for report in reports[:recent_limit]],
            latest_audit_events=[event.to_dict() for event in audit_events],
        )

    def create_connection_profile(
        self,
        workspace_id: str,
        name: str,
        deployment_mode: DeploymentMode,
        endpoint: str,
        database: str,
        username: str,
        verify_ssl: bool = True,
        secret_refs: Optional[Dict[str, Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConnectionProfile:
        """Create non-secret ArangoDB connection metadata for a workspace."""

        self.repository.get_workspace(workspace_id)
        if not name.strip():
            raise ValidationError("Connection profile name is required")
        if not endpoint.strip():
            raise ValidationError("Connection endpoint is required")
        if not database.strip():
            raise ValidationError("Database name is required")
        if not username.strip():
            raise ValidationError("Database username is required")

        profile = create_connection_profile(
            workspace_id=workspace_id,
            name=name.strip(),
            deployment_mode=deployment_mode,
            endpoint=endpoint.strip(),
            database=database.strip(),
            username=username.strip(),
            verify_ssl=verify_ssl,
            secret_refs=secret_refs or {},
            metadata=metadata or {},
        )
        self.repository.create_connection_profile(profile)
        return profile

    def check_workspace_health(self, workspace_id: str) -> WorkspaceHealthResult:
        """Check workspace metadata readiness for admin and setup views."""

        self.repository.get_workspace(workspace_id)
        connection_profiles = self.repository.list_connection_profiles(workspace_id)
        graph_profiles = self.repository.list_graph_profiles(workspace_id)
        source_documents = self.repository.list_source_documents(workspace_id)
        requirement_interviews = self.repository.list_requirement_interviews(workspace_id)
        requirement_versions = self.repository.list_requirement_versions(workspace_id)
        workflow_runs = self.repository.list_workflow_runs(workspace_id)
        reports = self.repository.list_report_manifests(workspace_id)

        counts = {
            "connection_profiles": len(connection_profiles),
            "graph_profiles": len(graph_profiles),
            "source_documents": len(source_documents),
            "requirement_interviews": len(requirement_interviews),
            "requirement_versions": len(requirement_versions),
            "workflow_runs": len(workflow_runs),
            "reports": len(reports),
        }
        issues = self._workspace_health_issues(
            connection_profiles=connection_profiles,
            graph_profiles=graph_profiles,
            requirement_versions=requirement_versions,
            workflow_runs=workflow_runs,
            reports=reports,
        )
        status = "healthy" if not issues else "needs_attention"

        return WorkspaceHealthResult(
            workspace_id=workspace_id,
            status=status,
            counts=counts,
            issues=issues,
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

    def create_workflow_run_from_steps(
        self,
        workspace_id: str,
        workflow_mode: WorkflowMode,
        steps: List[WorkflowStep],
        dag_edges: List[WorkflowDAGEdge],
        requirement_version_id: Optional[str] = None,
        graph_profile_id: Optional[str] = None,
        template_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowRun:
        """Create a visualizable workflow run from planned steps and edges."""

        self._validate_workflow_dag(steps, dag_edges)
        run = create_workflow_run(
            workspace_id=workspace_id,
            workflow_mode=workflow_mode,
            status=WorkflowRunStatus.QUEUED,
            requirement_version_id=requirement_version_id,
            graph_profile_id=graph_profile_id,
            template_ids=template_ids or [],
            steps=steps,
            dag_edges=dag_edges,
            metadata=metadata or {},
        )
        self.repository.create_workflow_run(run)
        return run

    def start_workflow_run(self, run_id: str) -> WorkflowRun:
        """Mark a queued workflow run as running."""

        run = self.repository.get_workflow_run(run_id)
        run.status = WorkflowRunStatus.RUNNING
        run.started_at = run.started_at or current_timestamp()
        self.repository.update_workflow_run(run)
        return run

    def update_workflow_step(
        self,
        run_id: str,
        step_id: str,
        status: WorkflowStepStatus,
        outputs: Optional[Dict[str, Any]] = None,
        artifact_refs: Optional[List[Dict[str, str]]] = None,
        warnings: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
        checkpoint_id: Optional[str] = None,
        cost: Optional[Dict[str, Any]] = None,
    ) -> WorkflowStepUpdateResult:
        """Update a workflow step and roll up run status for the visualizer."""

        run = self.repository.get_workflow_run(run_id)
        step = self._find_workflow_step(run, step_id)
        previous_status = step.status
        step.status = status

        if status == WorkflowStepStatus.RUNNING and step.started_at is None:
            step.started_at = current_timestamp()
        if status in {
            WorkflowStepStatus.COMPLETED,
            WorkflowStepStatus.FAILED,
            WorkflowStepStatus.SKIPPED,
        }:
            step.completed_at = current_timestamp()
        if previous_status == WorkflowStepStatus.FAILED and status == WorkflowStepStatus.RUNNING:
            step.retry_count += 1

        if outputs is not None:
            step.outputs = outputs
        if artifact_refs is not None:
            step.artifact_refs = artifact_refs
        if warnings is not None:
            step.warnings = warnings
        if errors is not None:
            step.errors = errors
        if checkpoint_id is not None:
            step.checkpoint_id = checkpoint_id
        if cost is not None:
            step.cost = cost

        self._roll_up_workflow_run_status(run)
        self.repository.update_workflow_run(run)
        return WorkflowStepUpdateResult(
            workflow_run=run.to_dict(),
            dag_view=self.get_workflow_dag_view(run.run_id).to_dict(),
        )

    def supported_workflow_recovery_actions(self, run_id: str) -> Dict[str, List[str]]:
        """Return supported recovery actions keyed by workflow step ID."""

        run = self.repository.get_workflow_run(run_id)
        actions: Dict[str, List[str]] = {}
        for step in run.steps:
            if step.status == WorkflowStepStatus.FAILED:
                actions[step.step_id] = ["retry", "open_logs"]
            elif step.status == WorkflowStepStatus.PAUSED:
                actions[step.step_id] = ["resume", "cancel", "open_logs"]
            else:
                actions[step.step_id] = []
        return actions

    def get_report_bundle(self, report_id: str) -> ReportBundle:
        """Load a full dynamic report payload."""

        manifest = self.repository.get_report_manifest(report_id)
        sections = self.repository.list_report_sections(report_id)
        charts = self.repository.list_chart_specs(report_id)
        snapshots = self.repository.list_published_snapshots(report_id)

        return self._report_bundle(manifest, sections, charts, snapshots)

    def export_report(self, report_id: str, format: str = "html") -> ReportExportResult:
        """Render a report to a downloadable HTML or Markdown document.

        Implements PRD FR-42 / MVP acceptance #14. Returns a
        :class:`ReportExportResult` so the FastAPI adapter can stream the
        bytes back as an attachment with the correct media type rather than
        wrapping them in a JSON envelope.

        Args:
            report_id: Report manifest identifier.
            format: ``"html"`` or ``"markdown"`` (case-insensitive). Anything
                else raises :class:`ValidationError` so callers get a clean
                4xx instead of a server error.
        """

        normalized = (format or "html").lower()
        if normalized not in {"html", "markdown"}:
            raise ValidationError(
                f"Unsupported report export format: {format!r} "
                "(supported: html, markdown)"
            )

        manifest = self.repository.get_report_manifest(report_id)
        sections = self.repository.list_report_sections(report_id)
        charts = self.repository.list_chart_specs(report_id)

        # Sort sections by their ``order`` field so the export reads in the
        # same flow as the canvas. Charts retain insertion order; the report
        # canvas does the same.
        ordered_sections = sorted(sections, key=lambda section: section.order)
        slug = self._slugify(manifest.title) or manifest.report_id
        timestamp = current_timestamp().isoformat()

        if normalized == "markdown":
            content = self._render_report_markdown(
                manifest=manifest,
                sections=ordered_sections,
                charts=charts,
                exported_at=timestamp,
            )
            return ReportExportResult(
                content=content,
                media_type="text/markdown; charset=utf-8",
                filename=f"{slug}.md",
                fmt="markdown",
            )

        content = self._render_report_html(
            manifest=manifest,
            sections=ordered_sections,
            charts=charts,
            exported_at=timestamp,
        )
        return ReportExportResult(
            content=content,
            media_type="text/html; charset=utf-8",
            filename=f"{slug}.html",
            fmt="html",
        )

    @staticmethod
    def _slugify(value: str) -> str:
        """Lowercase, replace runs of non-alphanumerics with single ``-``."""

        cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value or "").strip("-").lower()
        return cleaned[:80]

    @staticmethod
    def _section_text(section: ReportSection) -> str:
        """Best-effort plain text for a section's content payload.

        Sections are stored as free-form dicts. The most common shape is
        ``{"text": "..."}`` (markdown body); fall back to a JSON dump so
        unknown shapes are still inspectable rather than silently dropped.
        """

        text = section.content.get("text") if isinstance(section.content, dict) else None
        if isinstance(text, str) and text.strip():
            return text
        if not section.content:
            return ""
        try:
            return json.dumps(section.content, indent=2, default=str)
        except (TypeError, ValueError):
            return repr(section.content)

    def _render_report_markdown(
        self,
        *,
        manifest: ReportManifest,
        sections: List[ReportSection],
        charts: List[ChartSpec],
        exported_at: str,
    ) -> str:
        lines: List[str] = []
        lines.append(f"# {manifest.title}")
        lines.append("")
        status_value = getattr(manifest.status, "value", manifest.status)
        lines.append(
            f"*Report v{manifest.version} · status: {status_value} · "
            f"exported {exported_at}*"
        )
        lines.append("")
        if manifest.summary:
            lines.append(manifest.summary)
            lines.append("")

        if sections:
            lines.append("## Sections")
            lines.append("")
            for section in sections:
                lines.append(f"### {section.title}")
                lines.append("")
                section_type = getattr(section.type, "value", section.type)
                lines.append(f"_{section_type}_")
                lines.append("")
                body = self._section_text(section)
                if body:
                    lines.append(body)
                    lines.append("")
                if section.evidence_refs:
                    lines.append(
                        f"_{len(section.evidence_refs)} evidence reference(s)._"
                    )
                    lines.append("")

        if charts:
            lines.append("## Charts")
            lines.append("")
            for chart in charts:
                chart_type = getattr(chart.chart_type, "value", chart.chart_type)
                lines.append(
                    f"- **{chart.title}** — `{chart_type}` "
                    f"(data source: `{chart.data_source}`)"
                )
            lines.append("")

        # PRD FR-44 lineage: include any populated lineage refs so the export
        # is auditable on its own (no need to cross-reference the live UI).
        lineage_lines: List[str] = []
        if manifest.run_id:
            lineage_lines.append(f"- Run: `{manifest.run_id}`")
        if manifest.workspace_id:
            lineage_lines.append(f"- Workspace: `{manifest.workspace_id}`")
        if manifest.requirement_version_id:
            lineage_lines.append(
                f"- Requirement version: `{manifest.requirement_version_id}`"
            )
        for use_case_id in manifest.use_case_ids:
            lineage_lines.append(f"- Use case: `{use_case_id}`")
        for template_id in manifest.template_ids:
            lineage_lines.append(f"- Template: `{template_id}`")
        for execution_id in manifest.analysis_execution_ids:
            lineage_lines.append(f"- Execution: `{execution_id}`")
        for collection in manifest.result_collections:
            lineage_lines.append(f"- Result collection: `{collection}`")

        if lineage_lines:
            lines.append("## Lineage")
            lines.append("")
            lines.extend(lineage_lines)
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def _render_report_html(
        self,
        *,
        manifest: ReportManifest,
        sections: List[ReportSection],
        charts: List[ChartSpec],
        exported_at: str,
    ) -> str:
        # Self-contained HTML doc — inline minimal CSS so the export is
        # readable in any browser without external assets. User content is
        # always escaped via :func:`html.escape` (see calls below) to prevent
        # injection through report titles or sections.
        title_html = html.escape(manifest.title or manifest.report_id)
        status_value = getattr(manifest.status, "value", manifest.status)
        meta_html = html.escape(
            f"Report v{manifest.version} · status: {status_value} · "
            f"exported {exported_at}"
        )

        body_parts: List[str] = []
        body_parts.append(f"<h1>{title_html}</h1>")
        body_parts.append(f'<p class="meta">{meta_html}</p>')
        if manifest.summary:
            body_parts.append(f"<p>{html.escape(manifest.summary)}</p>")

        if sections:
            body_parts.append("<h2>Sections</h2>")
            for section in sections:
                section_type = getattr(section.type, "value", section.type)
                body_parts.append(
                    f'<section class="report-section">'
                    f"<h3>{html.escape(section.title)}</h3>"
                    f'<p class="muted">{html.escape(str(section_type))}</p>'
                )
                body = self._section_text(section)
                if body:
                    body_parts.append(f"<pre>{html.escape(body)}</pre>")
                if section.evidence_refs:
                    body_parts.append(
                        f'<p class="muted">{len(section.evidence_refs)} '
                        f"evidence reference(s).</p>"
                    )
                body_parts.append("</section>")

        if charts:
            body_parts.append("<h2>Charts</h2><ul>")
            for chart in charts:
                chart_type = getattr(chart.chart_type, "value", chart.chart_type)
                body_parts.append(
                    "<li>"
                    f"<strong>{html.escape(chart.title)}</strong> — "
                    f"<code>{html.escape(str(chart_type))}</code> "
                    f"(data source: <code>{html.escape(chart.data_source)}</code>)"
                    "</li>"
                )
            body_parts.append("</ul>")

        lineage_items: List[str] = []
        if manifest.run_id:
            lineage_items.append(f"<li>Run: <code>{html.escape(manifest.run_id)}</code></li>")
        if manifest.workspace_id:
            lineage_items.append(
                f"<li>Workspace: <code>{html.escape(manifest.workspace_id)}</code></li>"
            )
        if manifest.requirement_version_id:
            lineage_items.append(
                "<li>Requirement version: "
                f"<code>{html.escape(manifest.requirement_version_id)}</code></li>"
            )
        for use_case_id in manifest.use_case_ids:
            lineage_items.append(f"<li>Use case: <code>{html.escape(use_case_id)}</code></li>")
        for template_id in manifest.template_ids:
            lineage_items.append(f"<li>Template: <code>{html.escape(template_id)}</code></li>")
        for execution_id in manifest.analysis_execution_ids:
            lineage_items.append(f"<li>Execution: <code>{html.escape(execution_id)}</code></li>")
        for collection in manifest.result_collections:
            lineage_items.append(
                f"<li>Result collection: <code>{html.escape(collection)}</code></li>"
            )
        if lineage_items:
            body_parts.append("<h2>Lineage</h2><ul>")
            body_parts.extend(lineage_items)
            body_parts.append("</ul>")

        style = (
            "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
            "max-width:880px;margin:32px auto;padding:0 24px;color:#222;line-height:1.5;}"
            "h1{margin-bottom:4px;}"
            ".meta{color:#666;font-size:0.9em;margin-top:0;}"
            ".muted{color:#888;font-size:0.85em;}"
            ".report-section{border-top:1px solid #eee;padding-top:16px;margin-top:16px;}"
            "pre{background:#f6f8fa;padding:12px;border-radius:6px;overflow-x:auto;white-space:pre-wrap;}"
            "code{background:#f6f8fa;padding:1px 4px;border-radius:3px;font-size:0.9em;}"
            "ul{padding-left:20px;}"
        )

        return (
            "<!DOCTYPE html>\n"
            "<html lang=\"en\"><head>"
            f'<meta charset="utf-8"/><title>{title_html}</title>'
            f"<style>{style}</style>"
            "</head><body>"
            + "".join(body_parts)
            + "</body></html>"
        )

    def verify_connection_profile(
        self,
        connection_profile_id: str,
        password_secret_key: str = "password",
        verify_system: bool = True,
    ) -> ConnectionVerificationResult:
        """Resolve a profile password and test its ArangoDB connection."""

        profile = self.repository.get_connection_profile(connection_profile_id)
        password_ref = profile.secret_refs.get(password_secret_key)
        if not password_ref:
            raise ValidationError(
                f"Connection profile is missing secret ref: {password_secret_key}"
            )

        password = self.secret_resolver.resolve(password_ref)
        verified_at = current_timestamp()

        try:
            self.db_connector(
                endpoint=profile.endpoint,
                username=profile.username,
                password=password,
                database=profile.database,
                verify_ssl=profile.verify_ssl,
                verify_system=verify_system,
            )
        except Exception as exc:
            profile.last_verified_at = verified_at
            profile.last_verification_status = ConnectionVerificationStatus.FAILED
            self.repository.update_connection_profile(profile)
            return ConnectionVerificationResult(
                connection_profile_id=profile.connection_profile_id,
                workspace_id=profile.workspace_id,
                status=ConnectionVerificationStatus.FAILED.value,
                verified_at=verified_at.isoformat(),
                endpoint=profile.endpoint,
                database=profile.database,
                error_message=self._mask_secret(str(exc), password),
            )

        profile.last_verified_at = verified_at
        profile.last_verification_status = ConnectionVerificationStatus.SUCCESS
        self.repository.update_connection_profile(profile)
        return ConnectionVerificationResult(
            connection_profile_id=profile.connection_profile_id,
            workspace_id=profile.workspace_id,
            status=ConnectionVerificationStatus.SUCCESS.value,
            verified_at=verified_at.isoformat(),
            endpoint=profile.endpoint,
            database=profile.database,
        )

    def list_connection_profile_graphs(
        self,
        connection_profile_id: str,
        password_secret_key: str = "password",
        verify_system: bool = True,
        include_system: bool = False,
        include_counts: bool = True,
    ) -> ConnectionGraphsResult:
        """Enumerate named graphs available on a connection profile."""

        profile = self.repository.get_connection_profile(connection_profile_id)
        password_ref = profile.secret_refs.get(password_secret_key)
        if not password_ref:
            raise ValidationError(
                f"Connection profile is missing secret ref: {password_secret_key}"
            )

        password = self.secret_resolver.resolve(password_ref)
        db = self.db_connector(
            endpoint=profile.endpoint,
            username=profile.username,
            password=password,
            database=profile.database,
            verify_ssl=profile.verify_ssl,
            verify_system=verify_system,
        )

        try:
            raw_graphs = list(db.graphs() or [])
        except Exception as exc:  # pragma: no cover - depends on driver
            raise ValidationError(
                f"Failed to enumerate graphs on '{profile.database}': {exc}"
            ) from exc

        summaries: List[ConnectionGraphSummary] = []
        for raw in raw_graphs:
            name = raw.get("name") or ""
            if not name:
                continue
            is_system = name.startswith("_")
            if is_system and not include_system:
                continue
            edge_definitions = list(raw.get("edge_definitions") or [])
            orphan_collections = list(raw.get("orphan_collections") or [])
            vertex_collections, edge_collections = _collections_from_edge_definitions(
                edge_definitions, orphan_collections
            )

            vertex_count: Optional[int] = None
            edge_count: Optional[int] = None
            if include_counts:
                vertex_count = _safe_collection_total(db, vertex_collections)
                edge_count = _safe_collection_total(db, edge_collections)

            summaries.append(
                ConnectionGraphSummary(
                    name=name,
                    is_system=is_system,
                    vertex_collections=vertex_collections,
                    edge_collections=edge_collections,
                    orphan_collections=orphan_collections,
                    edge_definitions=edge_definitions,
                    vertex_count=vertex_count,
                    edge_count=edge_count,
                )
            )

        summaries.sort(key=lambda graph: (graph.is_system, graph.name.lower()))

        return ConnectionGraphsResult(
            connection_profile_id=profile.connection_profile_id,
            workspace_id=profile.workspace_id,
            database=profile.database,
            graphs=summaries,
        )

    def discover_graph_profile(
        self,
        connection_profile_id: str,
        graph_name: Optional[str] = None,
        created_by: Optional[str] = None,
        password_secret_key: str = "password",
        sample_size: int = 100,
        max_samples_per_collection: int = 3,
        verify_system: bool = True,
    ) -> GraphDiscoveryResult:
        """Discover graph schema from a connection profile and persist it."""

        profile = self.repository.get_connection_profile(connection_profile_id)
        password_ref = profile.secret_refs.get(password_secret_key)
        if not password_ref:
            raise ValidationError(
                f"Connection profile is missing secret ref: {password_secret_key}"
            )

        password = self.secret_resolver.resolve(password_ref)
        db = self.db_connector(
            endpoint=profile.endpoint,
            username=profile.username,
            password=password,
            database=profile.database,
            verify_ssl=profile.verify_ssl,
            verify_system=verify_system,
        )
        extractor = self.schema_extractor_factory(
            db,
            sample_size=sample_size,
            max_samples_per_collection=max_samples_per_collection,
        )
        schema = extractor.extract()

        selected_graph_name = self._select_graph_name(schema, graph_name, profile.database)

        graph_scope = self._scope_to_named_graph(db, schema, selected_graph_name)
        scoped_vertex_collections = sorted(graph_scope["vertex_collections"])
        scoped_edge_collections = sorted(graph_scope["edge_collections"])
        scoped_edge_definitions = (
            graph_scope["edge_definitions"]
            or self._schema_edge_definitions(schema)
        )
        scoped_counts: Dict[str, int] = {
            "vertex_collections": len(scoped_vertex_collections),
            "edge_collections": len(scoped_edge_collections),
            "document_collections": len(schema.document_collections),
            "total_documents": graph_scope.get(
                "total_documents", schema.total_documents
            ),
            "total_edges": graph_scope.get("total_edges", schema.total_edges),
            "relationships": len(scoped_edge_definitions),
        }

        graph_profile = create_graph_profile(
            workspace_id=profile.workspace_id,
            connection_profile_id=profile.connection_profile_id,
            graph_name=selected_graph_name,
            vertex_collections=scoped_vertex_collections,
            edge_collections=scoped_edge_collections,
            edge_definitions=scoped_edge_definitions,
            counts=scoped_counts,
            created_by=created_by,
            metadata={
                "database": schema.database_name,
                "available_graphs": schema.graph_names,
                "scope": graph_scope.get("scope", "named_graph"),
                "schema_summary": schema.to_summary_dict(),
                "discovered_at": current_timestamp().isoformat(),
            },
        )
        self.repository.create_graph_profile(graph_profile)

        return GraphDiscoveryResult(
            graph_profile=graph_profile.to_dict(),
            schema_summary=schema.to_summary_dict(),
        )

    def start_requirements_copilot(
        self,
        graph_profile_id: str,
        domain: Optional[str] = None,
        created_by: Optional[str] = None,
        based_on_version_id: Optional[str] = None,
    ) -> RequirementInterview:
        """Start a schema-aware Requirements Copilot interview.

        When ``based_on_version_id`` is provided, the new interview is
        pre-populated with synthesised answers derived from that version's
        summary / objectives / requirements / constraints, so the user is
        revising rather than retyping. The new interview is still tied to a
        fresh ``requirement_interview_id``; on approve, a new
        ``RequirementVersion`` is created and any prior APPROVED versions in
        the same workspace are flipped to ``SUPERSEDED``.
        """

        graph_profile = self.repository.get_graph_profile(graph_profile_id)
        schema_observations = self._schema_observations_from_graph_profile(graph_profile)
        questions = self._requirements_copilot_questions(schema_observations)

        prefilled_answers: List[Dict[str, Any]] = []
        prior_version_metadata: Dict[str, Any] = {}
        if based_on_version_id:
            prior = self.repository.get_requirement_version(based_on_version_id)
            if prior.workspace_id != graph_profile.workspace_id:
                raise ValidationError(
                    "based_on_version_id must belong to the same workspace as the graph profile"
                )
            prefilled_answers = self._prefill_answers_from_version(prior, questions)
            prior_version_metadata = {
                "based_on_version_id": prior.requirement_version_id,
                "based_on_version": prior.version,
            }
            # Inherit the prior version's domain when the caller didn't pass
            # one explicitly. The approve flow stamps `metadata["domain"]` onto
            # each new version, so this chains forward across v1 → v2 → vN
            # without the user retyping "AdTech" every time.
            if domain is None:
                prior_domain = prior.metadata.get("domain") if prior.metadata else None
                if isinstance(prior_domain, str) and prior_domain.strip():
                    domain = prior_domain

        metadata: Dict[str, Any] = {}
        if created_by:
            metadata["created_by"] = created_by
        metadata.update(prior_version_metadata)

        interview = create_requirement_interview(
            workspace_id=graph_profile.workspace_id,
            graph_profile_id=graph_profile.graph_profile_id,
            domain=domain,
            questions=questions,
            schema_observations=schema_observations,
            answers=prefilled_answers,
            metadata=metadata,
        )
        self.repository.create_requirement_interview(interview)
        return interview

    def _prefill_answers_from_version(
        self,
        version: RequirementVersion,
        questions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Synthesise interview answers from a prior approved RequirementVersion.

        Maps the structured fields of the prior version back onto the
        question_ids the copilot will ask, so users see their previous answers
        already filled in (and editable) rather than starting from a blank
        interview.
        """

        def _items_to_text(items: List[Dict[str, Any]]) -> str:
            # Items can come in two shapes:
            #   - Copilot-derived: {"id", "text", "source"}
            #   - BRD-imported:    {"id", "title", "description", "priority"}
            # Prefer the most descriptive field available, then fall back.
            lines: List[str] = []
            for item in items:
                text = str(item.get("text") or "").strip()
                title = str(item.get("title") or "").strip()
                description = str(item.get("description") or "").strip()
                if text:
                    lines.append(f"- {text}")
                elif title and description and title != description:
                    lines.append(f"- {title}: {description}")
                elif title:
                    lines.append(f"- {title}")
                elif description:
                    lines.append(f"- {description}")
            return "\n".join(lines)

        synthesised: Dict[str, str] = {
            "business_goal": (version.summary or "").strip(),
            "analytics_questions": _items_to_text(version.requirements),
            "constraints": _items_to_text(version.constraints),
        }
        # Some deployments may add extra question_ids; we only pre-fill the
        # ones we recognise to avoid leaking stale text into unrelated fields.
        valid_ids = {str(q.get("id")) for q in questions if q.get("id")}
        timestamp = current_timestamp().isoformat()
        return [
            {
                "question_id": qid,
                "answer": text,
                "actor": "system:prefilled-from-version",
                "answered_at": timestamp,
            }
            for qid, text in synthesised.items()
            if qid in valid_ids and text
        ]

    def answer_requirements_copilot_question(
        self,
        requirement_interview_id: str,
        question_id: str,
        answer: str,
        actor: Optional[str] = None,
    ) -> RequirementInterview:
        """Record or replace an answer in a Requirements Copilot session."""

        interview = self.repository.get_requirement_interview(requirement_interview_id)
        answers = [
            existing
            for existing in interview.answers
            if existing.get("question_id") != question_id
        ]
        answers.append(
            {
                "question_id": question_id,
                "answer": answer,
                "actor": actor,
                "answered_at": current_timestamp().isoformat(),
            }
        )
        interview.answers = answers
        self.repository.update_requirement_interview(interview)
        return interview

    def generate_requirements_copilot_draft(
        self,
        requirement_interview_id: str,
    ) -> RequirementsDraftResult:
        """Generate a deterministic BRD draft from schema observations and answers."""

        interview = self.repository.get_requirement_interview(requirement_interview_id)
        answer_map = {
            answer["question_id"]: answer.get("answer", "")
            for answer in interview.answers
        }
        draft_brd = self._build_requirements_draft(interview, answer_map)
        provenance_labels = self._build_requirements_provenance(interview, answer_map)

        interview.draft_brd = draft_brd
        interview.provenance_labels = provenance_labels
        interview.status = RequirementInterviewStatus.READY_FOR_REVIEW
        self.repository.update_requirement_interview(interview)

        return RequirementsDraftResult(
            requirement_interview=interview.to_dict(),
            draft_brd=draft_brd,
            provenance_labels=provenance_labels,
        )

    def approve_requirements_copilot_draft(
        self,
        requirement_interview_id: str,
        version: Optional[int] = None,
        approved_by: Optional[str] = None,
    ) -> RequirementVersion:
        """Approve a generated BRD draft into a requirement version.

        Behaviour:
        - If ``version`` is omitted, the next version number is computed as
          ``max(existing.version) + 1`` for the workspace (or 1 if none).
        - If ``version`` is provided AND collides with an existing version
          number for this workspace, ``ValidationError`` is raised; pass
          ``None`` (or omit) to take the auto-incremented value.
        - All currently APPROVED versions in the workspace are flipped to
          ``SUPERSEDED`` so there is always exactly one active version.
        """

        interview = self.repository.get_requirement_interview(requirement_interview_id)
        if not interview.draft_brd:
            raise ValidationError("Requirements Copilot draft must be generated first")

        existing_versions = self.repository.list_requirement_versions(
            interview.workspace_id
        )
        existing_numbers = {prior.version for prior in existing_versions}

        if version is None:
            next_version = max(existing_numbers, default=0) + 1
        else:
            if version in existing_numbers:
                raise ValidationError(
                    f"RequirementVersion v{version} already exists in this workspace; "
                    "omit the 'version' field to auto-increment."
                )
            next_version = version

        prior_version_metadata: Dict[str, Any] = {}
        if interview.metadata:
            for key in ("based_on_version_id", "based_on_version"):
                if interview.metadata.get(key) is not None:
                    prior_version_metadata[key] = interview.metadata[key]

        requirement_version = create_requirement_version(
            workspace_id=interview.workspace_id,
            version=next_version,
            status=RequirementVersionStatus.APPROVED,
            requirement_interview_id=interview.requirement_interview_id,
            summary=self._answer_for_question(interview, "business_goal")
            or "Requirements Copilot approved draft",
            objectives=self._requirement_items_from_answer(
                interview,
                "business_goal",
                prefix="OBJ",
            ),
            requirements=self._requirement_items_from_answer(
                interview,
                "analytics_questions",
                prefix="REQ",
            ),
            constraints=self._requirement_items_from_answer(
                interview,
                "constraints",
                prefix="CON",
            ),
            approved_at=current_timestamp(),
            metadata={
                "approved_by": approved_by,
                "source": "requirements_copilot",
                "draft_brd": interview.draft_brd,
                "provenance_labels": interview.provenance_labels,
                # Persist the interview's domain on the version so a later
                # "Reopen Copilot to Produce v(N+1)" can pre-fill the Domain
                # field instead of asking the user to retype it.
                **({"domain": interview.domain} if interview.domain else {}),
                **prior_version_metadata,
            },
        )
        self.repository.create_requirement_version(requirement_version)

        # Flip any prior APPROVED versions to SUPERSEDED so the workspace has
        # exactly one active set of requirements.
        for prior in existing_versions:
            if prior.status is RequirementVersionStatus.APPROVED:
                prior.status = RequirementVersionStatus.SUPERSEDED
                prior.metadata = {
                    **(prior.metadata or {}),
                    "superseded_by": requirement_version.requirement_version_id,
                    "superseded_at": current_timestamp().isoformat(),
                }
                self.repository.update_requirement_version(prior)

        interview.status = RequirementInterviewStatus.APPROVED
        self.repository.update_requirement_interview(interview)
        return requirement_version

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

    def import_workspace_bundle(
        self,
        bundle: WorkspaceBundle | Dict[str, Any],
        include_audit_events: bool = False,
    ) -> WorkspaceImportResult:
        """Import a workspace bundle after validating shape and secret handling."""

        bundle_doc = bundle.to_dict() if isinstance(bundle, WorkspaceBundle) else bundle
        self._validate_workspace_bundle(bundle_doc)

        workspace = Workspace.from_dict(bundle_doc["workspace"])
        self.repository.create_workspace(workspace)

        connection_profiles = [
            ConnectionProfile.from_dict(profile)
            for profile in bundle_doc.get("connection_profiles", [])
        ]
        graph_profiles = [
            GraphProfile.from_dict(profile)
            for profile in bundle_doc.get("graph_profiles", [])
        ]
        source_documents = [
            SourceDocument.from_dict(document)
            for document in bundle_doc.get("source_documents", [])
        ]
        requirement_interviews = [
            RequirementInterview.from_dict(interview)
            for interview in bundle_doc.get("requirement_interviews", [])
        ]
        requirement_versions = [
            RequirementVersion.from_dict(version)
            for version in bundle_doc.get("requirement_versions", [])
        ]
        workflow_runs = [
            WorkflowRun.from_dict(run)
            for run in bundle_doc.get("workflow_runs", [])
        ]

        for profile in connection_profiles:
            self.repository.create_connection_profile(profile)
        for profile in graph_profiles:
            self.repository.create_graph_profile(profile)
        for document in source_documents:
            self.repository.create_source_document(document)
        for interview in requirement_interviews:
            self.repository.create_requirement_interview(interview)
        for version in requirement_versions:
            self.repository.create_requirement_version(version)
        for run in workflow_runs:
            self.repository.create_workflow_run(run)

        report_count = 0
        section_count = 0
        chart_count = 0
        snapshot_count = 0
        for report_doc in bundle_doc.get("reports", []):
            manifest = ReportManifest.from_dict(report_doc["manifest"])
            self.repository.create_report_manifest(manifest)
            report_count += 1

            for section_doc in report_doc.get("sections", []):
                self.repository.create_report_section(ReportSection.from_dict(section_doc))
                section_count += 1
            for chart_doc in report_doc.get("charts", []):
                self.repository.create_chart_spec(ChartSpec.from_dict(chart_doc))
                chart_count += 1
            for snapshot_doc in report_doc.get("snapshots", []):
                self.repository.create_published_snapshot(
                    PublishedSnapshot.from_dict(snapshot_doc)
                )
                snapshot_count += 1

        audit_count = 0
        if include_audit_events:
            for event_doc in bundle_doc.get("audit_events", []):
                self.repository.create_audit_event(AuditEvent.from_dict(event_doc))
                audit_count += 1

        return WorkspaceImportResult(
            workspace_id=workspace.workspace_id,
            counts={
                "connection_profiles": len(connection_profiles),
                "graph_profiles": len(graph_profiles),
                "source_documents": len(source_documents),
                "requirement_interviews": len(requirement_interviews),
                "requirement_versions": len(requirement_versions),
                "workflow_runs": len(workflow_runs),
                "reports": report_count,
                "report_sections": section_count,
                "chart_specs": chart_count,
                "published_snapshots": snapshot_count,
                "audit_events": audit_count,
            },
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

    def _validate_workflow_dag(
        self,
        steps: List[WorkflowStep],
        dag_edges: List[WorkflowDAGEdge],
    ) -> None:
        step_ids = {step.step_id for step in steps}
        if len(step_ids) != len(steps):
            raise ValidationError("Workflow steps must have unique step_id values")
        for edge in dag_edges:
            if edge.from_step_id not in step_ids:
                raise ValidationError(
                    f"Workflow edge references missing from_step_id: {edge.from_step_id}"
                )
            if edge.to_step_id not in step_ids:
                raise ValidationError(
                    f"Workflow edge references missing to_step_id: {edge.to_step_id}"
                )

    def _find_workflow_step(self, run: WorkflowRun, step_id: str) -> WorkflowStep:
        for step in run.steps:
            if step.step_id == step_id:
                return step
        raise ValidationError(f"Workflow step not found: {step_id}")

    def _roll_up_workflow_run_status(self, run: WorkflowRun) -> None:
        statuses = [step.status for step in run.steps]
        if any(status == WorkflowStepStatus.FAILED for status in statuses):
            run.status = WorkflowRunStatus.FAILED
            run.completed_at = current_timestamp()
        elif any(status == WorkflowStepStatus.PAUSED for status in statuses):
            run.status = WorkflowRunStatus.PAUSED
        elif statuses and all(
            status in {WorkflowStepStatus.COMPLETED, WorkflowStepStatus.SKIPPED}
            for status in statuses
        ):
            run.status = WorkflowRunStatus.COMPLETED
            run.completed_at = current_timestamp()
        elif any(status == WorkflowStepStatus.RUNNING for status in statuses):
            run.status = WorkflowRunStatus.RUNNING
            run.started_at = run.started_at or current_timestamp()
        else:
            run.status = WorkflowRunStatus.QUEUED

    def _export_connection_profile(
        self,
        profile: ConnectionProfile,
    ) -> Dict[str, Any]:
        doc = profile.to_dict()
        secret_ref_keys = sorted(doc.get("secret_refs", {}).keys())
        doc.pop("secret_refs", None)
        doc["secret_ref_keys"] = secret_ref_keys
        return doc

    def _validate_workspace_bundle(self, bundle_doc: Dict[str, Any]) -> None:
        required_keys = {
            "schema_version",
            "workspace",
            "connection_profiles",
            "graph_profiles",
            "source_documents",
            "requirement_interviews",
            "requirement_versions",
            "workflow_runs",
            "reports",
        }
        missing = sorted(required_keys - set(bundle_doc.keys()))
        if missing:
            raise ValidationError(
                f"Workspace bundle is missing required keys: {', '.join(missing)}"
            )

        if bundle_doc["schema_version"] != PRODUCT_SCHEMA_VERSION:
            raise ValidationError(
                "Unsupported workspace bundle schema version: "
                f"{bundle_doc['schema_version']}"
            )

        workspace_id = bundle_doc["workspace"].get("workspace_id") or bundle_doc[
            "workspace"
        ].get("_key")
        if not workspace_id:
            raise ValidationError("Workspace bundle is missing workspace_id")

        for profile in bundle_doc.get("connection_profiles", []):
            if "secret_refs" in profile:
                raise ValidationError(
                    "Workspace bundle imports must not include connection secret_refs"
                )

        for collection_name in [
            "connection_profiles",
            "graph_profiles",
            "source_documents",
            "requirement_interviews",
            "requirement_versions",
            "workflow_runs",
        ]:
            for item in bundle_doc.get(collection_name, []):
                self._validate_workspace_id(collection_name, item, workspace_id)

        for report in bundle_doc.get("reports", []):
            if "manifest" not in report:
                raise ValidationError("Workspace bundle report is missing manifest")
            self._validate_workspace_id("reports.manifest", report["manifest"], workspace_id)
            for section in report.get("sections", []):
                self._validate_workspace_id("reports.sections", section, workspace_id)
            for chart in report.get("charts", []):
                self._validate_workspace_id("reports.charts", chart, workspace_id)
            for snapshot in report.get("snapshots", []):
                self._validate_workspace_id("reports.snapshots", snapshot, workspace_id)

        for event in bundle_doc.get("audit_events", []):
            self._validate_workspace_id("audit_events", event, workspace_id)

    def _validate_workspace_id(
        self,
        collection_name: str,
        item: Dict[str, Any],
        workspace_id: str,
    ) -> None:
        item_workspace_id = item.get("workspace_id")
        if item_workspace_id != workspace_id:
            raise ValidationError(
                f"Workspace bundle item in {collection_name} has mismatched "
                f"workspace_id: {item_workspace_id}"
            )

    def _mask_secret(self, message: str, secret_value: str) -> str:
        if not secret_value:
            return message
        return message.replace(secret_value, "***MASKED***")

    def _select_graph_name(
        self,
        schema: GraphSchema,
        requested_graph_name: Optional[str],
        fallback_name: str,
    ) -> str:
        if requested_graph_name:
            if schema.graph_names and requested_graph_name not in schema.graph_names:
                raise ValidationError(
                    f"Graph '{requested_graph_name}' was not found in database"
                )
            return requested_graph_name
        if schema.graph_names:
            return schema.graph_names[0]
        return fallback_name

    def _schema_edge_definitions(self, schema: GraphSchema) -> List[Dict[str, Any]]:
        definitions = []
        for relationship in schema.relationships:
            definitions.append(
                {
                    "edge_collection": relationship.edge_collection,
                    "from_vertex_collections": [relationship.from_collection],
                    "to_vertex_collections": [relationship.to_collection],
                    "edge_count": relationship.edge_count,
                    "relationship_type": relationship.relationship_type,
                }
            )
        return definitions

    def _scope_to_named_graph(
        self,
        db: Any,
        schema: GraphSchema,
        graph_name: str,
    ) -> Dict[str, Any]:
        """Resolve the vertex/edge collections for a named graph.

        Falls back to the full schema if the graph is the database name (no real
        named graph) or if the driver cannot fetch graph metadata.
        """

        scope: Dict[str, Any] = {
            "vertex_collections": list(schema.vertex_collections.keys()),
            "edge_collections": list(schema.edge_collections.keys()),
            "edge_definitions": [],
            "scope": "database",
            "total_documents": schema.total_documents,
            "total_edges": schema.total_edges,
        }

        if not graph_name or graph_name not in (schema.graph_names or []):
            return scope

        try:
            graph_handle = db.graph(graph_name)
            edge_definitions = list(graph_handle.edge_definitions() or [])
        except Exception:
            return scope

        try:
            orphan_collections = list(graph_handle.orphan_collections() or [])
        except Exception:
            orphan_collections = []

        vertex_collections, edge_collections = _collections_from_edge_definitions(
            edge_definitions, orphan_collections
        )
        if not vertex_collections and not edge_collections:
            return scope

        total_documents = _safe_collection_total(db, vertex_collections)
        total_edges = _safe_collection_total(db, edge_collections)

        scope.update(
            {
                "vertex_collections": vertex_collections,
                "edge_collections": edge_collections,
                "edge_definitions": edge_definitions,
                "scope": "named_graph",
                "total_documents": (
                    total_documents if total_documents is not None else 0
                )
                + sum(
                    schema.document_collections[name].document_count
                    for name in schema.document_collections
                    if name in orphan_collections
                ),
                "total_edges": total_edges if total_edges is not None else 0,
            }
        )
        return scope

    def _workspace_health_issues(
        self,
        connection_profiles: List[ConnectionProfile],
        graph_profiles: List[GraphProfile],
        requirement_versions: List[RequirementVersion],
        workflow_runs: List[WorkflowRun],
        reports: List[ReportManifest],
    ) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        if not connection_profiles:
            issues.append(
                {
                    "severity": "warning",
                    "code": "missing_connection_profile",
                    "message": "Workspace has no connection profiles.",
                }
            )
        if not graph_profiles:
            issues.append(
                {
                    "severity": "warning",
                    "code": "missing_graph_profile",
                    "message": "Workspace has no discovered graph profiles.",
                }
            )
        if not requirement_versions:
            issues.append(
                {
                    "severity": "info",
                    "code": "missing_requirement_version",
                    "message": "Workspace has no approved or draft requirement versions.",
                }
            )

        failed_connections = [
            profile.connection_profile_id
            for profile in connection_profiles
            if profile.last_verification_status == ConnectionVerificationStatus.FAILED
        ]
        if failed_connections:
            issues.append(
                {
                    "severity": "error",
                    "code": "failed_connection_verification",
                    "message": "One or more connection profiles failed verification.",
                    "entity_ids": failed_connections,
                }
            )

        failed_runs = [
            run.run_id
            for run in workflow_runs
            if run.status == WorkflowRunStatus.FAILED
        ]
        if failed_runs:
            issues.append(
                {
                    "severity": "warning",
                    "code": "failed_workflow_runs",
                    "message": "One or more workflow runs failed.",
                    "entity_ids": failed_runs,
                }
            )

        draft_reports = [
            report.report_id
            for report in reports
            if report.status == ReportStatus.DRAFT
        ]
        if draft_reports:
            issues.append(
                {
                    "severity": "info",
                    "code": "draft_reports",
                    "message": "Workspace has draft reports that are not published.",
                    "entity_ids": draft_reports,
                }
            )
        return issues

    def _schema_observations_from_graph_profile(
        self,
        graph_profile: GraphProfile,
    ) -> Dict[str, Any]:
        return {
            "graph_name": graph_profile.graph_name,
            "vertex_collections": graph_profile.vertex_collections,
            "edge_collections": graph_profile.edge_collections,
            "edge_definitions": graph_profile.edge_definitions,
            "collection_roles": graph_profile.collection_roles,
            "counts": graph_profile.counts,
            "schema_summary": graph_profile.metadata.get("schema_summary", {}),
        }

    def _requirements_copilot_questions(
        self,
        schema_observations: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        graph_name = schema_observations.get("graph_name", "the graph")
        return [
            {
                "id": "business_goal",
                "text": f"What business decision should {graph_name} support?",
                "provenance": "user_provided",
            },
            {
                "id": "analytics_questions",
                "text": "What graph analytics questions should the system answer?",
                "provenance": "user_provided",
            },
            {
                "id": "audience",
                "text": "Who will consume the report and what level of detail do they need?",
                "provenance": "user_provided",
            },
            {
                "id": "constraints",
                "text": "What runtime, cost, freshness, sensitivity, or evidence constraints apply?",
                "provenance": "user_provided",
            },
        ]

    def _build_requirements_draft(
        self,
        interview: RequirementInterview,
        answer_map: Dict[str, str],
    ) -> str:
        observations = interview.schema_observations
        vertex_collections = ", ".join(observations.get("vertex_collections", [])) or "None observed"
        edge_collections = ", ".join(observations.get("edge_collections", [])) or "None observed"
        domain = interview.domain or "Unspecified domain"

        return "\n".join(
            [
                "# Business Requirements Draft",
                "",
                f"## Domain",
                domain,
                "",
                "## Observed Graph Schema",
                f"- Graph: {observations.get('graph_name', interview.graph_profile_id)}",
                f"- Vertex collections: {vertex_collections}",
                f"- Edge collections: {edge_collections}",
                f"- Counts: {json.dumps(observations.get('counts', {}), sort_keys=True)}",
                "",
                "## Business Goal",
                answer_map.get("business_goal", "[Needs user input]"),
                "",
                "## Analytics Questions",
                answer_map.get("analytics_questions", "[Needs user input]"),
                "",
                "## Reporting Audience",
                answer_map.get("audience", "[Needs user input]"),
                "",
                "## Constraints",
                answer_map.get("constraints", "[Needs user input]"),
                "",
                "## Assumptions To Confirm",
                "- Generated requirements should be reviewed before use-case or template generation.",
                "- Graph schema observations may need business terminology refinement.",
            ]
        )

    def _build_requirements_provenance(
        self,
        interview: RequirementInterview,
        answer_map: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        labels = [
            {"path": "observed_schema.graph_name", "label": "observed_from_schema"},
            {"path": "observed_schema.vertex_collections", "label": "observed_from_schema"},
            {"path": "observed_schema.edge_collections", "label": "observed_from_schema"},
            {"path": "assumptions.review_required", "label": "assumption"},
        ]
        for question_id in sorted(answer_map):
            labels.append(
                {
                    "path": f"answers.{question_id}",
                    "label": "user_provided",
                }
            )
        if interview.domain:
            labels.append({"path": "domain", "label": "user_provided"})
        return labels

    def _answer_for_question(
        self,
        interview: RequirementInterview,
        question_id: str,
    ) -> str:
        for answer in interview.answers:
            if answer.get("question_id") == question_id:
                return answer.get("answer", "")
        return ""

    def _requirement_items_from_answer(
        self,
        interview: RequirementInterview,
        question_id: str,
        prefix: str,
    ) -> List[Dict[str, Any]]:
        answer = self._answer_for_question(interview, question_id)
        if not answer:
            return []
        items = [
            item.strip(" -")
            for item in answer.replace(";", "\n").split("\n")
            if item.strip(" -")
        ]
        return [
            {
                "id": f"{prefix}-{index}",
                "text": item,
                "source": "requirements_copilot",
            }
            for index, item in enumerate(items, start=1)
        ]

    def _content_hash(self, payload: Dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
