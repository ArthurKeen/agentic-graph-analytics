"""Application services for product UI workflows.

The service layer exposes UI-ready read models and workflow operations without
coupling the core package to a web framework.
"""

import hashlib
import html
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..ai.schema.acquire import (
    SchemaAcquisitionBundle,
    SchemaCache,
    SchemaChangeReport,
    acquire_schema,
    describe_schema_change,
)
from ..ai.schema.graph_purpose import classify_graph_purpose
from ..ai.schema.sensitivity import (
    classify_conceptual_schema,
    classify_schema_sensitivity,
)
from ..ai.schema.arango_products import detect_arango_products
from ..ai.schema.extractor import SchemaExtractor
from ..ai.schema.models import GraphSchema
from ..db_connection import connect_arango_database
from .constants import PRODUCT_SCHEMA_VERSION
from .exceptions import ConflictError, ValidationError
from .models import (
    AuditEvent,
    ChartSpec,
    ConnectionProfile,
    ConnectionVerificationStatus,
    CrossGraphLink,
    DeploymentMode,
    GraphProfile,
    GraphSet,
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
    WorkspaceStatus,
    WorkflowDAGEdge,
    WorkflowMode,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowStep,
    WorkflowStepStatus,
    create_audit_event,
    create_connection_profile,
    create_graph_profile,
    create_graph_set,
    create_published_snapshot,
    create_requirement_interview,
    create_requirement_version,
    create_workspace,
    create_workflow_run,
    current_timestamp,
)
from .repository import ProductRepository, WorkspaceSchemaCache
from .secrets import EnvironmentSecretResolver, SecretResolver

logger = logging.getLogger(__name__)

