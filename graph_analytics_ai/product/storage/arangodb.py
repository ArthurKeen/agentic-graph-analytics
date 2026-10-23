"""ArangoDB storage for UI product metadata."""

import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional

from arango.database import StandardDatabase

from ...arango_index import IndexSpec, ensure_persistent_indexes
from arango.exceptions import DocumentGetError, DocumentInsertError, DocumentUpdateError

from ..constants import (
    ANALYSIS_EPOCHS_COLLECTION,
    USE_CASES_COLLECTION,
    ANALYSIS_EXECUTIONS_COLLECTION,
    ANALYSIS_TEMPLATES_COLLECTION,
    RETENTION_POLICIES_COLLECTION,
    AUDIT_EVENTS_COLLECTION,
    CHART_SPECS_COLLECTION,
    COLLECTION_ROLES_COLLECTION,
    CONNECTION_PROFILES_COLLECTION,
    DOCUMENTS_COLLECTION,
    GRAPH_PROFILES_COLLECTION,
    GRAPH_SETS_COLLECTION,
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
    AnalysisEpoch,
    AnalysisExecution,
    AnalysisTemplate,
    AuditEvent,
    RetentionPolicy,
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
    UseCase,
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
    GRAPH_SETS_COLLECTION = GRAPH_SETS_COLLECTION
    ANALYSIS_EXECUTIONS_COLLECTION = ANALYSIS_EXECUTIONS_COLLECTION
    ANALYSIS_EPOCHS_COLLECTION = ANALYSIS_EPOCHS_COLLECTION
    USE_CASES_COLLECTION = USE_CASES_COLLECTION
    ANALYSIS_TEMPLATES_COLLECTION = ANALYSIS_TEMPLATES_COLLECTION
    RETENTION_POLICIES_COLLECTION = RETENTION_POLICIES_COLLECTION

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
            raise StorageError(
                f"Failed to initialize product collections: {exc}"
            ) from exc

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
        """Create indexes used by dashboard and API queries (NFR-12).

        Declared as data rather than 50 imperative calls so the set is
        reviewable at a glance and testable without a database. Every index is
        persistent: `add_hash_index`/`add_skiplist_index` were removed in
        python-arango 8, and a persistent index serves both the equality
        lookups hash provided and the range/sort access skiplist provided.
        """

        workspace_scoped = [
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
            ANALYSIS_EXECUTIONS_COLLECTION,
            ANALYSIS_EPOCHS_COLLECTION,
            USE_CASES_COLLECTION,
            ANALYSIS_TEMPLATES_COLLECTION,
            RETENTION_POLICIES_COLLECTION,
        ]

        specs = [IndexSpec(name, ["workspace_id"]) for name in workspace_scoped]
        specs += [
            IndexSpec(WORKSPACES_COLLECTION, ["status"]),
            IndexSpec(WORKSPACES_COLLECTION, ["created_at"]),
            IndexSpec(CONNECTION_PROFILES_COLLECTION, ["workspace_id"]),
            IndexSpec(CONNECTION_PROFILES_COLLECTION, ["workspace_id", "name"]),
            IndexSpec(CONNECTION_PROFILES_COLLECTION, ["last_verification_status"]),
            IndexSpec(DOCUMENTS_COLLECTION, ["workspace_id", "sha256"]),
            IndexSpec(REQUIREMENT_INTERVIEWS_COLLECTION, ["graph_profile_id"]),
            IndexSpec(REQUIREMENT_VERSIONS_COLLECTION, ["analysis_requirements_id"]),
            IndexSpec(WORKFLOW_RUNS_COLLECTION, ["status"]),
            IndexSpec(WORKFLOW_RUNS_COLLECTION, ["requirement_version_id"]),
            IndexSpec(REPORT_MANIFESTS_COLLECTION, ["run_id"]),
            IndexSpec(REPORT_SECTIONS_COLLECTION, ["report_id"]),
            IndexSpec(CHART_SPECS_COLLECTION, ["report_id"]),
            IndexSpec(PUBLISHED_SNAPSHOTS_COLLECTION, ["report_id"]),
            IndexSpec(AUDIT_EVENTS_COLLECTION, ["timestamp"]),
            # FR-25: template version chains resolve by lineage_id; use cases
            # are filtered by status in the review queue.
            IndexSpec(ANALYSIS_TEMPLATES_COLLECTION, ["lineage_id"]),
            IndexSpec(ANALYSIS_TEMPLATES_COLLECTION, ["use_case_id"]),
            IndexSpec(USE_CASES_COLLECTION, ["workspace_id", "status"]),
            # PRD v0.6: cache_key is the SchemaCache lookup field used by every
            # acquire_schema call. Non-unique because
            # (workspace_id, database, graph_name) -> cache_key is deterministic
            # but a workspace-clone flow could legally produce two rows for the
            # same logical key during the transition. Lookups select the most
            # recent by updated_at, so duplicates are tolerated, not enforced.
            IndexSpec(SCHEMA_SNAPSHOTS_COLLECTION, ["cache_key"]),
            IndexSpec(SCHEMA_SNAPSHOTS_COLLECTION, ["workspace_id", "database"]),
            IndexSpec(SCHEMA_SNAPSHOTS_COLLECTION, ["schema_kind"]),
            # PRD v0.6 / FR-68: a workspace can host many graph sets, but the
            # workbench often filters by name. Non-unique on name -- the
            # workspace UI deduplicates client-side.
            IndexSpec(GRAPH_SETS_COLLECTION, ["workspace_id"]),
            IndexSpec(GRAPH_SETS_COLLECTION, ["workspace_id", "name"]),
            IndexSpec(ANALYSIS_EXECUTIONS_COLLECTION, ["run_id"]),
            IndexSpec(ANALYSIS_EXECUTIONS_COLLECTION, ["epoch_id"]),
            IndexSpec(ANALYSIS_EXECUTIONS_COLLECTION, ["workspace_id", "algorithm"]),
            IndexSpec(ANALYSIS_EXECUTIONS_COLLECTION, ["workspace_id", "status"]),
            IndexSpec(ANALYSIS_EXECUTIONS_COLLECTION, ["graph_profile_id"]),
            IndexSpec(ANALYSIS_EXECUTIONS_COLLECTION, ["started_at"]),
            IndexSpec(ANALYSIS_EPOCHS_COLLECTION, ["workspace_id", "name"]),
            IndexSpec(ANALYSIS_EPOCHS_COLLECTION, ["workspace_id", "status"]),
            IndexSpec(ANALYSIS_EPOCHS_COLLECTION, ["timestamp"]),
        ]

        ensure_persistent_indexes(
            self.db, specs, logger=logger, context="product indexes"
        )

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
            raise NotFoundError(
                f"Document {key} not found in {collection_name}"
            ) from exc
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

        return self._insert_document(SCHEMA_SNAPSHOTS_COLLECTION, snapshot.to_dict())

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
        return self._update_document(SCHEMA_SNAPSHOTS_COLLECTION, snapshot.to_dict())

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
            raise StorageError(f"Failed to delete schema snapshots: {exc}") from exc

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
            raise StorageError(f"Failed to list schema snapshots: {exc}") from exc

    # --- Graph set operations (PRD v0.6 / FR-68..FR-70) ---

    def insert_graph_set(self, graph_set: GraphSet) -> str:
        """Insert a graph set."""

        return self._insert_document(GRAPH_SETS_COLLECTION, graph_set.to_dict())

    def get_graph_set(self, graph_set_id: str) -> GraphSet:
        """Get a graph set by ID."""

        return GraphSet.from_dict(
            self._get_document(GRAPH_SETS_COLLECTION, graph_set_id)
        )

    def update_graph_set(self, graph_set: GraphSet) -> str:
        """Update a graph set."""

        graph_set.updated_at = datetime.now(timezone.utc)
        return self._update_document(GRAPH_SETS_COLLECTION, graph_set.to_dict())

    def list_graph_sets(self, workspace_id: str) -> List[GraphSet]:
        """List graph sets for a workspace, freshest first."""

        docs = self._list_workspace_documents(GRAPH_SETS_COLLECTION, workspace_id)
        return [GraphSet.from_dict(doc) for doc in docs]

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

    def get_requirement_version(
        self, requirement_version_id: str
    ) -> RequirementVersion:
        """Get a requirement version by ID."""

        return RequirementVersion.from_dict(
            self._get_document(REQUIREMENT_VERSIONS_COLLECTION, requirement_version_id)
        )

    def update_requirement_version(self, version: RequirementVersion) -> str:
        """Update a requirement version."""

        version.updated_at = datetime.now(timezone.utc)
        return self._update_document(REQUIREMENT_VERSIONS_COLLECTION, version.to_dict())

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

    def list_workflow_runs_by_status(self, status: Any) -> List[WorkflowRun]:
        """List workflow runs in a given status, across every workspace.

        Deliberately not workspace-scoped: the orphan sweep runs at supervisor
        startup, before any workspace is selected, and a run left RUNNING by a
        dead process is orphaned regardless of which workspace owns it.
        """

        status_value = getattr(status, "value", status)
        query = f"""
        FOR doc IN {WORKFLOW_RUNS_COLLECTION}
            FILTER doc.status == @status
            SORT doc.updated_at DESC
            RETURN doc
        """
        try:
            cursor = self.db.aql.execute(query, bind_vars={"status": status_value})
            return [WorkflowRun.from_dict(doc) for doc in cursor]
        except Exception as exc:  # noqa: BLE001 — surfaced as StorageError
            raise StorageError(
                f"Failed to list workflow runs with status '{status_value}': {exc}"
            ) from exc

    # --- Product Analysis Catalog operations (FR-31 / FR-45..FR-48) ---

    def insert_analysis_execution(self, execution: AnalysisExecution) -> str:
        """Insert a workspace-scoped analysis execution."""

        return self._insert_document(
            ANALYSIS_EXECUTIONS_COLLECTION, execution.to_dict()
        )

    def get_analysis_execution(self, analysis_execution_id: str) -> AnalysisExecution:
        """Get an analysis execution by ID."""

        return AnalysisExecution.from_dict(
            self._get_document(ANALYSIS_EXECUTIONS_COLLECTION, analysis_execution_id)
        )

    def update_analysis_execution(self, execution: AnalysisExecution) -> str:
        """Update an analysis execution."""

        execution.updated_at = datetime.now(timezone.utc)
        return self._update_document(
            ANALYSIS_EXECUTIONS_COLLECTION, execution.to_dict()
        )

    def list_analysis_executions(self, workspace_id: str) -> List[AnalysisExecution]:
        """List a workspace's executions, newest first."""

        docs = self._list_workspace_documents(
            ANALYSIS_EXECUTIONS_COLLECTION,
            workspace_id,
            sort_field="started_at",
        )
        return [AnalysisExecution.from_dict(doc) for doc in docs]

    def insert_analysis_epoch(self, epoch: AnalysisEpoch) -> str:
        """Insert a workspace-scoped analysis epoch."""

        return self._insert_document(ANALYSIS_EPOCHS_COLLECTION, epoch.to_dict())

    def get_analysis_epoch(self, analysis_epoch_id: str) -> AnalysisEpoch:
        """Get an analysis epoch by ID."""

        return AnalysisEpoch.from_dict(
            self._get_document(ANALYSIS_EPOCHS_COLLECTION, analysis_epoch_id)
        )

    def update_analysis_epoch(self, epoch: AnalysisEpoch) -> str:
        """Update an analysis epoch."""

        epoch.updated_at = datetime.now(timezone.utc)
        return self._update_document(ANALYSIS_EPOCHS_COLLECTION, epoch.to_dict())

    def list_analysis_epochs(self, workspace_id: str) -> List[AnalysisEpoch]:
        """List a workspace's epochs, newest first."""

        docs = self._list_workspace_documents(
            ANALYSIS_EPOCHS_COLLECTION,
            workspace_id,
            sort_field="timestamp",
        )
        return [AnalysisEpoch.from_dict(doc) for doc in docs]

    # --- Use case and analysis template operations (FR-19..FR-26) ---

    def insert_use_case(self, use_case: UseCase) -> str:
        """Insert a workspace-scoped use case."""

        return self._insert_document(USE_CASES_COLLECTION, use_case.to_dict())

    def get_use_case(self, use_case_id: str) -> UseCase:
        """Get a use case by ID."""

        return UseCase.from_dict(self._get_document(USE_CASES_COLLECTION, use_case_id))

    def update_use_case(self, use_case: UseCase) -> str:
        """Update a use case."""

        use_case.updated_at = datetime.now(timezone.utc)
        return self._update_document(USE_CASES_COLLECTION, use_case.to_dict())

    def list_use_cases(self, workspace_id: str) -> List[UseCase]:
        """List a workspace's use cases, newest first."""

        docs = self._list_workspace_documents(
            USE_CASES_COLLECTION,
            workspace_id,
            sort_field="created_at",
        )
        return [UseCase.from_dict(doc) for doc in docs]

    def insert_analysis_template(self, template: AnalysisTemplate) -> str:
        """Insert a workspace-scoped analysis template."""

        return self._insert_document(ANALYSIS_TEMPLATES_COLLECTION, template.to_dict())

    def get_analysis_template(self, analysis_template_id: str) -> AnalysisTemplate:
        """Get an analysis template by ID."""

        return AnalysisTemplate.from_dict(
            self._get_document(ANALYSIS_TEMPLATES_COLLECTION, analysis_template_id)
        )

    def update_analysis_template(self, template: AnalysisTemplate) -> str:
        """Update an analysis template."""

        template.updated_at = datetime.now(timezone.utc)
        return self._update_document(ANALYSIS_TEMPLATES_COLLECTION, template.to_dict())

    def list_analysis_templates(self, workspace_id: str) -> List[AnalysisTemplate]:
        """List a workspace's analysis templates, newest first."""

        docs = self._list_workspace_documents(
            ANALYSIS_TEMPLATES_COLLECTION,
            workspace_id,
            sort_field="created_at",
        )
        return [AnalysisTemplate.from_dict(doc) for doc in docs]

    # --- Retention policy operations (FR-54) ---

    def insert_retention_policy(self, policy: RetentionPolicy) -> str:
        """Insert a workspace retention policy."""

        return self._insert_document(RETENTION_POLICIES_COLLECTION, policy.to_dict())

    def update_retention_policy(self, policy: RetentionPolicy) -> str:
        """Update a workspace retention policy."""

        policy.updated_at = datetime.now(timezone.utc)
        return self._update_document(RETENTION_POLICIES_COLLECTION, policy.to_dict())

    def get_retention_policy(self, workspace_id: str) -> Optional[RetentionPolicy]:
        """Return a workspace's retention policy, or None when unset."""

        docs = self._list_workspace_documents(
            RETENTION_POLICIES_COLLECTION, workspace_id
        )
        return RetentionPolicy.from_dict(docs[0]) if docs else None

    def delete_document_by_key(self, collection_name: str, key: str) -> bool:
        """Delete one document by key. Returns False when already absent.

        Used by the FR-54 retention sweep; kept generic because the sweep
        spans several collections and each already has a typed reader.
        """

        try:
            self.db.collection(collection_name).delete(key)
            return True
        except Exception:  # noqa: BLE001 — already-gone is not an error
            return False

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

    def list_audit_events(
        self, workspace_id: str, limit: int = 100
    ) -> List[AuditEvent]:
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
