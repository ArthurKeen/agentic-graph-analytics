"""Data models for UI product metadata.

The product layer stores non-secret workspace and UI state alongside the
existing Analysis Catalog. These dataclasses intentionally mirror the catalog
model style so the library can remain framework-agnostic.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .exceptions import ValidationError


class WorkspaceStatus(Enum):
    """Lifecycle status for a customer workspace."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class ConnectionVerificationStatus(Enum):
    """Last verification result for a connection profile."""

    UNKNOWN = "unknown"
    SUCCESS = "success"
    FAILED = "failed"


class DeploymentMode(Enum):
    """Supported deployment modes for ArangoDB/GAE connections."""

    SELF_MANAGED = "self_managed"
    ARANGO_GRAPH = "arangograph"
    AMP = "amp"
    LOCAL = "local"


class GraphProfileStatus(Enum):
    """Lifecycle status for graph profiles."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class DocumentStorageMode(Enum):
    """How source document content is stored."""

    INLINE = "inline"
    URI = "uri"
    EXTRACT_ONLY = "extract_only"


class RequirementInterviewStatus(Enum):
    """Lifecycle status for Requirements Copilot sessions."""

    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class RequirementVersionStatus(Enum):
    """Lifecycle status for requirement versions."""

    DRAFT = "draft"
    APPROVED = "approved"
    ARCHIVED = "archived"


class WorkflowMode(Enum):
    """Supported workflow execution modes."""

    TRADITIONAL = "traditional"
    AGENTIC = "agentic"
    PARALLEL_AGENTIC = "parallel_agentic"


class WorkflowRunStatus(Enum):
    """Lifecycle status for workflow runs."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    INTERRUPTED = "interrupted"