# PRD v0.6: bundles produced under PRODUCT_SCHEMA_VERSION 1.0.0 / 1.1.0
# must still import cleanly under the current (1.2.0) version. The
# only deltas are the additive aga_schema_snapshots (1.1.0) and
# aga_graph_sets (1.2.0) collections — pre-existing collections are
# unchanged. Keep this set explicit — adding a future version is a
# one-line append, not a regex change.
_SUPPORTED_BUNDLE_SCHEMA_VERSIONS = frozenset(
    {"1.0.0", "1.1.0", PRODUCT_SCHEMA_VERSION}
)


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
class WorkspaceGraphInventoryResult:
    """Result of bulk-discovering every named graph on a connection (FR-67).

    The plural variant of :class:`GraphDiscoveryResult`. Returned by
    :meth:`ProductService.discover_graph_profiles`. Callers iterate
    ``graph_profiles`` to render the workspace's complete graph
    inventory and use ``failures`` to surface per-graph errors
    without aborting the whole sweep.

    ``database_only`` is an optional fallback entry returned when
    the connection's database has no named graphs at all (so the
    UI can still show a "treat the database as a single graph"
    card with the same shape as the regular profile cards).
    """

    connection_profile_id: str
    workspace_id: str
    database: str
    discovered_graph_count: int
    graph_profiles: List[Dict[str, Any]]
    failures: List[Dict[str, Any]] = field(default_factory=list)
    database_only: Optional[Dict[str, Any]] = None
    arango_product: Optional[Dict[str, Any]] = None
    """First-party Arango product report (PRD v0.6 / FR-67 follow-up).

    When the connection's database contains artefacts created by an
    Arango product (today: Autograph corpus + KG projects), this
    block carries the detection result so the UI can badge the
    inventory and auto-suggest GraphSets. ``None`` when no product
    artefacts were detected.
    """
    auto_created_graph_sets: List[Dict[str, Any]] = field(default_factory=list)
    """GraphSets that were auto-created from the detection report.

    One entry per detected Autograph project (corpus + KG bundled
    together with the implicit ``rags.entity_types ->
    Entities.entity_type`` cross-graph link). Empty when no
    Autograph projects were detected.
    """

    def to_dict(self) -> Dict[str, Any]:
        """Convert inventory result to an API-friendly dictionary."""

        return {
            "connection_profile_id": self.connection_profile_id,
            "workspace_id": self.workspace_id,
            "database": self.database,
            "discovered_graph_count": self.discovered_graph_count,
            "graph_profiles": self.graph_profiles,
            "failures": self.failures,
            "database_only": self.database_only,
            "arango_product": self.arango_product,
            "auto_created_graph_sets": self.auto_created_graph_sets,
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
class SchemaChangeView:
    """Result of probing a graph profile's cached schema for staleness.

    PRD v0.6 / FR-60. Returned by
    :meth:`ProductService.get_graph_profile_schema_change`. The fields
    mirror :class:`graph_analytics_ai.ai.schema.SchemaChangeReport` plus
    the originating ``graph_profile_id`` so the UI can route the response
    back to the right profile card without re-resolving it.
    """

    graph_profile_id: str
    status: str
    current_shape_fingerprint: str
    current_full_fingerprint: str
    cached_shape_fingerprint: Optional[str]
    cached_full_fingerprint: Optional[str]
    needs_full_rebuild: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to an API-friendly dictionary."""

        return {
            "graph_profile_id": self.graph_profile_id,
            "status": self.status,
            "current_shape_fingerprint": self.current_shape_fingerprint,
            "current_full_fingerprint": self.current_full_fingerprint,
            "cached_shape_fingerprint": self.cached_shape_fingerprint,
            "cached_full_fingerprint": self.cached_full_fingerprint,
            "needs_full_rebuild": self.needs_full_rebuild,
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
        agentic_run_supervisor: Optional[Any] = None,
    ):
        """Initialize service.

        ``agentic_run_supervisor`` is the FR-31a Phase 1 hook that
        actually executes agentic runs. It's optional so existing
        callers (including the current test suite) don't have to
        wire one up — when absent, ``start_workflow_run`` keeps its
        legacy "flip status to RUNNING and return" behavior, which
        is what callers got before FR-31a.
        """

        self.repository = repository
        self.secret_resolver = secret_resolver or EnvironmentSecretResolver()
        self.db_connector = db_connector or connect_arango_database
        self.schema_extractor_factory = schema_extractor_factory or SchemaExtractor
        # Optional FR-31a supervisor — the FastAPI app factory wires
        # one in via ``ProductService(..., agentic_run_supervisor=...)``
        # so it can also share its lifespan. Tests typically leave it
        # ``None`` (falling back to the legacy synchronous path) or
        # pass a fake supervisor with a known ``submit`` / ``cancel``
        # / ``get_status`` shape.
        self._agentic_run_supervisor = agentic_run_supervisor

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

    def update_workspace(
        self,
        workspace_id: str,
        customer_name: Optional[str] = None,
        project_name: Optional[str] = None,
        environment: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        actor: Optional[str] = None,
    ) -> Workspace:
        """Patch editable workspace metadata in place.

        Implements PRD FR-1 (workspace identity edit). All editable fields
        are optional so callers can update one column at a time. ``status``
        is intentionally NOT editable through this path — use
        :meth:`archive_workspace` instead so the lifecycle change always
        emits a dedicated audit event.
        """

        workspace = self.repository.get_workspace(workspace_id)
        changes: Dict[str, Any] = {}

        if customer_name is not None:
            stripped = customer_name.strip()
            if not stripped:
                raise ValidationError("Customer name cannot be empty")
            if stripped != workspace.customer_name:
                changes["customer_name"] = {
                    "from": workspace.customer_name,
                    "to": stripped,
                }
                workspace.customer_name = stripped

        if project_name is not None:
            stripped = project_name.strip()
            if not stripped:
                raise ValidationError("Project name cannot be empty")
            if stripped != workspace.project_name:
                changes["project_name"] = {
                    "from": workspace.project_name,
                    "to": stripped,
                }
                workspace.project_name = stripped

        if environment is not None:
            stripped = environment.strip()
            if not stripped:
                raise ValidationError("Environment cannot be empty")
            if stripped != workspace.environment:
                changes["environment"] = {"from": workspace.environment, "to": stripped}
                workspace.environment = stripped

        if description is not None:
            new_description = description.strip()
            if new_description != workspace.description:
                changes["description"] = {
                    "from": workspace.description,
                    "to": new_description,
                }
                workspace.description = new_description

        if tags is not None:
            normalized_tags = [tag.strip() for tag in tags if tag and tag.strip()]
            if normalized_tags != workspace.tags:
                changes["tags"] = {"from": list(workspace.tags), "to": normalized_tags}
                workspace.tags = normalized_tags

        # No-op updates do not emit audit events; they would just clutter
        # the timeline with zero-information rows. We still bump
        # ``updated_at`` only when something actually changed.
        if not changes:
            return workspace

        workspace.updated_at = current_timestamp()
        self.repository.update_workspace(workspace)
        self.repository.create_audit_event(
            create_audit_event(
                workspace_id=workspace.workspace_id,
                actor=actor or "system",
                action="update_workspace",
                target_type="workspace",
                target_id=workspace.workspace_id,
                details={"changes": changes},
            )
        )
        return workspace

    def archive_workspace(
        self,
        workspace_id: str,
        actor: Optional[str] = None,
    ) -> Workspace:
        """Soft-delete a workspace by flipping it to ARCHIVED.

        Idempotent: calling on an already-archived workspace returns it
        unchanged and does NOT emit a duplicate audit event. PRD FR-1
        treats archival as a soft-delete so historical reports/runs remain
        queryable for lineage/audit.
        """

        workspace = self.repository.get_workspace(workspace_id)
        if workspace.status == WorkspaceStatus.ARCHIVED:
            return workspace

        workspace.status = WorkspaceStatus.ARCHIVED
        workspace.updated_at = current_timestamp()
        self.repository.update_workspace(workspace)
        self.repository.create_audit_event(
            create_audit_event(
                workspace_id=workspace.workspace_id,
                actor=actor or "system",
                action="archive_workspace",
                target_type="workspace",
                target_id=workspace.workspace_id,
            )
        )
        return workspace

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
        requirement_interviews = self.repository.list_requirement_interviews(
            workspace_id
        )
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
        """Create a visualizable workflow run from planned steps and edges.

        FR-31a: when ``workflow_mode`` is ``AGENTIC``, any client-supplied
        steps and edges are ignored and replaced with the canonical
        six-step layout (schema_analysis → ... → reporting). This is
        the design decision locked in PRD v0.4: the visualizer must
        reflect what the runner actually does, not free-form labels
        a user typed. Traditional mode is unchanged — labels remain
        free-form there.
        """

        if workflow_mode == WorkflowMode.AGENTIC:
            steps, dag_edges = self._build_canonical_agentic_dag()

        self._validate_workflow_dag(steps, dag_edges)
        # Stamp executor_kind on agentic runs so we can distinguish
        # rows produced by the in-process supervisor from rows
        # produced by future durable executors (FR-31b).
        run_metadata = dict(metadata or {})
        if workflow_mode == WorkflowMode.AGENTIC:
            execution_meta = dict(run_metadata.get("execution") or {})
            execution_meta.setdefault("executor_kind", "inprocess")
            execution_meta.setdefault("last_outcome", "pending")
            run_metadata["execution"] = execution_meta

        run = create_workflow_run(
            workspace_id=workspace_id,
            workflow_mode=workflow_mode,
            status=WorkflowRunStatus.QUEUED,
            requirement_version_id=requirement_version_id,
            graph_profile_id=graph_profile_id,
            template_ids=template_ids or [],
            steps=steps,
            dag_edges=dag_edges,
            metadata=run_metadata,
        )
        self.repository.create_workflow_run(run)
        return run

    def _build_canonical_agentic_dag(self):
        """Seed the canonical agentic six-step layout.

        Lazily imports the supervisor module to avoid a circular
        import (the supervisor imports product.models). Returns a
        sequential DAG; parallelism inside the runner is its own
        concern and isn't reflected here in Phase 1.
        """

        from .agentic_run_supervisor import AGENTIC_STEP_LAYOUT

        steps = [
            WorkflowStep(step_id=canonical.step_id, label=canonical.label)
            for canonical in AGENTIC_STEP_LAYOUT
        ]
        edges: List[WorkflowDAGEdge] = []
        for previous, current in zip(AGENTIC_STEP_LAYOUT, AGENTIC_STEP_LAYOUT[1:]):
            edges.append(
                WorkflowDAGEdge(
                    from_step_id=previous.step_id,
                    to_step_id=current.step_id,
                )
            )
        return steps, edges

    def start_workflow_run(
        self, run_id: str, actor: Optional[str] = None
    ) -> WorkflowRun:
        """Mark a queued workflow run as running.

        FR-31a: when the run is in AGENTIC mode and a supervisor is
        wired up, also dispatch the run to the supervisor so the real
        agent pipeline executes in the background. The HTTP request
        returns immediately after flipping status to RUNNING — actual
        completion is reflected via per-step updates streamed by the
        :class:`StepStatusReporter`.

        Always emits a ``start_workflow_run`` audit event. For agentic
        runs the metadata records whether the supervisor accepted the
        submission, so audit logs can later distinguish "started but
        the supervisor wasn't wired" from "started and dispatched."
        """

        run = self.repository.get_workflow_run(run_id)
        run.status = WorkflowRunStatus.RUNNING
        run.started_at = run.started_at or current_timestamp()
        self.repository.update_workflow_run(run)

        dispatched = False
        if (
            run.workflow_mode == WorkflowMode.AGENTIC
            and self._agentic_run_supervisor is not None
        ):
            # Submit to the supervisor. submit() is idempotent so a
            # double-start (e.g. user clicks twice) is safe.
            self._agentic_run_supervisor.submit(run_id)
            dispatched = True

        execution_meta = (run.metadata or {}).get("execution") or {}
        self.repository.create_audit_event(
            create_audit_event(
                workspace_id=run.workspace_id,
                actor=actor or "workspace-ui",
                action="start_workflow_run",
                target_type="workflow_run",
                target_id=run.run_id,
                metadata={
                    "workflow_mode": run.workflow_mode.value,
                    "dispatched_to_supervisor": dispatched,
                    "executor_kind": execution_meta.get("executor_kind"),
                },
            )
        )

        return run

    def cancel_workflow_run(
        self, run_id: str, actor: Optional[str] = None
    ) -> WorkflowRun:
        """Request cooperative cancellation of an agentic run.

        Phase 1 semantics:
        * If a supervisor is wired and owns the run, the cancel signal
          is delivered immediately. The orchestrator polls between
          steps; the run will transition to ``cancelled`` once the
          current step finishes.
        * If no supervisor is wired (or the run is unknown to it,
          e.g. after an API restart), the run is flipped to
          ``cancelled`` synchronously so the visualizer doesn't keep
          showing a perpetual RUNNING.
        * Always emits an audit event so cancellations are recorded
          alongside other workspace state changes.
        """

        run = self.repository.get_workflow_run(run_id)

        delivered_to_supervisor = False
        if self._agentic_run_supervisor is not None:
            try:
                delivered_to_supervisor = bool(
                    self._agentic_run_supervisor.cancel(run_id)
                )
            except Exception:  # noqa: BLE001
                delivered_to_supervisor = False

        if not delivered_to_supervisor:
            # Synchronous fallback. The supervisor either doesn't own
            # the run or doesn't exist — in either case we don't want
            # to leave the row in RUNNING.
            run.status = WorkflowRunStatus.CANCELLED
            run.completed_at = current_timestamp()
            run.metadata = dict(run.metadata or {})
            execution_meta = dict(run.metadata.get("execution") or {})
            execution_meta["last_outcome"] = "cancelled"
            execution_meta["cancel_path"] = "synchronous"
            run.metadata["execution"] = execution_meta
            self.repository.update_workflow_run(run)

        self.repository.create_audit_event(
            create_audit_event(
                workspace_id=run.workspace_id,
                actor=actor or "workflow-runner",
                action="cancel_workflow_run",
                target_type="workflow_run",
                target_id=run.run_id,
                metadata={"delivered_to_supervisor": delivered_to_supervisor},
            )
        )

        return self.repository.get_workflow_run(run_id)

    def get_workflow_run_status(self, run_id: str) -> Dict[str, Any]:
        """Return a concise execution-status snapshot for a run.

        Combines the persisted run.status with supervisor-side
        execution metadata so the UI can poll a single small endpoint
        for cancel results, orphan-sweep outcomes, and live-run
        outcome strings without re-fetching the whole DAG.
        """

        run = self.repository.get_workflow_run(run_id)
        execution_meta = (run.metadata or {}).get("execution") or {}

        supervisor_status: Dict[str, Any]
        if self._agentic_run_supervisor is not None:
            try:
                supervisor_status = dict(
                    self._agentic_run_supervisor.get_status(run_id)
                )
            except Exception:  # noqa: BLE001
                supervisor_status = {"supervised": False}
        else:
            supervisor_status = {"supervised": False}

        return {
            "run_id": run.run_id,
            "workspace_id": run.workspace_id,
            "workflow_mode": run.workflow_mode.value,
            "status": run.status.value,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": (
                run.completed_at.isoformat() if run.completed_at else None
            ),
            "executor_kind": execution_meta.get("executor_kind"),
            "last_outcome": execution_meta.get("last_outcome"),
            "errors": list(run.errors or []),
            "supervisor": supervisor_status,
        }

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
        _internal: bool = False,
    ) -> WorkflowStepUpdateResult:
        """Update a workflow step and roll up run status for the visualizer.

        FR-31a AC#8: rejects manual updates against agentic runs because
        the :class:`AgenticRunSupervisor` is the sole authority on step
        transitions there — a UI-driven retry would race with the
        :class:`StepStatusReporter`. ``_internal=True`` bypasses the
        check; the supervisor passes it because it *is* the executor.
        The leading underscore intentionally hides the bypass from the
        FastAPI dispatcher (which maps JSON body keys to kwargs by
        name) so external HTTP callers cannot opt out.
        """

        run = self.repository.get_workflow_run(run_id)
        if not _internal and run.workflow_mode == WorkflowMode.AGENTIC:
            raise ConflictError(
                "Step transitions on agentic runs are managed by the "
                "AgenticRunSupervisor. Use POST /api/runs/{id}/cancel to "
                "stop a run; per-step retry on agentic runs is FR-31c."
            )
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
        if (
            previous_status == WorkflowStepStatus.FAILED
            and status == WorkflowStepStatus.RUNNING
        ):
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

        text = (
            section.content.get("text") if isinstance(section.content, dict) else None
        )
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
            lineage_items.append(
                f"<li>Run: <code>{html.escape(manifest.run_id)}</code></li>"
            )
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
            lineage_items.append(
                f"<li>Use case: <code>{html.escape(use_case_id)}</code></li>"
            )
        for template_id in manifest.template_ids:
            lineage_items.append(
                f"<li>Template: <code>{html.escape(template_id)}</code></li>"
            )
        for execution_id in manifest.analysis_execution_ids:
            lineage_items.append(
                f"<li>Execution: <code>{html.escape(execution_id)}</code></li>"
            )
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
            '<html lang="en"><head>'
            f'<meta charset="utf-8"/><title>{title_html}</title>'
            f"<style>{style}</style>"
            "</head><body>" + "".join(body_parts) + "</body></html>"
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
        schema_strategy: str = "auto",
    ) -> GraphDiscoveryResult:
        """Discover graph schema from a connection profile and persist it.

        v0.6 (FR-56..FR-65) — after the legacy collection-typed extraction,
        we additionally run :func:`acquire_schema` to obtain a bundle that
        understands LPG / hybrid / RPT graphs, then stamp the rolled-up
        ``schema_kind`` and conceptual + physical mappings onto the
        persisted :class:`GraphProfile`. The bundle is also written through
        to ``aga_schema_snapshots`` via :class:`WorkspaceSchemaCache` so
        subsequent discoveries / requirements-copilot runs hit the cache.
        ``schema_strategy`` ("auto" | "analyzer" | "heuristic") is the
        FR-57 escalation knob — see :func:`acquire_schema` for the
        precedence rules.
        """

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

        selected_graph_name = self._select_graph_name(
            schema, graph_name, profile.database
        )

        graph_scope = self._scope_to_named_graph(db, schema, selected_graph_name)
        scoped_vertex_collections = sorted(graph_scope["vertex_collections"])
        scoped_edge_collections = sorted(graph_scope["edge_collections"])
        scoped_edge_definitions = graph_scope[
            "edge_definitions"
        ] or self._schema_edge_definitions(schema)
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

        # v0.6 enrichment: acquire a typed conceptual + physical bundle.
        # Run after the legacy extraction so a failure here can degrade
        # gracefully — the GraphProfile still gets created with its
        # collection lists; only the v0.6 fields are skipped.
        acquisition_bundle, snapshot_id = self._acquire_and_persist_bundle(
            db=db,
            workspace_id=profile.workspace_id,
            graph_name=selected_graph_name,
            strategy=schema_strategy,
        )

        v6_kwargs: Dict[str, Any] = {}
        if acquisition_bundle is not None:
            v6_kwargs["schema_kind"] = acquisition_bundle.schema_kind
            v6_kwargs["conceptual_schema"] = acquisition_bundle.conceptual_schema
            v6_kwargs["physical_mapping"] = acquisition_bundle.physical_mapping
            v6_kwargs["analyzer_metadata"] = acquisition_bundle.analyzer_metadata
            if snapshot_id is not None:
                v6_kwargs["schema_snapshot_id"] = snapshot_id

            # Phase 6b (FR-61..FR-63): classify the analytical purpose
            # so the UI can badge each profile (corpus / KG /
            # structured / analytics / hybrid / unknown). The
            # classification result is stamped into ``analyzer_metadata``
            # under "graph_purpose_classification" so reasons +
            # confidence + per-rule scores survive the round-trip and
            # back the workbench tooltip.
            try:
                classification = classify_graph_purpose(acquisition_bundle)
            except Exception:  # noqa: BLE001 — never block discovery
                classification = None
            if classification is not None:
                v6_kwargs["graph_purpose"] = classification.purpose
                merged_meta = dict(v6_kwargs["analyzer_metadata"])
                merged_meta["graph_purpose_classification"] = classification.to_dict()
                v6_kwargs["analyzer_metadata"] = merged_meta

            # Phase 6d (FR-72): tag every conceptual property with a
            # sensitivity level (high/medium/low/safe/unknown). Stored
            # under analyzer_metadata.sensitivity so the report
            # generator's masking pass + Graph Explorer overlay can read
            # it without re-running the classifier.
            try:
                sensitivity_report = classify_schema_sensitivity(acquisition_bundle)
            except Exception:  # noqa: BLE001 — never block discovery
                sensitivity_report = None
            if sensitivity_report is not None:
                merged_meta = dict(v6_kwargs["analyzer_metadata"])
                merged_meta["sensitivity"] = sensitivity_report.to_dict()
                v6_kwargs["analyzer_metadata"] = merged_meta

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
                "schema_strategy": schema_strategy,
            },
            **v6_kwargs,
        )
        self.repository.create_graph_profile(graph_profile)

        return GraphDiscoveryResult(
            graph_profile=graph_profile.to_dict(),
            schema_summary=schema.to_summary_dict(),
        )

    def discover_graph_profiles(
        self,
        connection_profile_id: str,
        created_by: Optional[str] = None,
        password_secret_key: str = "password",
        sample_size: int = 100,
        max_samples_per_collection: int = 3,
        verify_system: bool = True,
        schema_strategy: str = "auto",
        include_system: bool = False,
    ) -> WorkspaceGraphInventoryResult:
        """Bulk-discover every named graph on a connection (FR-67).

        Iterates :meth:`list_connection_profile_graphs`, calls
        :meth:`discover_graph_profile` for each non-system graph, and
        aggregates the resulting profiles into a single inventory
        result. Per-graph failures are collected into ``failures``
        rather than aborting the sweep — the UI can render a partial
        inventory with red flags on the broken entries instead of
        nothing at all.

        When the database exposes no named graphs (a common case for
        small / hand-built corpora), a single fallback profile is
        created against the whole database and returned in the
        ``database_only`` slot. This preserves the v0.5 single-graph
        UX for that case while still funnelling everything through
        the same downstream wiring (acquisition + classifier + cache).
        """

        # Enumerate the named graphs first so we can persist each one
        # individually. ``list_connection_profile_graphs`` already opens
        # a database handle and reads ``db.graphs()``; we rely on its
        # error mapping (ValidationError on driver failure).
        inventory = self.list_connection_profile_graphs(
            connection_profile_id=connection_profile_id,
            password_secret_key=password_secret_key,
            verify_system=verify_system,
            include_system=include_system,
            include_counts=False,
        )
        connection = self.repository.get_connection_profile(connection_profile_id)

        graph_profiles: List[Dict[str, Any]] = []
        failures: List[Dict[str, Any]] = []
        database_only: Optional[Dict[str, Any]] = None

        eligible_names = [g.name for g in inventory.graphs if not g.is_system]

        if not eligible_names:
            # Fallback: treat the whole database as a single
            # database-level graph (graph_name="__db__"). This mirrors
            # the existing single-graph behavior so the UI doesn't
            # have to special-case workspaces that haven't created a
            # named graph yet.
            try:
                result = self.discover_graph_profile(
                    connection_profile_id=connection_profile_id,
                    graph_name=None,
                    created_by=created_by,
                    password_secret_key=password_secret_key,
                    sample_size=sample_size,
                    max_samples_per_collection=max_samples_per_collection,
                    verify_system=verify_system,
                    schema_strategy=schema_strategy,
                )
                database_only = result.to_dict()
            except Exception as exc:  # noqa: BLE001
                failures.append(
                    {
                        "graph_name": None,
                        "error_type": exc.__class__.__name__,
                        "message": str(exc),
                    }
                )
        else:
            for graph_name in eligible_names:
                try:
                    result = self.discover_graph_profile(
                        connection_profile_id=connection_profile_id,
                        graph_name=graph_name,
                        created_by=created_by,
                        password_secret_key=password_secret_key,
                        sample_size=sample_size,
                        max_samples_per_collection=max_samples_per_collection,
                        verify_system=verify_system,
                        schema_strategy=schema_strategy,
                    )
                    graph_profiles.append(result.graph_profile)
                except Exception as exc:  # noqa: BLE001
                    # Per-graph failure should NOT take down the sweep.
                    # The UI surfaces the error next to the failing
                    # graph card and the user can retry that one
                    # individually with discover_graph_profile.
                    failures.append(
                        {
                            "graph_name": graph_name,
                            "error_type": exc.__class__.__name__,
                            "message": str(exc),
                        }
                    )

        # PRD v0.6 follow-up: detect first-party Arango product
        # artefacts (Autograph corpora + KGs) from the inventory and
        # auto-create one GraphSet per detected project. Failures here
        # are non-fatal — the inventory still returns even if the
        # detector or GraphSet creation throws.
        arango_product_dict, auto_graph_sets = self._detect_and_auto_pair_products(
            connection_profile_id=connection_profile_id,
            workspace_id=connection.workspace_id,
            graph_profiles=graph_profiles,
            inventory=inventory,
            actor=created_by,
        )

        return WorkspaceGraphInventoryResult(
            connection_profile_id=connection_profile_id,
            workspace_id=connection.workspace_id,
            database=connection.database,
            discovered_graph_count=len(graph_profiles),
            graph_profiles=graph_profiles,
            failures=failures,
            database_only=database_only,
            arango_product=arango_product_dict,
            auto_created_graph_sets=auto_graph_sets,
        )

    def _detect_and_auto_pair_products(
        self,
        *,
        connection_profile_id: str,
        workspace_id: str,
        graph_profiles: List[Dict[str, Any]],
        inventory: "ConnectionGraphsResult",
        actor: Optional[str],
    ) -> tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """Detect Autograph projects and auto-create one GraphSet each.

        Builds a minimal snapshot from the inventory's collection +
        named-graph names, runs :func:`detect_arango_products`, and
        for each detected project:

        - Locates the corpus + KG :class:`GraphProfile` records that
          belong to this project (matched by ``graph_name`` ==
          ``<project>_CorpusGraph`` / ``<project>_kg``).
        - Calls :meth:`create_graph_set` to register a workspace
          GraphSet wrapping both, with the implicit
          ``rags.entity_types -> Entities.entity_type`` cross-graph
          link pre-populated.

        Idempotent: if a GraphSet with the same name already exists
        for the workspace, we attach to it instead of creating a
        duplicate.

        Returns ``(arango_product_dict_or_None, auto_created_graph_sets)``.
        """

        # Build the snapshot the detector expects (just names — no
        # samples needed). Use the inventory we already have rather
        # than re-querying the DB.
        try:
            snapshot = {
                "collections": [
                    {"name": name}
                    for graph in inventory.graphs
                    for name in (
                        list(graph.vertex_collections)
                        + list(graph.edge_collections)
                        + list(graph.orphan_collections)
                    )
                ],
                "graphs": [{"name": g.name} for g in inventory.graphs],
            }
            # De-dupe collection list — multiple graphs may share collections.
            seen_names: set[str] = set()
            unique_collections: list[dict[str, str]] = []
            for entry in snapshot["collections"]:
                if entry["name"] not in seen_names:
                    seen_names.add(entry["name"])
                    unique_collections.append(entry)
            snapshot["collections"] = unique_collections

            report = detect_arango_products(snapshot)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Autograph detection failed for connection %s: %s",
                connection_profile_id,
                exc,
            )
            return None, []

        if report.is_empty:
            return None, []

        product_dict = report.to_dict()
        auto_created: List[Dict[str, Any]] = []

        # Index the just-discovered graph profiles by graph_name for
        # quick lookup when pairing corpus + KG into a GraphSet.
        profiles_by_graph_name: Dict[str, str] = {}
        for profile_dict in graph_profiles:
            graph_name = profile_dict.get("graph_name")
            graph_profile_id = profile_dict.get("graph_profile_id")
            if graph_name and graph_profile_id:
                profiles_by_graph_name[graph_name] = graph_profile_id

        for project in report.autograph_projects:
            corpus_pid = (
                profiles_by_graph_name.get(project.corpus_graph)
                if project.corpus_graph
                else None
            )
            kg_pid = (
                profiles_by_graph_name.get(project.kg_graph)
                if project.kg_graph
                else None
            )
            members = [pid for pid in (corpus_pid, kg_pid) if pid]
            if len(members) < 1:
                # No matching profile in the just-created sweep —
                # likely the project's graphs were skipped (system or
                # excluded). Skip auto-creation rather than guessing.
                continue

            primary = kg_pid or corpus_pid
            graph_set_name = f"autograph:{project.project_name}"

            # Build cross-graph links from the detector's implicit
            # links — but only when both endpoints map to actual
            # GraphProfiles. (When KG is missing for a corpus_only
            # project, no cross-graph link is possible.)
            cross_links: List[Dict[str, Any]] = []
            if corpus_pid and kg_pid:
                for link in project.implicit_links:
                    cross_links.append(
                        {
                            "from_graph_profile_id": corpus_pid,
                            "from_field": link["from"],
                            "to_graph_profile_id": kg_pid,
                            "to_field": link["to"],
                            "link_type": "equality",
                            "confidence": project.confidence,
                            "metadata": {
                                "kind": link["kind"],
                                "discovered_by": "autograph_detector",
                            },
                        }
                    )

            try:
                # Idempotent: re-use existing GraphSet if same name
                # already registered for this workspace.
                existing = [
                    gs
                    for gs in self.list_graph_sets(workspace_id=workspace_id)
                    if gs.name == graph_set_name
                ]
                if existing:
                    auto_created.append(existing[0].to_dict())
                    continue

                graph_set = self.create_graph_set(
                    workspace_id=workspace_id,
                    name=graph_set_name,
                    description=(
                        f"Auto-created from detected Autograph project "
                        f"'{project.project_name}' "
                        f"({project.completeness}). "
                        f"{'; '.join(project.warnings) if project.warnings else ''}"
                    ).strip(),
                    graph_profile_ids=members,
                    primary_graph_profile_id=primary,
                    cross_graph_links=cross_links,
                    actor=actor,
                )
                auto_created.append(graph_set.to_dict())
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Auto-creating GraphSet for Autograph project '%s' " "failed: %s",
                    project.project_name,
                    exc,
                )

        return product_dict, auto_created

    def _acquire_and_persist_bundle(
        self,
        db: Any,
        workspace_id: str,
        graph_name: str,
        strategy: str,
    ) -> tuple[Optional[SchemaAcquisitionBundle], Optional[str]]:
        """Run :func:`acquire_schema` and write through to ``aga_schema_snapshots``.

        Failures here are *non-fatal* — discover_graph_profile must still
        succeed and persist a v0.5-shaped profile. The fallback path the
        acquisition module already provides (analyzer → heuristic →
        warning) covers the most common failure mode (analyzer not
        installed); only a hard storage outage on the cache write or a
        DB-side AQL failure during sampling will surface here.

        Returns ``(bundle, snapshot_id)``. ``snapshot_id`` is set when
        the cache write succeeded so the caller can stamp it onto the
        ``GraphProfile`` for the UI back-pointer.
        """

        try:
            cache = WorkspaceSchemaCache(self.repository, workspace_id)
            bundle = acquire_schema(
                db,
                strategy=strategy,  # type: ignore[arg-type]
                graph_name=graph_name,
                cache=cache,
            )
        except Exception:  # noqa: BLE001 — degrade gracefully on any failure
            return None, None

        # Look up the snapshot row that WorkspaceSchemaCache.set just
        # persisted, keyed by the same cache_key the acquisition module
        # uses. The lookup is best-effort — when missing, the GraphProfile
        # simply omits the back-pointer.
        snapshot_id: Optional[str] = None
        try:
            from ..ai.schema.acquire import cache_key as _cache_key

            persisted = self.repository.get_schema_snapshot_by_cache_key(
                _cache_key(database=bundle.database, graph_name=bundle.graph_name)
            )
            snapshot_id = persisted.schema_snapshot_id if persisted else None
        except Exception:  # noqa: BLE001
            snapshot_id = None

        return bundle, snapshot_id

    def get_graph_profile_schema_change(
        self,
        graph_profile_id: str,
        password_secret_key: str = "password",
        verify_system: bool = True,
    ) -> SchemaChangeView:
        """Lightweight schema-change probe for a graph profile (FR-60).

        Resolves the connection from the profile's
        ``connection_profile_id``, opens a database handle, and calls
        :func:`describe_schema_change` against the L2 cache. Read-only:
        does not mutate either cache, never re-runs the analyzer, and
        does not write a snapshot. Typical cost is well under 200ms.
        """

        graph_profile = self.repository.get_graph_profile(graph_profile_id)
        connection = self.repository.get_connection_profile(
            graph_profile.connection_profile_id
        )

        password_ref = connection.secret_refs.get(password_secret_key)
        if not password_ref:
            raise ValidationError(
                f"Connection profile is missing secret ref: {password_secret_key}"
            )
        password = self.secret_resolver.resolve(password_ref)

        db = self.db_connector(
            endpoint=connection.endpoint,
            username=connection.username,
            password=password,
            database=connection.database,
            verify_ssl=connection.verify_ssl,
            verify_system=verify_system,
        )
        cache = WorkspaceSchemaCache(self.repository, connection.workspace_id)
        report: SchemaChangeReport = describe_schema_change(
            db, graph_name=graph_profile.graph_name, cache=cache
        )
        return SchemaChangeView(
            graph_profile_id=graph_profile_id,
            status=report.status,
            current_shape_fingerprint=report.current_shape_fingerprint,
            current_full_fingerprint=report.current_full_fingerprint,
            cached_shape_fingerprint=report.cached_shape_fingerprint,
            cached_full_fingerprint=report.cached_full_fingerprint,
            needs_full_rebuild=report.needs_full_rebuild,
        )

    def update_graph_profile_conceptual_schema(
        self,
        graph_profile_id: str,
        conceptual_schema: Dict[str, Any],
        actor: Optional[str] = None,
    ) -> GraphProfile:
        """Patch the conceptual schema on a graph profile (FR-64).

        Used by the Type Role editor in Graph Explorer when the user
        renames a logical entity, splits a hybrid label, or attaches
        a description that the analyzer could not infer. The patch is
        bounded — only ``conceptual_schema`` changes; physical mapping
        is owned by the analyzer and untouched here.

        Validates the incoming payload as a dict with at least
        ``entities`` and ``relationships`` keys (lists). Stamps an
        audit event with the actor + before/after summary so the
        change history is traceable.
        """

        if not isinstance(conceptual_schema, dict):
            raise ValidationError("conceptual_schema must be a JSON object")
        for required_key in ("entities", "relationships"):
            value = conceptual_schema.get(required_key)
            if not isinstance(value, list):
                raise ValidationError(
                    f"conceptual_schema.{required_key} must be a list "
                    "(got {})".format(type(value).__name__)
                )

        graph_profile = self.repository.get_graph_profile(graph_profile_id)
        before_entities = len(
            (graph_profile.conceptual_schema or {}).get("entities", [])
        )
        before_relationships = len(
            (graph_profile.conceptual_schema or {}).get("relationships", [])
        )

        graph_profile.conceptual_schema = conceptual_schema
        # Stamp a manual-override marker on analyzer_metadata so the UI
        # can show "edited by user" provenance and so the next
        # acquisition's reconciliation step can preserve user edits.
        meta = dict(graph_profile.analyzer_metadata or {})
        meta["manual_override"] = {
            "edited_at": current_timestamp().isoformat(),
            "edited_by": actor or "system",
            "field": "conceptual_schema",
        }
        # Phase 6d (FR-72): re-classify sensitivity now that the
        # entity/property names changed. Failures are non-fatal — we
        # keep the prior tags rather than blocking the user's edit.
        try:
            updated_sensitivity = classify_conceptual_schema(conceptual_schema)
            meta["sensitivity"] = updated_sensitivity.to_dict()
        except Exception:  # noqa: BLE001
            pass
        graph_profile.analyzer_metadata = meta

        self.repository.update_graph_profile(graph_profile)
        self.repository.create_audit_event(
            create_audit_event(
                workspace_id=graph_profile.workspace_id,
                actor=actor or "system",
                action="update_graph_profile_conceptual_schema",
                target_type="graph_profile",
                target_id=graph_profile.graph_profile_id,
                metadata={
                    "before": {
                        "entities": before_entities,
                        "relationships": before_relationships,
                    },
                    "after": {
                        "entities": len(conceptual_schema.get("entities", [])),
                        "relationships": len(
                            conceptual_schema.get("relationships", [])
                        ),
                    },
                },
            )
        )
        return graph_profile

    def update_graph_profile_purpose(
        self,
        graph_profile_id: str,
        graph_purpose: str,
        actor: Optional[str] = None,
    ) -> GraphProfile:
        """Patch the analytical purpose tag on a graph profile (FR-65).

        Used when the user disagrees with the classifier's verdict.
        ``graph_purpose`` must be one of the closed set defined in
        :data:`graph_analytics_ai.ai.schema.graph_purpose.GraphPurpose`.

        The override is recorded on ``analyzer_metadata.manual_override``
        (with field ``graph_purpose``) so the UI can flag the badge as
        "user-set" and so subsequent re-classifications can defer to
        the user's choice unless explicitly reset.
        """

        valid_values = {
            "corpus",
            "knowledge_graph",
            "structured",
            "analytics",
            "hybrid",
            "unknown",
        }
        if graph_purpose not in valid_values:
            raise ValidationError(
                f"graph_purpose must be one of {sorted(valid_values)}, "
                f"got {graph_purpose!r}"
            )

        graph_profile = self.repository.get_graph_profile(graph_profile_id)
        before = graph_profile.graph_purpose

        graph_profile.graph_purpose = graph_purpose
        meta = dict(graph_profile.analyzer_metadata or {})
        meta["manual_override"] = {
            "edited_at": current_timestamp().isoformat(),
            "edited_by": actor or "system",
            "field": "graph_purpose",
            "previous_value": before,
        }
        graph_profile.analyzer_metadata = meta

        self.repository.update_graph_profile(graph_profile)
        self.repository.create_audit_event(
            create_audit_event(
                workspace_id=graph_profile.workspace_id,
                actor=actor or "system",
                action="update_graph_profile_purpose",
                target_type="graph_profile",
                target_id=graph_profile.graph_profile_id,
                metadata={"before": before, "after": graph_purpose},
            )
        )
        return graph_profile

    # ------------------------------------------------------------------
    # GraphSet workbench (PRD v0.6 / FR-68..FR-70)
    # ------------------------------------------------------------------

    def create_graph_set(
        self,
        workspace_id: str,
        name: str,
        graph_profile_ids: List[str],
        description: Optional[str] = None,
        cross_graph_links: Optional[List[Dict[str, Any]]] = None,
        primary_graph_profile_id: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> GraphSet:
        """Create a curated multi-graph grouping (FR-68).

        Validates that:
        - the workspace exists,
        - every ``graph_profile_id`` belongs to that workspace,
        - ``primary_graph_profile_id`` (if set) is in the list,
        - cross-graph link endpoints reference profiles in the set
          (already enforced by :class:`GraphSet.__post_init__`, but
          we surface a friendlier ValidationError here too).
        """

        if not name or not name.strip():
            raise ValidationError("GraphSet name is required")
        if not graph_profile_ids:
            raise ValidationError("GraphSet must contain at least one graph_profile_id")

        # Reject duplicates so the workbench's side-by-side render
        # is deterministic and so the cross-graph link validator
        # operates on a clean ID set.
        seen: set[str] = set()
        deduped: List[str] = []
        for pid in graph_profile_ids:
            if pid in seen:
                raise ValidationError(f"Duplicate graph_profile_id in GraphSet: {pid}")
            seen.add(pid)
            deduped.append(pid)

        # Existence + workspace-scoping check. We never trust the
        # caller to have already validated this — the API surface
        # is workspace-scoped but the endpoint receives raw IDs.
        for pid in deduped:
            profile = self.repository.get_graph_profile(pid)
            if profile.workspace_id != workspace_id:
                raise ValidationError(
                    f"graph_profile {pid} does not belong to workspace {workspace_id}"
                )

        link_objs = [CrossGraphLink.from_dict(d) for d in (cross_graph_links or [])]
        graph_set = create_graph_set(
            workspace_id=workspace_id,
            name=name.strip(),
            graph_profile_ids=deduped,
            description=(description.strip() if description else None),
            cross_graph_links=link_objs,
            primary_graph_profile_id=(
                primary_graph_profile_id or (deduped[0] if deduped else None)
            ),
            created_by=actor,
        )
        self.repository.create_graph_set(graph_set)
        self.repository.create_audit_event(
            create_audit_event(
                workspace_id=workspace_id,
                actor=actor or "system",
                action="create_graph_set",
                target_type="graph_set",
                target_id=graph_set.graph_set_id,
                metadata={
                    "graph_profile_count": len(deduped),
                    "cross_graph_link_count": len(link_objs),
                },
            )
        )
        return graph_set

    def list_graph_sets(self, workspace_id: str) -> List[GraphSet]:
        """List all graph sets in a workspace, freshest first (FR-68)."""

        return self.repository.list_graph_sets(workspace_id)

    def get_graph_set(self, graph_set_id: str) -> GraphSet:
        """Get a graph set by ID (FR-68)."""

        return self.repository.get_graph_set(graph_set_id)

    def update_graph_set(
        self,
        graph_set_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        graph_profile_ids: Optional[List[str]] = None,
        cross_graph_links: Optional[List[Dict[str, Any]]] = None,
        primary_graph_profile_id: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> GraphSet:
        """Patch a graph set in place (FR-68 / FR-69).

        Each field is optional so the workbench can rename, retarget
        the primary, add/remove members, or update the link list
        independently. Re-validates the resulting set the same way
        :meth:`create_graph_set` does — duplicates rejected, members
        confirmed in the same workspace, links reference set members.
        """

        graph_set = self.repository.get_graph_set(graph_set_id)
        changes: Dict[str, Any] = {}

        if name is not None:
            stripped = name.strip()
            if not stripped:
                raise ValidationError("name cannot be empty")
            if stripped != graph_set.name:
                changes["name"] = {"from": graph_set.name, "to": stripped}
                graph_set.name = stripped

        if description is not None:
            new_desc = description.strip() if description else None
            if new_desc != graph_set.description:
                changes["description"] = True
                graph_set.description = new_desc

        if graph_profile_ids is not None:
            if not graph_profile_ids:
                raise ValidationError("graph_profile_ids cannot be empty")
            seen: set[str] = set()
            deduped: List[str] = []
            for pid in graph_profile_ids:
                if pid in seen:
                    raise ValidationError(f"Duplicate graph_profile_id: {pid}")
                seen.add(pid)
                deduped.append(pid)
            for pid in deduped:
                profile = self.repository.get_graph_profile(pid)
                if profile.workspace_id != graph_set.workspace_id:
                    raise ValidationError(
                        f"graph_profile {pid} does not belong to "
                        f"workspace {graph_set.workspace_id}"
                    )
            changes["graph_profile_ids"] = {
                "from": list(graph_set.graph_profile_ids),
                "to": deduped,
            }
            graph_set.graph_profile_ids = deduped
            # Demote primary if it dropped out of the list.
            if (
                graph_set.primary_graph_profile_id
                and graph_set.primary_graph_profile_id not in deduped
            ):
                graph_set.primary_graph_profile_id = deduped[0]

        if cross_graph_links is not None:
            ids = set(graph_set.graph_profile_ids)
            link_objs = [CrossGraphLink.from_dict(d) for d in cross_graph_links]
            for link in link_objs:
                if link.from_graph_profile_id not in ids:
                    raise ValidationError(
                        f"CrossGraphLink references unknown profile: "
                        f"{link.from_graph_profile_id}"
                    )
                if link.to_graph_profile_id not in ids:
                    raise ValidationError(
                        f"CrossGraphLink references unknown profile: "
                        f"{link.to_graph_profile_id}"
                    )
            changes["cross_graph_links"] = len(link_objs)
            graph_set.cross_graph_links = link_objs

        if primary_graph_profile_id is not None:
            if primary_graph_profile_id not in graph_set.graph_profile_ids:
                raise ValidationError(
                    "primary_graph_profile_id must be in graph_profile_ids"
                )
            if primary_graph_profile_id != graph_set.primary_graph_profile_id:
                changes["primary_graph_profile_id"] = {
                    "from": graph_set.primary_graph_profile_id,
                    "to": primary_graph_profile_id,
                }
                graph_set.primary_graph_profile_id = primary_graph_profile_id

        if not changes:
            return graph_set

        self.repository.update_graph_set(graph_set)
        self.repository.create_audit_event(
            create_audit_event(
                workspace_id=graph_set.workspace_id,
                actor=actor or "system",
                action="update_graph_set",
                target_type="graph_set",
                target_id=graph_set.graph_set_id,
                metadata={"changed_fields": sorted(changes.keys())},
            )
        )
        return graph_set

    def discover_cross_graph_links(
        self,
        graph_set_id: str,
        max_links: int = 16,
        min_overlap: int = 5,
    ) -> List[Dict[str, Any]]:
        """Suggest CrossGraphLinks across the profiles in a set (FR-69).

        Heuristic: any field name that appears in the conceptual
        schemas of two distinct profiles in the set, AND has a
        plausible "joinable identifier" name (id, key, _id, email,
        sha256, document_id, source_id, ssn) is surfaced as a
        candidate link with confidence 0.6. Confidence is bumped
        toward 0.85 when both sides come from the same connection
        (same database — the most common case for a workspace's own
        corpus + KG).

        This method does NOT touch the database; it only inspects the
        conceptual_schema / physical_mapping snapshots already on the
        graph profiles. Heavier statistical overlap probes (which
        WOULD need DB access) are intentionally deferred to Phase 6d.

        ``max_links`` caps the number of suggestions returned to keep
        the workbench tooltip manageable. ``min_overlap`` reserved
        for the future statistical path; ignored here.
        """

        graph_set = self.repository.get_graph_set(graph_set_id)

        # Collect (profile_id, set_of_field_names) per member.
        members: List[tuple[str, str, set[str]]] = []
        for pid in graph_set.graph_profile_ids:
            profile = self.repository.get_graph_profile(pid)
            field_names = self._collect_joinable_fields(profile)
            members.append((pid, profile.connection_profile_id, field_names))

        # Limit reserved (paginates the suggestion list shown in UI).
        del min_overlap

        candidates: List[Dict[str, Any]] = []
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                pid_a, conn_a, fields_a = members[i]
                pid_b, conn_b, fields_b = members[j]
                shared = sorted(fields_a & fields_b)
                for fld in shared:
                    confidence = 0.85 if conn_a == conn_b else 0.60
                    candidates.append(
                        {
                            "from_graph_profile_id": pid_a,
                            "to_graph_profile_id": pid_b,
                            "from_field": fld,
                            "to_field": fld,
                            "link_type": "equality",
                            "confidence": confidence,
                            "metadata": {
                                "discovery": "name_match",
                                "shared_field": fld,
                            },
                        }
                    )

        # Sort by confidence desc then field name for stable output.
        candidates.sort(
            key=lambda c: (
                -c["confidence"],
                c["from_field"],
                c["from_graph_profile_id"],
            )
        )
        return candidates[:max_links]

    @staticmethod
    def _collect_joinable_fields(profile: GraphProfile) -> set[str]:
        """Pull joinable-looking property names from a profile's schemas.

        Drawn from both the conceptual schema (entity properties +
        relationship properties) and the physical mapping (typeField,
        collectionName) so a heuristic name match against e.g.
        ``email`` or ``sha256`` works for both PG and LPG profiles.
        """
        joinable_patterns = {
            "id",
            "_id",
            "_key",
            "key",
            "email",
            "sha256",
            "uuid",
            "url",
            "document_id",
            "source_id",
            "source_document_id",
            "ssn",
            "phone",
            "tax_id",
            "ein",
            "isbn",
            "doi",
        }
        out: set[str] = set()
        if profile.conceptual_schema:
            for entity in profile.conceptual_schema.get("entities", []) or []:
                for prop in entity.get("properties", []) or []:
                    name = prop if isinstance(prop, str) else (prop or {}).get("name")
                    if isinstance(name, str) and name.lower() in joinable_patterns:
                        out.add(name.lower())
            for rel in profile.conceptual_schema.get("relationships", []) or []:
                for prop in rel.get("properties", []) or []:
                    name = prop if isinstance(prop, str) else (prop or {}).get("name")
                    if isinstance(name, str) and name.lower() in joinable_patterns:
                        out.add(name.lower())
        return out

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
        schema_observations = self._schema_observations_from_graph_profile(
            graph_profile
        )
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
        requirement_interviews = self.repository.list_requirement_interviews(
            workspace_id
        )
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
            WorkflowRun.from_dict(run) for run in bundle_doc.get("workflow_runs", [])
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
                self.repository.create_report_section(
                    ReportSection.from_dict(section_doc)
                )
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

        # PRD v0.6 bumped PRODUCT_SCHEMA_VERSION 1.0.0 → 1.1.0 (added the
        # aga_schema_snapshots collection — additive only, no breaking
        # changes to existing collections). Bundles emitted by 1.0.0
        # callers are forward-compatible: the new collection simply
        # remains empty until the next discover_graph_profile call
        # populates it. Accept the open set of supported versions so
        # exporters can keep emitting 1.0.0 during the transition.
        if bundle_doc["schema_version"] not in _SUPPORTED_BUNDLE_SCHEMA_VERSIONS:
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
            self._validate_workspace_id(
                "reports.manifest", report["manifest"], workspace_id
            )
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
        vertex_collections = (
            ", ".join(observations.get("vertex_collections", [])) or "None observed"
        )
        edge_collections = (
            ", ".join(observations.get("edge_collections", [])) or "None observed"
        )
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
            {
                "path": "observed_schema.vertex_collections",
                "label": "observed_from_schema",
            },
            {
                "path": "observed_schema.edge_collections",
                "label": "observed_from_schema",
            },
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
