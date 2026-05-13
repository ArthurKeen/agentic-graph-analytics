"""ArangoDB storage for UI product metadata."""

import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional

from arango.database import StandardDatabase
from arango.exceptions import DocumentGetError, DocumentInsertError, DocumentUpdateError

from ..constants import (
    AUDIT_EVENTS_COLLECTION,
    CHART_SPECS_COLLECTION,
    COLLECTION_ROLES_COLLECTION,
    CONNECTION_PROFILES_COLLECTION,
    DOCUMENTS_COLLECTION,
    GRAPH_PROFILES_COLLECTION,
    META_COLLECTION,
    PRODUCT_COLLECTIONS,
    PRODUCT_SCHEMA_VERSION,
    PUBLISHED_SNAPSHOTS_COLLECTION,
    REPORT_MANIFESTS_COLLECTION,
    REPORT_SECTIONS_COLLECTION,
    REQUIREMENT_INTERVIEWS_COLLECTION,
    REQUIREMENT_VERSIONS_COLLECTION,
    SCHEMA_SNAPSHOTS_COLLECTION,
    WORKFLOW_RUNS_COLLECTION,
    WORKSPACES_COLLECTION,
)
from ..exceptions import DuplicateError, NotFoundError, StorageError
from ..models import (
    AuditEvent,
    ChartSpec,
    ConnectionProfile,
    GraphProfile,
    PublishedSnapshot,
    ReportManifest,
    ReportSection,
    RequirementInterview,
    RequirementVersion,
    SchemaSnapshot,
    SourceDocument,
    Workspace,
    WorkflowRun,
)

logger = logging.getLogger(__name__)


