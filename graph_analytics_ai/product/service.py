"""Application services for product UI workflows.

The service layer exposes UI-ready read models and workflow operations without
coupling the core package to a web framework.
"""

import hashlib
import json
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
    create_graph_profile,
    create_published_snapshot,
    create_requirement_interview,
    create_requirement_version,
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
        graph_profile = create_graph_profile(
            workspace_id=profile.workspace_id,
            connection_profile_id=profile.connection_profile_id,
            graph_name=selected_graph_name,
            vertex_collections=sorted(schema.vertex_collections.keys()),
            edge_collections=sorted(schema.edge_collections.keys()),
            edge_definitions=self._schema_edge_definitions(schema),
            counts={
                "vertex_collections": len(schema.vertex_collections),
                "edge_collections": len(schema.edge_collections),
                "document_collections": len(schema.document_collections),
                "total_documents": schema.total_documents,
                "total_edges": schema.total_edges,
                "relationships": len(schema.relationships),
            },
            created_by=created_by,
            metadata={
                "database": schema.database_name,
                "available_graphs": schema.graph_names,
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
    ) -> RequirementInterview:
        """Start a schema-aware Requirements Copilot interview."""

        graph_profile = self.repository.get_graph_profile(graph_profile_id)
        schema_observations = self._schema_observations_from_graph_profile(graph_profile)
        interview = create_requirement_interview(
            workspace_id=graph_profile.workspace_id,
            graph_profile_id=graph_profile.graph_profile_id,
            domain=domain,
            questions=self._requirements_copilot_questions(schema_observations),
            schema_observations=schema_observations,
            metadata={"created_by": created_by} if created_by else {},
        )
        self.repository.create_requirement_interview(interview)
        return interview

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
        version: int,
        approved_by: Optional[str] = None,
    ) -> RequirementVersion:
        """Approve a generated BRD draft into a requirement version."""

        interview = self.repository.get_requirement_interview(requirement_interview_id)
        if not interview.draft_brd:
            raise ValidationError("Requirements Copilot draft must be generated first")

        requirement_version = create_requirement_version(
            workspace_id=interview.workspace_id,
            version=version,
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
            },
        )
        self.repository.create_requirement_version(requirement_version)

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
