"""High-level product metadata repository."""

import logging
from typing import List, Optional

from .models import (
    AuditEvent,
    ChartSpec,
    ConnectionProfile,
    GraphProfile,
    GraphSet,
    PublishedSnapshot,
    ReportManifest,
    ReportSection,
    RequirementInterview,
    RequirementVersion,
    SchemaSnapshot,
    SourceDocument,
    Workspace,
    WorkflowRun,
    create_schema_snapshot,
)
from .storage import ProductArangoStorage

logger = logging.getLogger(__name__)


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

    # --- Schema snapshot operations (PRD v0.6 / FR-59) ---

    def create_schema_snapshot(self, snapshot: SchemaSnapshot) -> str:
        """Insert a schema snapshot row."""

        return self.storage.insert_schema_snapshot(snapshot)

    def get_schema_snapshot(self, schema_snapshot_id: str) -> SchemaSnapshot:
        """Get a schema snapshot by ID."""

        return self.storage.get_schema_snapshot(schema_snapshot_id)

    def update_schema_snapshot(self, snapshot: SchemaSnapshot) -> str:
        """Update a schema snapshot row."""

        return self.storage.update_schema_snapshot(snapshot)

    def get_schema_snapshot_by_cache_key(
        self, cache_key: str
    ) -> Optional[SchemaSnapshot]:
        """Look up the most recent snapshot for a cache_key, or None."""

        return self.storage.get_schema_snapshot_by_cache_key(cache_key)

    def delete_schema_snapshot_by_cache_key(self, cache_key: str) -> int:
        """Delete every snapshot row for a cache_key."""

        return self.storage.delete_schema_snapshot_by_cache_key(cache_key)

    def list_schema_snapshots(
        self, workspace_id: str, limit: int = 50
    ) -> List[SchemaSnapshot]:
        """List schema snapshots for a workspace."""

        return self.storage.list_schema_snapshots(workspace_id, limit=limit)

    # --- Graph set operations (PRD v0.6 / FR-68..FR-70) ---

    def create_graph_set(self, graph_set: GraphSet) -> str:
        """Insert a graph set."""

        return self.storage.insert_graph_set(graph_set)

    def get_graph_set(self, graph_set_id: str) -> GraphSet:
        """Get a graph set by ID."""

        return self.storage.get_graph_set(graph_set_id)

    def update_graph_set(self, graph_set: GraphSet) -> str:
        """Update a graph set."""

        return self.storage.update_graph_set(graph_set)

    def list_graph_sets(self, workspace_id: str) -> List[GraphSet]:
        """List graph sets for a workspace."""

        return self.storage.list_graph_sets(workspace_id)

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


class WorkspaceSchemaCache:
    """L2 cache adapter implementing the ``SchemaCache`` Protocol.

    PRD v0.6 / FR-59. Bridges :mod:`graph_analytics_ai.ai.schema.acquire`
    to a :class:`ProductRepository` without an inverse import:
    ``acquire.py`` only knows about the ``SchemaCache`` Protocol;
    this class supplies the concrete ArangoDB-backed implementation.

    Each ``WorkspaceSchemaCache`` is bound to a single workspace so
    rows written via :meth:`set` carry the right ``workspace_id``
    even though the acquisition module has no concept of workspaces.

    The cache is *write-through-by-key*: ``set(key, bundle)`` upserts
    the row keyed by ``cache_key`` (the same hash the in-memory
    :class:`InMemorySchemaCache` uses), bumping ``updated_at`` so the
    most-recent-wins lookup in
    :meth:`ProductRepository.get_schema_snapshot_by_cache_key`
    returns the freshly persisted row.

    Failures inside :meth:`set` are caught by the acquisition module's
    :func:`_persist_layered`, so a transient storage outage degrades
    to L1-only caching rather than blocking the discovery flow.
    """

    def __init__(self, repository: ProductRepository, workspace_id: str) -> None:
        self._repository = repository
        self._workspace_id = workspace_id

    @property
    def workspace_id(self) -> str:
        """The workspace this cache is scoped to."""

        return self._workspace_id

    def get(self, key: str):
        """Return the cached bundle for ``key`` or ``None`` on miss."""

        # Late import: acquire is in the AI subtree, repository is in
        # the product subtree, and product imports from ai are tightly
        # restricted. Lazy import keeps the dependency at runtime, not
        # at module-load time.
        from graph_analytics_ai.ai.schema.acquire import SchemaAcquisitionBundle

        snapshot = self._repository.get_schema_snapshot_by_cache_key(key)
        if snapshot is None:
            return None
        return SchemaAcquisitionBundle(
            schema_kind=snapshot.schema_kind,  # type: ignore[arg-type]
            conceptual_schema=dict(snapshot.conceptual_schema),
            physical_mapping=dict(snapshot.physical_mapping),
            analyzer_metadata=dict(snapshot.analyzer_metadata),
            shape_fingerprint=snapshot.shape_fingerprint,
            full_fingerprint=snapshot.full_fingerprint,
            database=snapshot.database,
            graph_name=snapshot.graph_name,
        )

    def set(self, key: str, bundle) -> None:
        """Upsert a snapshot row for ``key`` with the supplied bundle."""

        existing = self._repository.get_schema_snapshot_by_cache_key(key)
        if existing is not None:
            # Update the most recent row in place. A previous workspace
            # may have persisted a different schema_kind / mapping for
            # the same key; the bundle now becomes the authoritative
            # one. We do not version snapshot rows — the acquisition
            # module keeps a fresh fingerprint pair, which is the only
            # versioning the cache contract needs.
            existing.cache_key = key
            existing.database = bundle.database
            existing.graph_name = bundle.graph_name
            existing.schema_kind = bundle.schema_kind
            existing.shape_fingerprint = bundle.shape_fingerprint
            existing.full_fingerprint = bundle.full_fingerprint
            existing.conceptual_schema = bundle.conceptual_schema
            existing.physical_mapping = bundle.physical_mapping
            existing.analyzer_metadata = bundle.analyzer_metadata
            try:
                self._repository.update_schema_snapshot(existing)
            except Exception:
                logger.warning(
                    "WorkspaceSchemaCache.set: update failed for %s; "
                    "will fall back to L1-only caching",
                    key,
                    exc_info=True,
                )
            return

        snapshot = create_schema_snapshot(
            workspace_id=self._workspace_id,
            cache_key=key,
            database=bundle.database,
            graph_name=bundle.graph_name,
            schema_kind=bundle.schema_kind,
            shape_fingerprint=bundle.shape_fingerprint,
            full_fingerprint=bundle.full_fingerprint,
            conceptual_schema=bundle.conceptual_schema,
            physical_mapping=bundle.physical_mapping,
            analyzer_metadata=bundle.analyzer_metadata,
        )
        try:
            self._repository.create_schema_snapshot(snapshot)
        except Exception:
            logger.warning(
                "WorkspaceSchemaCache.set: insert failed for %s; "
                "will fall back to L1-only caching",
                key,
                exc_info=True,
            )

    def invalidate(self, key: str) -> None:
        """Drop every snapshot row for ``key``. Idempotent."""

        try:
            self._repository.delete_schema_snapshot_by_cache_key(key)
        except Exception:
            logger.warning(
                "WorkspaceSchemaCache.invalidate: delete failed for %s",
                key,
                exc_info=True,
            )