class ProductArangoStorage:
    """ArangoDB-backed storage for product UI metadata.

    This storage owns only `aga_*` collections and intentionally leaves the
    existing `analysis_*` catalog collections to the Analysis Catalog backend.
    """

    META_COLLECTION = META_COLLECTION
    WORKSPACES_COLLECTION = WORKSPACES_COLLECTION
    CONNECTION_PROFILES_COLLECTION = CONNECTION_PROFILES_COLLECTION
    GRAPH_PROFILES_COLLECTION = GRAPH_PROFILES_COLLECTION
    DOCUMENTS_COLLECTION = DOCUMENTS_COLLECTION
    REQUIREMENT_INTERVIEWS_COLLECTION = REQUIREMENT_INTERVIEWS_COLLECTION
    REQUIREMENT_VERSIONS_COLLECTION = REQUIREMENT_VERSIONS_COLLECTION
    WORKFLOW_RUNS_COLLECTION = WORKFLOW_RUNS_COLLECTION
    REPORT_MANIFESTS_COLLECTION = REPORT_MANIFESTS_COLLECTION
    REPORT_SECTIONS_COLLECTION = REPORT_SECTIONS_COLLECTION
    CHART_SPECS_COLLECTION = CHART_SPECS_COLLECTION
    PUBLISHED_SNAPSHOTS_COLLECTION = PUBLISHED_SNAPSHOTS_COLLECTION
    AUDIT_EVENTS_COLLECTION = AUDIT_EVENTS_COLLECTION
    SCHEMA_SNAPSHOTS_COLLECTION = SCHEMA_SNAPSHOTS_COLLECTION

    def __init__(self, db: StandardDatabase, auto_initialize: bool = True):
        """Initialize product storage."""

        self.db = db
        self._lock = Lock()

        if auto_initialize:
            self.initialize_collections()

    def initialize_collections(self) -> None:
        """Create product collections and indexes if they do not exist."""

        try:
            for collection_name in PRODUCT_COLLECTIONS:
                if not self.db.has_collection(collection_name):
                    self.db.create_collection(collection_name)
                    logger.info("Created product collection: %s", collection_name)

            self._create_indexes()
            self._write_schema_version()
        except Exception as exc:
            raise StorageError(f"Failed to initialize product collections: {exc}") from exc

    def _write_schema_version(self) -> None:
        """Store the product schema version as an idempotent metadata document."""

        collection = self.db.collection(META_COLLECTION)
        doc = {
            "_key": "schema",
            "schema_version": PRODUCT_SCHEMA_VERSION,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if collection.has("schema"):
            collection.update(doc)
        else:
            collection.insert(doc)

    def _create_indexes(self) -> None:
        """Create indexes used by dashboard and API queries."""

        try:
            self.db.collection(WORKSPACES_COLLECTION).add_hash_index(
                fields=["status"], unique=False
            )
            self.db.collection(WORKSPACES_COLLECTION).add_skiplist_index(
                fields=["created_at"], unique=False
            )

            connections = self.db.collection(CONNECTION_PROFILES_COLLECTION)
            connections.add_hash_index(fields=["workspace_id"], unique=False)
            connections.add_hash_index(
                fields=["workspace_id", "name"], unique=False
            )
            connections.add_hash_index(
                fields=["last_verification_status"], unique=False
            )

            for collection_name in [
                GRAPH_PROFILES_COLLECTION,
                COLLECTION_ROLES_COLLECTION,
                DOCUMENTS_COLLECTION,
                REQUIREMENT_INTERVIEWS_COLLECTION,
                REQUIREMENT_VERSIONS_COLLECTION,
                WORKFLOW_RUNS_COLLECTION,
                REPORT_MANIFESTS_COLLECTION,
                REPORT_SECTIONS_COLLECTION,
                CHART_SPECS_COLLECTION,
                PUBLISHED_SNAPSHOTS_COLLECTION,
                AUDIT_EVENTS_COLLECTION,
            ]:
                collection = self.db.collection(collection_name)
                collection.add_hash_index(fields=["workspace_id"], unique=False)

            self.db.collection(DOCUMENTS_COLLECTION).add_hash_index(
                fields=["workspace_id", "sha256"], unique=False
            )
            self.db.collection(REQUIREMENT_INTERVIEWS_COLLECTION).add_hash_index(
                fields=["graph_profile_id"], unique=False
            )
            self.db.collection(REQUIREMENT_VERSIONS_COLLECTION).add_hash_index(
                fields=["analysis_requirements_id"], unique=False
            )
            self.db.collection(WORKFLOW_RUNS_COLLECTION).add_hash_index(
                fields=["status"], unique=False
            )
            self.db.collection(WORKFLOW_RUNS_COLLECTION).add_hash_index(
                fields=["requirement_version_id"], unique=False
            )
            self.db.collection(REPORT_MANIFESTS_COLLECTION).add_hash_index(
                fields=["run_id"], unique=False
            )
            self.db.collection(REPORT_SECTIONS_COLLECTION).add_hash_index(
                fields=["report_id"], unique=False
            )
            self.db.collection(CHART_SPECS_COLLECTION).add_hash_index(
                fields=["report_id"], unique=False
            )
            self.db.collection(PUBLISHED_SNAPSHOTS_COLLECTION).add_hash_index(
                fields=["report_id"], unique=False
            )
            self.db.collection(AUDIT_EVENTS_COLLECTION).add_skiplist_index(
                fields=["timestamp"], unique=False
            )
            # PRD v0.6: cache_key is the SchemaCache lookup field used
            # by every acquire_schema call. Hash index is non-unique
            # because (workspace_id, database, graph_name) → cache_key
            # is deterministic but a workspace-clone flow could legally
            # produce two rows for the same logical key during the
            # transition. Lookups always select the most recent by
            # ``updated_at`` so duplicates are tolerated, not enforced.
            schema_snapshots = self.db.collection(SCHEMA_SNAPSHOTS_COLLECTION)
            schema_snapshots.add_hash_index(fields=["cache_key"], unique=False)
            schema_snapshots.add_hash_index(
                fields=["workspace_id", "database"], unique=False
            )
            schema_snapshots.add_hash_index(fields=["schema_kind"], unique=False)
        except Exception as exc:
            logger.warning("Failed to create some product indexes: %s", exc)

    # --- Workspace operations ---

    def _insert_document(self, collection_name: str, doc: Dict[str, Any]) -> str:
        """Insert a product metadata document."""

        with self._lock:
            try:
                self.db.collection(collection_name).insert(doc)
                return doc["_key"]
            except DocumentInsertError as exc:
                if "unique constraint violated" in str(exc).lower():
                    raise DuplicateError(
                        f"Document {doc['_key']} already exists in {collection_name}"
                    ) from exc
                raise StorageError(
                    f"Failed to insert document into {collection_name}: {exc}"
                ) from exc
            except Exception as exc:
                raise StorageError(
                    f"Failed to insert document into {collection_name}: {exc}"
                ) from exc

    def _get_document(self, collection_name: str, key: str) -> Dict[str, Any]:
        """Get a product metadata document by key."""

        try:
            doc = self.db.collection(collection_name).get(key)
            if doc is None:
                raise NotFoundError(f"Document {key} not found in {collection_name}")
            return doc
        except NotFoundError:
            raise
        except DocumentGetError as exc:
            raise NotFoundError(f"Document {key} not found in {collection_name}") from exc
        except Exception as exc:
            raise StorageError(
                f"Failed to get document {key} from {collection_name}: {exc}"
            ) from exc

    def _update_document(self, collection_name: str, doc: Dict[str, Any]) -> str:
        """Update a product metadata document."""

        with self._lock:
            try:
                self.db.collection(collection_name).update(doc)
                return doc["_key"]
            except DocumentUpdateError as exc:
                raise StorageError(
                    f"Failed to update document in {collection_name}: {exc}"
                ) from exc

    def _list_workspace_documents(
        self, collection_name: str, workspace_id: str, sort_field: str = "updated_at"
    ) -> List[Dict[str, Any]]:
        """List product metadata documents scoped to a workspace."""

        query = f"""
        FOR doc IN {collection_name}
            FILTER doc.workspace_id == @workspace_id
            SORT doc.{sort_field} DESC
            RETURN doc
        """

        try:
            cursor = self.db.aql.execute(
                query, bind_vars={"workspace_id": workspace_id}
            )
            return list(cursor)
        except Exception as exc:
            raise StorageError(
                f"Failed to list documents from {collection_name}: {exc}"
            ) from exc

    def insert_workspace(self, workspace: Workspace) -> str:
        """Insert a workspace."""

        with self._lock:
            try:
                self.db.collection(WORKSPACES_COLLECTION).insert(workspace.to_dict())
                return workspace.workspace_id
            except DocumentInsertError as exc:
                if "unique constraint violated" in str(exc).lower():
                    raise DuplicateError(
                        f"Workspace {workspace.workspace_id} already exists"
                    ) from exc
                raise StorageError(f"Failed to insert workspace: {exc}") from exc
            except Exception as exc:
                raise StorageError(f"Failed to insert workspace: {exc}") from exc

    def get_workspace(self, workspace_id: str) -> Workspace:
        """Get a workspace by ID."""

        try:
            doc = self.db.collection(WORKSPACES_COLLECTION).get(workspace_id)
            if doc is None:
                raise NotFoundError(f"Workspace {workspace_id} not found")
            return Workspace.from_dict(doc)
        except NotFoundError:
            raise
        except DocumentGetError as exc:
            raise NotFoundError(f"Workspace {workspace_id} not found") from exc
        except Exception as exc:
            raise StorageError(f"Failed to get workspace: {exc}") from exc

    def update_workspace(self, workspace: Workspace) -> str:
        """Update a workspace."""

        workspace.updated_at = datetime.now(timezone.utc)
        with self._lock:
            try:
                self.db.collection(WORKSPACES_COLLECTION).update(workspace.to_dict())
                return workspace.workspace_id
            except DocumentUpdateError as exc:
                raise StorageError(f"Failed to update workspace: {exc}") from exc

    def list_workspaces(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[Workspace]:
        """List workspaces, optionally filtered by status."""

        query = f"FOR doc IN {WORKSPACES_COLLECTION}"
        bind_vars: Dict[str, Any] = {"limit": limit}

        if status:
            query += " FILTER doc.status == @status"
            bind_vars["status"] = status

        query += " SORT doc.updated_at DESC LIMIT @limit RETURN doc"

        try:
            cursor = self.db.aql.execute(query, bind_vars=bind_vars)
            return [Workspace.from_dict(doc) for doc in cursor]
        except Exception as exc:
            raise StorageError(f"Failed to list workspaces: {exc}") from exc

    # --- Connection profile operations ---

    def insert_connection_profile(self, profile: ConnectionProfile) -> str:
        """Insert a connection profile."""

        with self._lock:
            try:
                self.db.collection(CONNECTION_PROFILES_COLLECTION).insert(
                    profile.to_dict()
                )
                return profile.connection_profile_id
            except DocumentInsertError as exc:
                if "unique constraint violated" in str(exc).lower():
                    raise DuplicateError(
                        f"Connection profile {profile.connection_profile_id} already exists"
                    ) from exc
                raise StorageError(
                    f"Failed to insert connection profile: {exc}"
                ) from exc
            except Exception as exc:
                raise StorageError(
                    f"Failed to insert connection profile: {exc}"
                ) from exc

    def get_connection_profile(self, connection_profile_id: str) -> ConnectionProfile:
        """Get a connection profile by ID."""

        try:
            doc = self.db.collection(CONNECTION_PROFILES_COLLECTION).get(
                connection_profile_id
            )
            if doc is None:
                raise NotFoundError(
                    f"Connection profile {connection_profile_id} not found"
                )
            return ConnectionProfile.from_dict(doc)
        except NotFoundError:
            raise
        except DocumentGetError as exc:
            raise NotFoundError(
                f"Connection profile {connection_profile_id} not found"
            ) from exc
        except Exception as exc:
            raise StorageError(f"Failed to get connection profile: {exc}") from exc

    def update_connection_profile(self, profile: ConnectionProfile) -> str:
        """Update a connection profile."""

        profile.updated_at = datetime.now(timezone.utc)
        with self._lock:
            try:
                self.db.collection(CONNECTION_PROFILES_COLLECTION).update(
                    profile.to_dict()
                )
                return profile.connection_profile_id
            except DocumentUpdateError as exc:
                raise StorageError(
                    f"Failed to update connection profile: {exc}"
                ) from exc

    def list_connection_profiles(self, workspace_id: str) -> List[ConnectionProfile]:
        """List connection profiles for a workspace."""

        query = f"""
        FOR doc IN {CONNECTION_PROFILES_COLLECTION}
            FILTER doc.workspace_id == @workspace_id
            SORT doc.updated_at DESC
            RETURN doc
        """

        try:
            cursor = self.db.aql.execute(
                query, bind_vars={"workspace_id": workspace_id}
            )
            return [ConnectionProfile.from_dict(doc) for doc in cursor]
        except Exception as exc:
            raise StorageError(f"Failed to list connection profiles: {exc}") from exc

    # --- Graph profile operations ---

    def insert_graph_profile(self, profile: GraphProfile) -> str:
        """Insert a graph profile."""

        return self._insert_document(GRAPH_PROFILES_COLLECTION, profile.to_dict())

    def get_graph_profile(self, graph_profile_id: str) -> GraphProfile:
        """Get a graph profile by ID."""

        return GraphProfile.from_dict(
            self._get_document(GRAPH_PROFILES_COLLECTION, graph_profile_id)
        )

    def update_graph_profile(self, profile: GraphProfile) -> str:
        """Update a graph profile."""

        profile.updated_at = datetime.now(timezone.utc)
        return self._update_document(GRAPH_PROFILES_COLLECTION, profile.to_dict())

    def list_graph_profiles(self, workspace_id: str) -> List[GraphProfile]:
        """List graph profiles for a workspace."""

        docs = self._list_workspace_documents(GRAPH_PROFILES_COLLECTION, workspace_id)
        return [GraphProfile.from_dict(doc) for doc in docs]

    # --- Schema snapshot operations (PRD v0.6 / FR-59) ---
    #
    # These methods are the persistence side of the L2 SchemaCache used
    # by graph_analytics_ai.ai.schema.acquire. The cache adapter
    # itself lives in repository.py so the acquisition module never
    # imports the storage module.

    def insert_schema_snapshot(self, snapshot: SchemaSnapshot) -> str:
        """Insert a schema snapshot row."""

        return self._insert_document(
            SCHEMA_SNAPSHOTS_COLLECTION, snapshot.to_dict()
        )

    def get_schema_snapshot(self, schema_snapshot_id: str) -> SchemaSnapshot:
        """Get a schema snapshot by ID."""

        return SchemaSnapshot.from_dict(
            self._get_document(SCHEMA_SNAPSHOTS_COLLECTION, schema_snapshot_id)
        )

    def update_schema_snapshot(self, snapshot: SchemaSnapshot) -> str:
        """Update a schema snapshot row.

        Bumps ``updated_at`` so the most-recent-wins lookup in
        :meth:`get_schema_snapshot_by_cache_key` returns this row.
        """

        snapshot.updated_at = datetime.now(timezone.utc)
        return self._update_document(
            SCHEMA_SNAPSHOTS_COLLECTION, snapshot.to_dict()
        )

    def get_schema_snapshot_by_cache_key(
        self, cache_key: str
    ) -> Optional[SchemaSnapshot]:
        """Look up the most recent snapshot for a cache key, or None.

        Returns the freshest snapshot when multiple rows exist for the
        same key (the workspace-clone edge case described in
        ``_create_indexes``). Returns ``None`` on a miss; callers must
        not raise.
        """

        query = f"""
        FOR doc IN {SCHEMA_SNAPSHOTS_COLLECTION}
            FILTER doc.cache_key == @cache_key
            SORT doc.updated_at DESC
            LIMIT 1
            RETURN doc
        """

        try:
            cursor = self.db.aql.execute(query, bind_vars={"cache_key": cache_key})
            for doc in cursor:
                return SchemaSnapshot.from_dict(doc)
            return None
        except Exception as exc:
            raise StorageError(
                f"Failed to look up schema snapshot by cache_key: {exc}"
            ) from exc

    def delete_schema_snapshot_by_cache_key(self, cache_key: str) -> int:
        """Delete every snapshot row for a cache key. Returns count removed.

        Used by the manual-invalidate path (``invalidate_schema_cache``)
        and by the future workspace-archive teardown.
        """

        query = f"""
        FOR doc IN {SCHEMA_SNAPSHOTS_COLLECTION}
            FILTER doc.cache_key == @cache_key
            REMOVE doc IN {SCHEMA_SNAPSHOTS_COLLECTION}
            RETURN OLD._key
        """

        try:
            cursor = self.db.aql.execute(query, bind_vars={"cache_key": cache_key})
            return sum(1 for _ in cursor)
        except Exception as exc:
            raise StorageError(
                f"Failed to delete schema snapshots: {exc}"
            ) from exc

    def list_schema_snapshots(
        self, workspace_id: str, limit: int = 50
    ) -> List[SchemaSnapshot]:
        """List schema snapshots for a workspace, freshest first.

        Used by the dashboard / Graph Explorer view that surfaces a
        workspace's known schemas alongside its graph profiles.
        """

        query = f"""
        FOR doc IN {SCHEMA_SNAPSHOTS_COLLECTION}
            FILTER doc.workspace_id == @workspace_id
            SORT doc.updated_at DESC
            LIMIT @limit
            RETURN doc
        """

        try:
            cursor = self.db.aql.execute(
                query,
                bind_vars={"workspace_id": workspace_id, "limit": limit},
            )
            return [SchemaSnapshot.from_dict(doc) for doc in cursor]
        except Exception as exc:
            raise StorageError(
                f"Failed to list schema snapshots: {exc}"
            ) from exc

    # --- Source document operations ---

    def insert_source_document(self, document: SourceDocument) -> str:
        """Insert a source document."""

        return self._insert_document(DOCUMENTS_COLLECTION, document.to_dict())

    def get_source_document(self, document_id: str) -> SourceDocument:
        """Get a source document by ID."""

        return SourceDocument.from_dict(
            self._get_document(DOCUMENTS_COLLECTION, document_id)
        )

    def list_source_documents(self, workspace_id: str) -> List[SourceDocument]:
        """List source documents for a workspace."""

        docs = self._list_workspace_documents(
            DOCUMENTS_COLLECTION, workspace_id, sort_field="uploaded_at"
        )
        return [SourceDocument.from_dict(doc) for doc in docs]

    # --- Requirements Copilot interview operations ---

    def insert_requirement_interview(self, interview: RequirementInterview) -> str:
        """Insert a Requirements Copilot interview."""

        return self._insert_document(
            REQUIREMENT_INTERVIEWS_COLLECTION, interview.to_dict()
        )

    def get_requirement_interview(
        self, requirement_interview_id: str
    ) -> RequirementInterview:
        """Get a Requirements Copilot interview by ID."""

        return RequirementInterview.from_dict(
            self._get_document(
                REQUIREMENT_INTERVIEWS_COLLECTION, requirement_interview_id
            )
        )

    def update_requirement_interview(self, interview: RequirementInterview) -> str:
        """Update a Requirements Copilot interview."""

        interview.updated_at = datetime.now(timezone.utc)
        return self._update_document(
            REQUIREMENT_INTERVIEWS_COLLECTION, interview.to_dict()
        )

    def list_requirement_interviews(
        self, workspace_id: str
    ) -> List[RequirementInterview]:
        """List Requirements Copilot interviews for a workspace."""

        docs = self._list_workspace_documents(
            REQUIREMENT_INTERVIEWS_COLLECTION, workspace_id
        )
        return [RequirementInterview.from_dict(doc) for doc in docs]

    # --- Requirement version operations ---

    def insert_requirement_version(self, version: RequirementVersion) -> str:
        """Insert a requirement version."""

        return self._insert_document(REQUIREMENT_VERSIONS_COLLECTION, version.to_dict())

    def get_requirement_version(self, requirement_version_id: str) -> RequirementVersion:
        """Get a requirement version by ID."""

        return RequirementVersion.from_dict(
            self._get_document(REQUIREMENT_VERSIONS_COLLECTION, requirement_version_id)
        )

    def update_requirement_version(self, version: RequirementVersion) -> str:
        """Update a requirement version."""

        version.updated_at = datetime.now(timezone.utc)
        return self._update_document(
            REQUIREMENT_VERSIONS_COLLECTION, version.to_dict()
        )

    def list_requirement_versions(self, workspace_id: str) -> List[RequirementVersion]:
        """List requirement versions for a workspace."""

        docs = self._list_workspace_documents(
            REQUIREMENT_VERSIONS_COLLECTION, workspace_id
        )
        return [RequirementVersion.from_dict(doc) for doc in docs]

    # --- Workflow run operations ---

    def insert_workflow_run(self, run: WorkflowRun) -> str:
        """Insert a workflow run."""

        return self._insert_document(WORKFLOW_RUNS_COLLECTION, run.to_dict())

    def get_workflow_run(self, run_id: str) -> WorkflowRun:
        """Get a workflow run by ID."""

        return WorkflowRun.from_dict(
            self._get_document(WORKFLOW_RUNS_COLLECTION, run_id)
        )

    def update_workflow_run(self, run: WorkflowRun) -> str:
        """Update a workflow run."""

        run.updated_at = datetime.now(timezone.utc)
        return self._update_document(WORKFLOW_RUNS_COLLECTION, run.to_dict())

    def list_workflow_runs(self, workspace_id: str) -> List[WorkflowRun]:
        """List workflow runs for a workspace."""

        docs = self._list_workspace_documents(WORKFLOW_RUNS_COLLECTION, workspace_id)
        return [WorkflowRun.from_dict(doc) for doc in docs]

    # --- Report operations ---

    def insert_report_manifest(self, manifest: ReportManifest) -> str:
        """Insert a report manifest."""

        return self._insert_document(REPORT_MANIFESTS_COLLECTION, manifest.to_dict())

    def get_report_manifest(self, report_id: str) -> ReportManifest:
        """Get a report manifest by ID."""

        return ReportManifest.from_dict(
            self._get_document(REPORT_MANIFESTS_COLLECTION, report_id)
        )

    def update_report_manifest(self, manifest: ReportManifest) -> str:
        """Update a report manifest."""

        manifest.updated_at = datetime.now(timezone.utc)
        return self._update_document(REPORT_MANIFESTS_COLLECTION, manifest.to_dict())

    def list_report_manifests(self, workspace_id: str) -> List[ReportManifest]:
        """List report manifests for a workspace."""

        docs = self._list_workspace_documents(REPORT_MANIFESTS_COLLECTION, workspace_id)
        return [ReportManifest.from_dict(doc) for doc in docs]

    def insert_report_section(self, section: ReportSection) -> str:
        """Insert a report section."""

        return self._insert_document(REPORT_SECTIONS_COLLECTION, section.to_dict())

    def get_report_section(self, section_id: str) -> ReportSection:
        """Get a report section by ID."""

        return ReportSection.from_dict(
            self._get_document(REPORT_SECTIONS_COLLECTION, section_id)
        )

    def list_report_sections(self, report_id: str) -> List[ReportSection]:
        """List report sections for a report ordered by section order."""

        query = f"""
        FOR doc IN {REPORT_SECTIONS_COLLECTION}
            FILTER doc.report_id == @report_id
            SORT doc.order ASC
            RETURN doc
        """

        try:
            cursor = self.db.aql.execute(query, bind_vars={"report_id": report_id})
            return [ReportSection.from_dict(doc) for doc in cursor]
        except Exception as exc:
            raise StorageError(f"Failed to list report sections: {exc}") from exc

    def insert_chart_spec(self, chart: ChartSpec) -> str:
        """Insert a chart spec."""

        return self._insert_document(CHART_SPECS_COLLECTION, chart.to_dict())

    def get_chart_spec(self, chart_id: str) -> ChartSpec:
        """Get a chart spec by ID."""

        return ChartSpec.from_dict(self._get_document(CHART_SPECS_COLLECTION, chart_id))

    def list_chart_specs(self, report_id: str) -> List[ChartSpec]:
        """List chart specs for a report."""

        query = f"""
        FOR doc IN {CHART_SPECS_COLLECTION}
            FILTER doc.report_id == @report_id
            SORT doc.title ASC
            RETURN doc
        """

        try:
            cursor = self.db.aql.execute(query, bind_vars={"report_id": report_id})
            return [ChartSpec.from_dict(doc) for doc in cursor]
        except Exception as exc:
            raise StorageError(f"Failed to list chart specs: {exc}") from exc

    def insert_published_snapshot(self, snapshot: PublishedSnapshot) -> str:
        """Insert a published report snapshot."""

        return self._insert_document(
            PUBLISHED_SNAPSHOTS_COLLECTION,
            snapshot.to_dict(),
        )

    def get_published_snapshot(self, published_snapshot_id: str) -> PublishedSnapshot:
        """Get a published report snapshot by ID."""

        return PublishedSnapshot.from_dict(
            self._get_document(PUBLISHED_SNAPSHOTS_COLLECTION, published_snapshot_id)
        )

    def list_published_snapshots(self, report_id: str) -> List[PublishedSnapshot]:
        """List published snapshots for a report."""

        query = f"""
        FOR doc IN {PUBLISHED_SNAPSHOTS_COLLECTION}
            FILTER doc.report_id == @report_id
            SORT doc.published_at DESC
            RETURN doc
        """

        try:
            cursor = self.db.aql.execute(query, bind_vars={"report_id": report_id})
            return [PublishedSnapshot.from_dict(doc) for doc in cursor]
        except Exception as exc:
            raise StorageError(f"Failed to list published snapshots: {exc}") from exc

    # --- Audit operations ---

    def insert_audit_event(self, event: AuditEvent) -> str:
        """Insert an audit event."""

        return self._insert_document(AUDIT_EVENTS_COLLECTION, event.to_dict())

    def list_audit_events(self, workspace_id: str, limit: int = 100) -> List[AuditEvent]:
        """List audit events for a workspace."""

        query = f"""
        FOR doc IN {AUDIT_EVENTS_COLLECTION}
            FILTER doc.workspace_id == @workspace_id
            SORT doc.timestamp DESC
            LIMIT @limit
            RETURN doc
        """

        try:
            cursor = self.db.aql.execute(
                query,
                bind_vars={"workspace_id": workspace_id, "limit": limit},
            )
            return [AuditEvent.from_dict(doc) for doc in cursor]
        except Exception as exc:
            raise StorageError(f"Failed to list audit events: {exc}") from exc

    def reset(self, confirm: bool = False) -> None:
        """Delete all product metadata documents.

        This only truncates `aga_*` product collections. It never modifies
        `analysis_*` catalog collections or customer graph data.
        """

        if not confirm:
            raise ValueError("reset requires confirm=True")

        for collection_name in PRODUCT_COLLECTIONS:
            if self.db.has_collection(collection_name):
                self.db.collection(collection_name).truncate()

    def close(self) -> None:
        """Close the storage backend."""

        # python-arango database handles do not require explicit close.
        return None