class WorkflowStepStatus(Enum):
    """Status for individual workflow DAG steps."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PAUSED = "paused"


def current_timestamp() -> datetime:
    """Get the current UTC timestamp."""

    return datetime.now(timezone.utc)


def generate_product_id(prefix: str) -> str:
    """Generate a stable product entity ID."""

    return f"{prefix}-{uuid.uuid4()}"


def _datetime_to_str(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _datetime_from_str(value: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(value) if value else None


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


FORBIDDEN_SECRET_KEYS = {
    "api_key",
    "api_key_secret",
    "api_secret",
    "authorization",
    "bearer",
    "client_secret",
    "graph_api_key_secret",
    "llm_api_key",
    "oasistoken",
    "oasis_token",
    "password",
    "secret",
    "token",
}


def validate_no_secret_values(payload: Dict[str, Any], path: str = "") -> None:
    """Reject product metadata payloads that appear to include secret values.

    Product collections may store secret references, but never resolved secret
    values. The check is intentionally key-oriented so normal metadata values
    are not treated as secrets solely because they are high entropy.
    """

    for key, value in payload.items():
        normalized = key.lower().replace("-", "_")
        current_path = f"{path}.{key}" if path else key

        if normalized in {"secret_refs", "secret_ref"}:
            continue

        if any(secret_key == normalized or normalized.endswith(f"_{secret_key}") for secret_key in FORBIDDEN_SECRET_KEYS):
            raise ValidationError(f"Secret-like field is not allowed in product metadata: {current_path}")

        if isinstance(value, dict):
            validate_no_secret_values(value, current_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    validate_no_secret_values(item, f"{current_path}[{index}]")


@dataclass
class Workspace:
    """Customer/project/environment workspace metadata."""

    workspace_id: str
    customer_name: str
    project_name: str
    environment: str
    description: str = ""
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=current_timestamp)
    updated_at: datetime = field(default_factory=current_timestamp)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to an ArangoDB document."""

        doc = {
            "_key": self.workspace_id,
            "workspace_id": self.workspace_id,
            "customer_name": self.customer_name,
            "project_name": self.project_name,
            "environment": self.environment,
            "description": self.description,
            "status": _enum_value(self.status),
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
        validate_no_secret_values(doc)
        return doc

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workspace":
        """Create a workspace from an ArangoDB document."""

        return cls(
            workspace_id=data.get("workspace_id") or data["_key"],
            customer_name=data["customer_name"],
            project_name=data["project_name"],
            environment=data["environment"],
            description=data.get("description", ""),
            status=WorkspaceStatus(data.get("status", WorkspaceStatus.ACTIVE.value)),
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConnectionProfile:
    """Non-secret connection metadata plus references to secret values."""

    connection_profile_id: str
    workspace_id: str
    name: str
    deployment_mode: DeploymentMode
    endpoint: str
    database: str
    username: str
    verify_ssl: bool = True
    secret_refs: Dict[str, Dict[str, str]] = field(default_factory=dict)
    last_verified_at: Optional[datetime] = None
    last_verification_status: ConnectionVerificationStatus = ConnectionVerificationStatus.UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=current_timestamp)
    updated_at: datetime = field(default_factory=current_timestamp)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to an ArangoDB document."""

        doc = {
            "_key": self.connection_profile_id,
            "connection_profile_id": self.connection_profile_id,
            "workspace_id": self.workspace_id,
            "name": self.name,
            "deployment_mode": _enum_value(self.deployment_mode),
            "endpoint": self.endpoint,
            "database": self.database,
            "username": self.username,
            "verify_ssl": self.verify_ssl,
            "secret_refs": self.secret_refs,
            "last_verified_at": _datetime_to_str(self.last_verified_at),
            "last_verification_status": _enum_value(self.last_verification_status),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

        non_secret_doc = {k: v for k, v in doc.items() if k != "secret_refs"}
        validate_no_secret_values(non_secret_doc)
        return doc

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectionProfile":
        """Create a connection profile from an ArangoDB document."""

        return cls(
            connection_profile_id=data.get("connection_profile_id") or data["_key"],
            workspace_id=data["workspace_id"],
            name=data["name"],
            deployment_mode=DeploymentMode(data["deployment_mode"]),
            endpoint=data["endpoint"],
            database=data["database"],
            username=data["username"],
            verify_ssl=data.get("verify_ssl", True),
            secret_refs=data.get("secret_refs", {}),
            last_verified_at=_datetime_from_str(data.get("last_verified_at")),
            last_verification_status=ConnectionVerificationStatus(
                data.get(
                    "last_verification_status",
                    ConnectionVerificationStatus.UNKNOWN.value,
                )
            ),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class GraphProfile:
    """Versioned graph inventory and role metadata for a workspace."""

    graph_profile_id: str
    workspace_id: str
    connection_profile_id: str
    graph_name: str
    version: int = 1
    status: GraphProfileStatus = GraphProfileStatus.DRAFT
    schema_hash: Optional[str] = None
    vertex_collections: List[str] = field(default_factory=list)
    edge_collections: List[str] = field(default_factory=list)
    edge_definitions: List[Dict[str, Any]] = field(default_factory=list)
    collection_roles: Dict[str, List[str]] = field(default_factory=dict)
    counts: Dict[str, int] = field(default_factory=dict)
    created_at: datetime = field(default_factory=current_timestamp)
    updated_at: datetime = field(default_factory=current_timestamp)
    created_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to an ArangoDB document."""

        doc = {
            "_key": self.graph_profile_id,
            "graph_profile_id": self.graph_profile_id,
            "workspace_id": self.workspace_id,
            "connection_profile_id": self.connection_profile_id,
            "graph_name": self.graph_name,
            "version": self.version,
            "status": _enum_value(self.status),
            "schema_hash": self.schema_hash,
            "vertex_collections": self.vertex_collections,
            "edge_collections": self.edge_collections,
            "edge_definitions": self.edge_definitions,
            "collection_roles": self.collection_roles,
            "counts": self.counts,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "metadata": self.metadata,
        }
        validate_no_secret_values(doc)
        return doc

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphProfile":
        """Create a graph profile from an ArangoDB document."""

        return cls(
            graph_profile_id=data.get("graph_profile_id") or data["_key"],
            workspace_id=data["workspace_id"],
            connection_profile_id=data["connection_profile_id"],
            graph_name=data["graph_name"],
            version=data.get("version", 1),
            status=GraphProfileStatus(data.get("status", GraphProfileStatus.DRAFT.value)),
            schema_hash=data.get("schema_hash"),
            vertex_collections=data.get("vertex_collections", []),
            edge_collections=data.get("edge_collections", []),
            edge_definitions=data.get("edge_definitions", []),
            collection_roles=data.get("collection_roles", {}),
            counts=data.get("counts", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            created_by=data.get("created_by"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SourceDocument:
    """Source document metadata and extracted text reference."""

    document_id: str
    workspace_id: str
    filename: str
    mime_type: str
    sha256: str
    storage_mode: DocumentStorageMode
    storage_uri: Optional[str] = None
    extracted_text: Optional[str] = None
    uploaded_at: datetime = field(default_factory=current_timestamp)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to an ArangoDB document."""

        doc = {
            "_key": self.document_id,
            "document_id": self.document_id,
            "workspace_id": self.workspace_id,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "sha256": self.sha256,
            "storage_mode": _enum_value(self.storage_mode),
            "storage_uri": self.storage_uri,
            "extracted_text": self.extracted_text,
            "uploaded_at": self.uploaded_at.isoformat(),
            "metadata": self.metadata,
        }
        validate_no_secret_values(doc)
        return doc

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceDocument":
        """Create a source document from an ArangoDB document."""

        return cls(
            document_id=data.get("document_id") or data["_key"],
            workspace_id=data["workspace_id"],
            filename=data["filename"],
            mime_type=data["mime_type"],
            sha256=data["sha256"],
            storage_mode=DocumentStorageMode(data["storage_mode"]),
            storage_uri=data.get("storage_uri"),
            extracted_text=data.get("extracted_text"),
            uploaded_at=datetime.fromisoformat(data["uploaded_at"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class RequirementInterview:
    """Requirements Copilot interview session and generated draft."""

    requirement_interview_id: str
    workspace_id: str
    graph_profile_id: str
    status: RequirementInterviewStatus = RequirementInterviewStatus.DRAFT
    domain: Optional[str] = None
    questions: List[Dict[str, Any]] = field(default_factory=list)
    answers: List[Dict[str, Any]] = field(default_factory=list)
    schema_observations: Dict[str, Any] = field(default_factory=dict)
    inferences: List[Dict[str, Any]] = field(default_factory=list)
    assumptions: List[Dict[str, Any]] = field(default_factory=list)
    draft_brd: Optional[str] = None
    provenance_labels: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=current_timestamp)
    updated_at: datetime = field(default_factory=current_timestamp)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to an ArangoDB document."""

        doc = {
            "_key": self.requirement_interview_id,
            "requirement_interview_id": self.requirement_interview_id,
            "workspace_id": self.workspace_id,
            "graph_profile_id": self.graph_profile_id,
            "status": _enum_value(self.status),
            "domain": self.domain,
            "questions": self.questions,
            "answers": self.answers,
            "schema_observations": self.schema_observations,
            "inferences": self.inferences,
            "assumptions": self.assumptions,
            "draft_brd": self.draft_brd,
            "provenance_labels": self.provenance_labels,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
        validate_no_secret_values(doc)
        return doc

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RequirementInterview":
        """Create an interview from an ArangoDB document."""

        return cls(
            requirement_interview_id=data.get("requirement_interview_id") or data["_key"],
            workspace_id=data["workspace_id"],
            graph_profile_id=data["graph_profile_id"],
            status=RequirementInterviewStatus(
                data.get("status", RequirementInterviewStatus.DRAFT.value)
            ),
            domain=data.get("domain"),
            questions=data.get("questions", []),
            answers=data.get("answers", []),
            schema_observations=data.get("schema_observations", {}),
            inferences=data.get("inferences", []),
            assumptions=data.get("assumptions", []),
            draft_brd=data.get("draft_brd"),
            provenance_labels=data.get("provenance_labels", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class RequirementVersion:
    """Reviewed, versioned requirement set."""

    requirement_version_id: str
    workspace_id: str
    version: int
    status: RequirementVersionStatus = RequirementVersionStatus.DRAFT
    document_ids: List[str] = field(default_factory=list)
    analysis_requirements_id: Optional[str] = None
    requirement_interview_id: Optional[str] = None
    summary: str = ""
    objectives: List[Dict[str, Any]] = field(default_factory=list)
    requirements: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    approved_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=current_timestamp)
    updated_at: datetime = field(default_factory=current_timestamp)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to an ArangoDB document."""

        doc = {
            "_key": self.requirement_version_id,
            "requirement_version_id": self.requirement_version_id,
            "workspace_id": self.workspace_id,
            "document_ids": self.document_ids,
            "analysis_requirements_id": self.analysis_requirements_id,
            "requirement_interview_id": self.requirement_interview_id,
            "version": self.version,
            "status": _enum_value(self.status),
            "summary": self.summary,
            "objectives": self.objectives,
            "requirements": self.requirements,
            "constraints": self.constraints,
            "approved_at": _datetime_to_str(self.approved_at),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
        validate_no_secret_values(doc)
        return doc

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RequirementVersion":
        """Create a requirement version from an ArangoDB document."""

        return cls(
            requirement_version_id=data.get("requirement_version_id") or data["_key"],
            workspace_id=data["workspace_id"],
            document_ids=data.get("document_ids", []),
            analysis_requirements_id=data.get("analysis_requirements_id"),
            requirement_interview_id=data.get("requirement_interview_id"),
            version=data["version"],
            status=RequirementVersionStatus(
                data.get("status", RequirementVersionStatus.DRAFT.value)
            ),
            summary=data.get("summary", ""),
            objectives=data.get("objectives", []),
            requirements=data.get("requirements", []),
            constraints=data.get("constraints", []),
            approved_at=_datetime_from_str(data.get("approved_at")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class WorkflowStep:
    """Visualizable workflow step state."""

    step_id: str
    label: str
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING
    agent_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    retry_count: int = 0
    checkpoint_id: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    artifact_refs: List[Dict[str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    cost: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary suitable for nested storage."""

        doc = {
            "step_id": self.step_id,
            "label": self.label,
            "status": _enum_value(self.status),
            "agent_name": self.agent_name,
            "started_at": _datetime_to_str(self.started_at),
            "completed_at": _datetime_to_str(self.completed_at),
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
            "checkpoint_id": self.checkpoint_id,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "artifact_refs": self.artifact_refs,
            "warnings": self.warnings,
            "errors": self.errors,
            "cost": self.cost,
            "metadata": self.metadata,
        }
        validate_no_secret_values(doc)
        return doc

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowStep":
        """Create a workflow step from a dictionary."""

        return cls(
            step_id=data["step_id"],
            label=data["label"],
            status=WorkflowStepStatus(data.get("status", WorkflowStepStatus.PENDING.value)),
            agent_name=data.get("agent_name"),
            started_at=_datetime_from_str(data.get("started_at")),
            completed_at=_datetime_from_str(data.get("completed_at")),
            duration_ms=data.get("duration_ms"),
            retry_count=data.get("retry_count", 0),
            checkpoint_id=data.get("checkpoint_id"),
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            artifact_refs=data.get("artifact_refs", []),
            warnings=data.get("warnings", []),
            errors=data.get("errors", []),
            cost=data.get("cost", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class WorkflowDAGEdge:
    """Directed dependency between workflow steps."""

    from_step_id: str
    to_step_id: str
    label: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary suitable for nested storage."""

        doc = {
            "from_step_id": self.from_step_id,
            "to_step_id": self.to_step_id,
            "label": self.label,
            "metadata": self.metadata,
        }
        validate_no_secret_values(doc)
        return doc

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDAGEdge":
        """Create an edge from a dictionary."""

        return cls(
            from_step_id=data["from_step_id"],
            to_step_id=data["to_step_id"],
            label=data.get("label"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class WorkflowRun:
    """UI-level workflow run state and visualizer DAG."""

    run_id: str
    workspace_id: str
    workflow_mode: WorkflowMode
    status: WorkflowRunStatus = WorkflowRunStatus.QUEUED
    requirement_version_id: Optional[str] = None
    graph_profile_id: Optional[str] = None
    template_ids: List[str] = field(default_factory=list)
    steps: List[WorkflowStep] = field(default_factory=list)
    dag_edges: List[WorkflowDAGEdge] = field(default_factory=list)
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=current_timestamp)
    updated_at: datetime = field(default_factory=current_timestamp)
    analysis_execution_ids: List[str] = field(default_factory=list)
    report_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to an ArangoDB document."""

        doc = {
            "_key": self.run_id,
            "run_id": self.run_id,
            "workspace_id": self.workspace_id,
            "workflow_mode": _enum_value(self.workflow_mode),
            "status": _enum_value(self.status),
            "requirement_version_id": self.requirement_version_id,
            "graph_profile_id": self.graph_profile_id,
            "template_ids": self.template_ids,
            "steps": [step.to_dict() for step in self.steps],
            "dag_edges": [edge.to_dict() for edge in self.dag_edges],
            "checkpoints": self.checkpoints,
            "warnings": self.warnings,
            "errors": self.errors,
            "started_at": _datetime_to_str(self.started_at),
            "completed_at": _datetime_to_str(self.completed_at),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "analysis_execution_ids": self.analysis_execution_ids,
            "report_ids": self.report_ids,
            "metadata": self.metadata,
        }
        validate_no_secret_values(doc)
        return doc

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowRun":
        """Create a workflow run from an ArangoDB document."""

        return cls(
            run_id=data.get("run_id") or data["_key"],
            workspace_id=data["workspace_id"],
            workflow_mode=WorkflowMode(data["workflow_mode"]),
            status=WorkflowRunStatus(data.get("status", WorkflowRunStatus.QUEUED.value)),
            requirement_version_id=data.get("requirement_version_id"),
            graph_profile_id=data.get("graph_profile_id"),
            template_ids=data.get("template_ids", []),
            steps=[WorkflowStep.from_dict(step) for step in data.get("steps", [])],
            dag_edges=[
                WorkflowDAGEdge.from_dict(edge) for edge in data.get("dag_edges", [])
            ],
            checkpoints=data.get("checkpoints", []),
            warnings=data.get("warnings", []),
            errors=data.get("errors", []),
            started_at=_datetime_from_str(data.get("started_at")),
            completed_at=_datetime_from_str(data.get("completed_at")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            analysis_execution_ids=data.get("analysis_execution_ids", []),
            report_ids=data.get("report_ids", []),
            metadata=data.get("metadata", {}),
        )


def create_workspace(
    customer_name: str,
    project_name: str,
    environment: str,
    **kwargs: Any,
) -> Workspace:
    """Create a workspace with a generated ID."""

    return Workspace(
        workspace_id=generate_product_id("workspace"),
        customer_name=customer_name,
        project_name=project_name,
        environment=environment,
        **kwargs,
    )


def create_connection_profile(
    workspace_id: str,
    name: str,
    deployment_mode: DeploymentMode,
    endpoint: str,
    database: str,
    username: str,
    **kwargs: Any,
) -> ConnectionProfile:
    """Create a connection profile with a generated ID."""

    return ConnectionProfile(
        connection_profile_id=generate_product_id("connection"),
        workspace_id=workspace_id,
        name=name,
        deployment_mode=deployment_mode,
        endpoint=endpoint,
        database=database,
        username=username,
        **kwargs,
    )


def create_graph_profile(
    workspace_id: str,
    connection_profile_id: str,
    graph_name: str,
    **kwargs: Any,
) -> GraphProfile:
    """Create a graph profile with a generated ID."""

    return GraphProfile(
        graph_profile_id=generate_product_id("graph-profile"),
        workspace_id=workspace_id,
        connection_profile_id=connection_profile_id,
        graph_name=graph_name,
        **kwargs,
    )


def create_source_document(
    workspace_id: str,
    filename: str,
    mime_type: str,
    sha256: str,
    storage_mode: DocumentStorageMode,
    **kwargs: Any,
) -> SourceDocument:
    """Create a source document with a generated ID."""

    return SourceDocument(
        document_id=generate_product_id("document"),
        workspace_id=workspace_id,
        filename=filename,
        mime_type=mime_type,
        sha256=sha256,
        storage_mode=storage_mode,
        **kwargs,
    )


def create_requirement_interview(
    workspace_id: str,
    graph_profile_id: str,
    **kwargs: Any,
) -> RequirementInterview:
    """Create a Requirements Copilot interview with a generated ID."""

    return RequirementInterview(
        requirement_interview_id=generate_product_id("requirement-interview"),
        workspace_id=workspace_id,
        graph_profile_id=graph_profile_id,
        **kwargs,
    )


def create_requirement_version(
    workspace_id: str,
    version: int,
    **kwargs: Any,
) -> RequirementVersion:
    """Create a requirement version with a generated ID."""

    return RequirementVersion(
        requirement_version_id=generate_product_id("requirement-version"),
        workspace_id=workspace_id,
        version=version,
        **kwargs,
    )


def create_workflow_run(
    workspace_id: str,
    workflow_mode: WorkflowMode,
    **kwargs: Any,
) -> WorkflowRun:
    """Create a workflow run with a generated ID."""

    return WorkflowRun(
        run_id=generate_product_id("run"),
        workspace_id=workspace_id,
        workflow_mode=workflow_mode,
        **kwargs,
    )

