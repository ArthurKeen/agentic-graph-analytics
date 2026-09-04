"""Unit tests for product UI application services."""

import hashlib
import logging

import pytest

from graph_analytics_ai.product import (
    AnalysisExecutionStatus,
    ChartType,
    ConnectionVerificationStatus,
    MappingSecretResolver,
    ProductService,
    RequirementInterviewStatus,
    RequirementVersionStatus,
    ReportSectionType,
    ReportStatus,
    WorkflowDAGEdge,
    WorkflowMode,
    WorkflowRunStatus,
    WorkflowStep,
    WorkflowStepStatus,
    create_audit_event,
    create_analysis_epoch,
    create_analysis_execution,
    create_chart_spec,
    create_connection_profile,
    create_graph_profile,
    create_requirement_interview,
    create_report_manifest,
    create_report_section,
    create_requirement_version,
    create_source_document,
    create_workflow_run,
    create_workspace,
)
from graph_analytics_ai.product.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from graph_analytics_ai.product.models import (
    AnalysisTemplateStatus,
    DeploymentMode,
    DocumentStorageMode,
    UseCaseOrigin,
    UseCaseStatus,
    create_analysis_template,
    create_use_case,
)
from graph_analytics_ai.ai.schema.models import (
    CollectionSchema,
    CollectionType,
    GraphSchema,
    Relationship,
)


class FakeProductRepository:
    """Minimal in-memory repository used by service tests."""

    def __init__(self):
        self.workspaces = {}
        self.connection_profiles = []
        self.graph_profiles = []
        self.source_documents = []
        self.use_cases = []
        self.analysis_templates = []
        self.requirement_interviews = []
        self.requirement_versions = []
        self.workflow_runs = {}
        self.analysis_executions = {}
        self.analysis_epochs = {}
        self.reports = {}
        self.sections = []
        self.charts = []
        self.snapshots = []
        self.audit_events = []

    def get_workspace(self, workspace_id):
        return self.workspaces[workspace_id]

    def create_workspace(self, workspace):
        self.workspaces[workspace.workspace_id] = workspace
        return workspace.workspace_id

    def update_workspace(self, workspace):
        if workspace.workspace_id not in self.workspaces:
            raise KeyError(workspace.workspace_id)
        self.workspaces[workspace.workspace_id] = workspace
        return workspace.workspace_id

    def list_connection_profiles(self, workspace_id):
        return [
            profile
            for profile in self.connection_profiles
            if profile.workspace_id == workspace_id
        ]

    def create_connection_profile(self, profile):
        self.connection_profiles.append(profile)
        return profile.connection_profile_id

    def get_connection_profile(self, connection_profile_id):
        for profile in self.connection_profiles:
            if profile.connection_profile_id == connection_profile_id:
                return profile
        raise KeyError(connection_profile_id)

    def update_connection_profile(self, profile):
        for index, existing in enumerate(self.connection_profiles):
            if existing.connection_profile_id == profile.connection_profile_id:
                self.connection_profiles[index] = profile
                return profile.connection_profile_id
        raise KeyError(profile.connection_profile_id)

    def list_graph_profiles(self, workspace_id):
        return [
            profile
            for profile in self.graph_profiles
            if profile.workspace_id == workspace_id
        ]

    def create_graph_profile(self, profile):
        self.graph_profiles.append(profile)
        return profile.graph_profile_id

    def get_graph_profile(self, graph_profile_id):
        for profile in self.graph_profiles:
            if profile.graph_profile_id == graph_profile_id:
                return profile
        raise KeyError(graph_profile_id)

    def update_graph_profile(self, profile):
        for index, existing in enumerate(self.graph_profiles):
            if existing.graph_profile_id == profile.graph_profile_id:
                self.graph_profiles[index] = profile
                return profile.graph_profile_id
        raise KeyError(profile.graph_profile_id)

    # --- Use cases and analysis templates (FR-19..FR-26) ---

    def create_use_case(self, use_case):
        self.use_cases.append(use_case)
        return use_case.use_case_id

    def get_use_case(self, use_case_id):
        for use_case in self.use_cases:
            if use_case.use_case_id == use_case_id:
                return use_case
        raise KeyError(use_case_id)

    def update_use_case(self, use_case):
        for index, existing in enumerate(self.use_cases):
            if existing.use_case_id == use_case.use_case_id:
                self.use_cases[index] = use_case
                return use_case.use_case_id
        raise KeyError(use_case.use_case_id)

    def list_use_cases(self, workspace_id):
        return [
            use_case
            for use_case in self.use_cases
            if use_case.workspace_id == workspace_id
        ]

    def create_analysis_template(self, template):
        self.analysis_templates.append(template)
        return template.analysis_template_id

    def get_analysis_template(self, analysis_template_id):
        for template in self.analysis_templates:
            if template.analysis_template_id == analysis_template_id:
                return template
        raise KeyError(analysis_template_id)

    def update_analysis_template(self, template):
        for index, existing in enumerate(self.analysis_templates):
            if existing.analysis_template_id == template.analysis_template_id:
                self.analysis_templates[index] = template
                return template.analysis_template_id
        raise KeyError(template.analysis_template_id)

    def list_analysis_templates(self, workspace_id):
        return [
            template
            for template in self.analysis_templates
            if template.workspace_id == workspace_id
        ]

    def list_source_documents(self, workspace_id):
        return [
            document
            for document in self.source_documents
            if document.workspace_id == workspace_id
        ]

    def create_source_document(self, document):
        self.source_documents.append(document)
        return document.document_id

    def get_source_document(self, document_id):
        for document in self.source_documents:
            if document.document_id == document_id:
                return document
        raise NotFoundError(f"Source document {document_id} not found")

    def list_requirement_versions(self, workspace_id):
        return [
            version
            for version in self.requirement_versions
            if version.workspace_id == workspace_id
        ]

    def create_requirement_version(self, version):
        self.requirement_versions.append(version)
        return version.requirement_version_id

    def get_requirement_version(self, requirement_version_id):
        for version in self.requirement_versions:
            if version.requirement_version_id == requirement_version_id:
                return version
        raise KeyError(requirement_version_id)

    def update_requirement_version(self, version):
        content_fields = ("summary", "objectives", "requirements", "constraints")
        for index, existing in enumerate(self.requirement_versions):
            if existing.requirement_version_id == version.requirement_version_id:
                if existing.status == RequirementVersionStatus.APPROVED and any(
                    getattr(existing, field) != getattr(version, field)
                    for field in content_fields
                ):
                    raise ConflictError(
                        f"RequirementVersion {version.requirement_version_id} is "
                        "approved and its content is immutable"
                    )
                self.requirement_versions[index] = version
                return version.requirement_version_id
        raise KeyError(version.requirement_version_id)

    def list_requirement_interviews(self, workspace_id):
        return [
            interview
            for interview in self.requirement_interviews
            if interview.workspace_id == workspace_id
        ]

    def create_requirement_interview(self, interview):
        self.requirement_interviews.append(interview)
        return interview.requirement_interview_id

    def get_requirement_interview(self, requirement_interview_id):
        for interview in self.requirement_interviews:
            if interview.requirement_interview_id == requirement_interview_id:
                return interview
        raise KeyError(requirement_interview_id)

    def update_requirement_interview(self, interview):
        for index, existing in enumerate(self.requirement_interviews):
            if existing.requirement_interview_id == interview.requirement_interview_id:
                self.requirement_interviews[index] = interview
                return interview.requirement_interview_id
        raise KeyError(interview.requirement_interview_id)

    def list_workflow_runs(self, workspace_id):
        return [
            run
            for run in self.workflow_runs.values()
            if run.workspace_id == workspace_id
        ]

    def create_workflow_run(self, run):
        self.workflow_runs[run.run_id] = run
        return run.run_id

    def get_workflow_run(self, run_id):
        return self.workflow_runs[run_id]

    def update_workflow_run(self, run):
        self.workflow_runs[run.run_id] = run
        return run.run_id

    def create_analysis_execution(self, execution):
        self.analysis_executions[execution.analysis_execution_id] = execution
        return execution.analysis_execution_id

    def get_analysis_execution(self, analysis_execution_id):
        return self.analysis_executions[analysis_execution_id]

    def update_analysis_execution(self, execution):
        self.analysis_executions[execution.analysis_execution_id] = execution
        return execution.analysis_execution_id

    def list_analysis_executions(self, workspace_id):
        return [
            execution
            for execution in self.analysis_executions.values()
            if execution.workspace_id == workspace_id
        ]

    def create_analysis_epoch(self, epoch):
        self.analysis_epochs[epoch.analysis_epoch_id] = epoch
        return epoch.analysis_epoch_id

    def get_analysis_epoch(self, analysis_epoch_id):
        return self.analysis_epochs[analysis_epoch_id]

    def update_analysis_epoch(self, epoch):
        self.analysis_epochs[epoch.analysis_epoch_id] = epoch
        return epoch.analysis_epoch_id

    def list_analysis_epochs(self, workspace_id):
        return [
            epoch
            for epoch in self.analysis_epochs.values()
            if epoch.workspace_id == workspace_id
        ]

    def get_report_manifest(self, report_id):
        return self.reports[report_id]

    def create_report_manifest(self, manifest):
        self.reports[manifest.report_id] = manifest
        return manifest.report_id

    def update_report_manifest(self, manifest):
        self.reports[manifest.report_id] = manifest
        return manifest.report_id

    def list_report_manifests(self, workspace_id):
        return [
            report
            for report in self.reports.values()
            if report.workspace_id == workspace_id
        ]

    def list_report_sections(self, report_id):
        return [section for section in self.sections if section.report_id == report_id]

    def create_report_section(self, section):
        self.sections.append(section)
        return section.section_id

    def list_chart_specs(self, report_id):
        return [chart for chart in self.charts if chart.report_id == report_id]

    def create_chart_spec(self, chart):
        self.charts.append(chart)
        return chart.chart_id

    def create_published_snapshot(self, snapshot):
        self.snapshots.append(snapshot)
        return snapshot.published_snapshot_id

    def list_published_snapshots(self, report_id):
        return [
            snapshot for snapshot in self.snapshots if snapshot.report_id == report_id
        ]

    def create_audit_event(self, event):
        self.audit_events.append(event)
        return event.audit_event_id

    def list_audit_events(self, workspace_id, limit=100):
        return [
            event for event in self.audit_events if event.workspace_id == workspace_id
        ][:limit]


def test_create_workspace_validates_and_audits_metadata():
    """Workspace creation stores trimmed metadata and records audit context."""

    repository = FakeProductRepository()
    service = ProductService(repository)

    workspace = service.create_workspace(
        customer_name=" Example Customer ",
        project_name=" Product UI ",
        environment=" dev ",
        description=" Workspace metadata ",
        tags=[" graph ", "", "analytics"],
        actor="tester",
    )

    assert workspace.workspace_id in repository.workspaces
    assert workspace.customer_name == "Example Customer"
    assert workspace.project_name == "Product UI"
    assert workspace.environment == "dev"
    assert workspace.description == "Workspace metadata"
    assert workspace.tags == ["graph", "analytics"]
    assert repository.audit_events[-1].action == "create_workspace"
    assert repository.audit_events[-1].actor == "tester"


def test_create_workspace_requires_core_fields():
    """Workspace creation fails before storing incomplete metadata."""

    service = ProductService(FakeProductRepository())

    try:
        service.create_workspace(
            customer_name="",
            project_name="Project",
            environment="dev",
        )
    except ValidationError as exc:
        assert "Customer name" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for missing customer name")


def test_update_workspace_patches_only_changed_fields_and_audits_diff():
    """FR-1: PATCH applies trimmed values, bumps updated_at, and audits diff."""

    repository = FakeProductRepository()
    service = ProductService(repository)
    workspace = service.create_workspace(
        customer_name="Acme",
        project_name="AdTech",
        environment="dev",
        description="Original",
        tags=["adtech"],
    )
    repository.audit_events.clear()
    original_updated_at = workspace.updated_at

    updated = service.update_workspace(
        workspace.workspace_id,
        customer_name=" Acme Corp ",
        description="Refined description",
        tags=["adtech", "demo", " "],
        actor="ops@example.com",
    )

    assert updated.customer_name == "Acme Corp"
    assert updated.project_name == "AdTech"  # untouched
    assert updated.environment == "dev"
    assert updated.description == "Refined description"
    assert updated.tags == ["adtech", "demo"]
    assert updated.updated_at > original_updated_at

    assert len(repository.audit_events) == 1
    event = repository.audit_events[0]
    assert event.action == "update_workspace"
    assert event.actor == "ops@example.com"
    diff = event.details["changes"]
    assert set(diff.keys()) == {"customer_name", "description", "tags"}
    assert diff["customer_name"] == {"from": "Acme", "to": "Acme Corp"}
    assert diff["tags"]["to"] == ["adtech", "demo"]


def test_update_workspace_is_noop_when_nothing_changes():
    """No-op PATCH does not bump updated_at or emit an audit event."""

    repository = FakeProductRepository()
    service = ProductService(repository)
    workspace = service.create_workspace(
        customer_name="Acme",
        project_name="AdTech",
        environment="dev",
    )
    repository.audit_events.clear()
    original_updated_at = workspace.updated_at

    result = service.update_workspace(
        workspace.workspace_id,
        customer_name="Acme",
        # Same value with surrounding whitespace must still be detected as
        # equal after trim.
        project_name=" AdTech ",
    )

    assert result.updated_at == original_updated_at
    assert repository.audit_events == []


def test_update_workspace_rejects_blank_required_field():
    """Editable required fields cannot be cleared via PATCH."""

    repository = FakeProductRepository()
    service = ProductService(repository)
    workspace = service.create_workspace(
        customer_name="Acme",
        project_name="AdTech",
        environment="dev",
    )

    with pytest.raises(ValidationError, match="Customer name"):
        service.update_workspace(workspace.workspace_id, customer_name="   ")


def test_archive_workspace_flips_status_and_audits():
    """FR-1: archive sets status=ARCHIVED and records a dedicated audit event."""

    repository = FakeProductRepository()
    service = ProductService(repository)
    workspace = service.create_workspace(
        customer_name="Acme",
        project_name="AdTech",
        environment="dev",
    )
    repository.audit_events.clear()

    archived = service.archive_workspace(
        workspace.workspace_id, actor="ops@example.com"
    )

    assert archived.status.value == "archived"
    assert len(repository.audit_events) == 1
    assert repository.audit_events[0].action == "archive_workspace"
    assert repository.audit_events[0].actor == "ops@example.com"


def test_archive_workspace_is_idempotent():
    """Re-archiving an archived workspace is a no-op (no duplicate audit row)."""

    repository = FakeProductRepository()
    service = ProductService(repository)
    workspace = service.create_workspace(
        customer_name="Acme",
        project_name="AdTech",
        environment="dev",
    )
    service.archive_workspace(workspace.workspace_id, actor="ops@example.com")
    repository.audit_events.clear()

    service.archive_workspace(workspace.workspace_id, actor="ops@example.com")

    assert repository.audit_events == []


def _seed_graph_profile(repository, workspace_id, graph_name="AdtechGraph"):
    """Helper: minimal in-memory GraphProfile for set_active_graph_profile tests."""

    from graph_analytics_ai.product.models import create_graph_profile

    profile = create_graph_profile(
        workspace_id=workspace_id,
        connection_profile_id="connection-test",
        graph_name=graph_name,
        vertex_collections=["a", "b"],
        edge_collections=["edge_ab"],
        edge_definitions=[],
        counts={
            "vertex_collections": 2,
            "edge_collections": 1,
            "total_documents": 0,
            "total_edges": 0,
            "relationships": 0,
        },
    )
    repository.create_graph_profile(profile)
    return profile


def test_set_active_graph_profile_persists_and_audits():
    """FR-67b: setting the active graph profile updates the workspace + audits."""

    repository = FakeProductRepository()
    service = ProductService(repository)
    workspace = service.create_workspace(
        customer_name="Acme",
        project_name="AdTech",
        environment="dev",
    )
    profile = _seed_graph_profile(repository, workspace.workspace_id)
    repository.audit_events.clear()
    original_updated_at = workspace.updated_at

    updated = service.set_active_graph_profile(
        workspace.workspace_id,
        profile.graph_profile_id,
        actor="ops@example.com",
    )

    assert updated.active_graph_profile_id == profile.graph_profile_id
    assert updated.updated_at > original_updated_at
    assert len(repository.audit_events) == 1
    event = repository.audit_events[0]
    assert event.action == "set_active_graph_profile"
    assert event.actor == "ops@example.com"
    assert event.details == {"from": None, "to": profile.graph_profile_id}


def test_set_active_graph_profile_clears_with_none_or_blank():
    """Pass None (or empty string) to clear the selection (FR-67b)."""

    repository = FakeProductRepository()
    service = ProductService(repository)
    workspace = service.create_workspace(
        customer_name="Acme", project_name="AdTech", environment="dev"
    )
    profile = _seed_graph_profile(repository, workspace.workspace_id)
    service.set_active_graph_profile(workspace.workspace_id, profile.graph_profile_id)
    repository.audit_events.clear()

    cleared = service.set_active_graph_profile(workspace.workspace_id, "  ")
    assert cleared.active_graph_profile_id is None
    assert len(repository.audit_events) == 1
    assert repository.audit_events[0].details == {
        "from": profile.graph_profile_id,
        "to": None,
    }

    repository.audit_events.clear()
    cleared_again = service.set_active_graph_profile(workspace.workspace_id, None)
    # Already cleared: idempotent no-op (no second audit row).
    assert cleared_again.active_graph_profile_id is None
    assert repository.audit_events == []


def test_set_active_graph_profile_is_idempotent_for_same_value():
    """Re-pointing at the same profile is a no-op (no audit row, no updated_at bump)."""

    repository = FakeProductRepository()
    service = ProductService(repository)
    workspace = service.create_workspace(
        customer_name="Acme", project_name="AdTech", environment="dev"
    )
    profile = _seed_graph_profile(repository, workspace.workspace_id)
    service.set_active_graph_profile(workspace.workspace_id, profile.graph_profile_id)
    refreshed = repository.workspaces[workspace.workspace_id]
    stable_updated_at = refreshed.updated_at
    repository.audit_events.clear()

    again = service.set_active_graph_profile(
        workspace.workspace_id, profile.graph_profile_id
    )
    assert again.updated_at == stable_updated_at
    assert repository.audit_events == []


def test_set_active_graph_profile_rejects_cross_workspace_id():
    """A graph profile id that belongs to another workspace must be rejected.

    Without this check a leaked id from a different customer's workspace
    could be pointed at the current workspace's banner.
    """

    repository = FakeProductRepository()
    service = ProductService(repository)
    workspace_a = service.create_workspace(
        customer_name="Acme A", project_name="AdTech", environment="dev"
    )
    workspace_b = service.create_workspace(
        customer_name="Acme B", project_name="AdTech", environment="dev"
    )
    foreign_profile = _seed_graph_profile(
        repository, workspace_b.workspace_id, graph_name="OtherGraph"
    )

    with pytest.raises(ValidationError, match="must belong to this workspace"):
        service.set_active_graph_profile(
            workspace_a.workspace_id, foreign_profile.graph_profile_id
        )


def test_workspace_overview_counts_and_recent_items():
    """Workspace overview aggregates related product metadata."""

    repository = FakeProductRepository()
    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )
    repository.workspaces[workspace.workspace_id] = workspace
    repository.connection_profiles.append(
        create_connection_profile(
            workspace_id=workspace.workspace_id,
            name="Development",
            deployment_mode=DeploymentMode.LOCAL,
            endpoint="http://localhost:8529",
            database="customer_graph",
            username="root",
        )
    )
    repository.graph_profiles.append(
        create_graph_profile(
            workspace_id=workspace.workspace_id,
            connection_profile_id="connection-1",
            graph_name="customer_graph",
        )
    )
    repository.source_documents.append(
        create_source_document(
            workspace_id=workspace.workspace_id,
            filename="requirements.md",
            mime_type="text/markdown",
            sha256="abc123",
            storage_mode=DocumentStorageMode.INLINE,
        )
    )
    repository.requirement_versions.append(
        create_requirement_version(workspace_id=workspace.workspace_id, version=1)
    )
    run = create_workflow_run(
        workspace_id=workspace.workspace_id,
        workflow_mode=WorkflowMode.AGENTIC,
    )
    repository.workflow_runs[run.run_id] = run
    report = create_report_manifest(
        workspace_id=workspace.workspace_id,
        run_id=run.run_id,
        title="Graph Report",
    )
    repository.reports[report.report_id] = report
    repository.audit_events.append(
        create_audit_event(
            workspace_id=workspace.workspace_id,
            actor="analyst@example.com",
            action="create_report",
            target_type="report",
            target_id=report.report_id,
        )
    )

    overview = ProductService(repository).get_workspace_overview(workspace.workspace_id)

    assert overview.counts["connection_profiles"] == 1
    assert overview.counts["reports"] == 1
    assert overview.latest_connection_profiles[0]["name"] == "Development"
    assert overview.latest_graph_profiles[0]["graph_name"] == "customer_graph"
    assert overview.latest_source_documents[0]["filename"] == "requirements.md"
    assert overview.latest_workflow_runs[0]["run_id"] == run.run_id
    assert overview.latest_reports[0]["report_id"] == report.report_id
    assert overview.latest_audit_events[0]["action"] == "create_report"


def test_workspace_overview_returns_all_requirement_versions_uncapped():
    """Every navigable asset list must appear in the overview uncapped.

    The Assets panel is the ONLY entry point that can open these entities, so
    a ``recent_limit`` slice is not a UI affordance — it is data loss. Anything
    past the cap is permanently unreachable while ``counts`` keeps advertising
    it. This bit FR-17c first (requirement versions: "all historical versions
    remain queryable and individually addressable") and then FR-41 (reports:
    ``counts.reports`` reported 10 while only 5 could be opened).

    ``latest_audit_events`` is the one list that stays capped — it is a genuine
    "recent activity" feed, not a navigable asset list.
    """

    repository = FakeProductRepository()
    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )
    repository.workspaces[workspace.workspace_id] = workspace

    total_versions = 7
    statuses = [
        RequirementVersionStatus.SUPERSEDED,
        RequirementVersionStatus.SUPERSEDED,
        RequirementVersionStatus.SUPERSEDED,
        RequirementVersionStatus.SUPERSEDED,
        RequirementVersionStatus.SUPERSEDED,
        RequirementVersionStatus.SUPERSEDED,
        RequirementVersionStatus.APPROVED,
    ]
    for version_number, status in enumerate(statuses, start=1):
        repository.requirement_versions.append(
            create_requirement_version(
                workspace_id=workspace.workspace_id,
                version=version_number,
                status=status,
            )
        )

    cap = 5
    over_cap = cap + 3

    run = create_workflow_run(
        workspace_id=workspace.workspace_id,
        workflow_mode=WorkflowMode.AGENTIC,
    )
    repository.workflow_runs[run.run_id] = run
    for _ in range(over_cap - 1):
        extra_run = create_workflow_run(
            workspace_id=workspace.workspace_id,
            workflow_mode=WorkflowMode.AGENTIC,
        )
        repository.workflow_runs[extra_run.run_id] = extra_run

    for index in range(over_cap):
        report = create_report_manifest(
            workspace_id=workspace.workspace_id,
            run_id=run.run_id,
            title=f"Report {index}",
        )
        repository.reports[report.report_id] = report

        profile = create_connection_profile(
            workspace_id=workspace.workspace_id,
            name=f"connection-{index}",
            deployment_mode=DeploymentMode.SELF_MANAGED,
            endpoint="https://example.invalid:8529",
            database="example",
            username="root",
        )
        repository.connection_profiles.append(profile)

        graph_profile = create_graph_profile(
            workspace_id=workspace.workspace_id,
            connection_profile_id=profile.connection_profile_id,
            graph_name=f"graph-{index}",
        )
        repository.graph_profiles.append(graph_profile)

        document = create_source_document(
            workspace_id=workspace.workspace_id,
            filename=f"doc-{index}.md",
            mime_type="text/markdown",
            sha256=f"{index:064d}",
            storage_mode=DocumentStorageMode.INLINE,
        )
        repository.source_documents.append(document)

    overview = ProductService(repository).get_workspace_overview(
        workspace.workspace_id,
        recent_limit=cap,
    )

    assert overview.counts["requirement_versions"] == total_versions
    assert len(overview.latest_requirement_versions) == total_versions
    returned_versions = [
        item["version"] for item in overview.latest_requirement_versions
    ]
    assert returned_versions == sorted(returned_versions, reverse=True)
    assert returned_versions == list(range(total_versions, 0, -1))

    # Every navigable asset list is uncapped, and each one matches the count
    # the same overview advertises — a list shorter than its own count is
    # exactly the "listed but unopenable" defect this guards against.
    for field_name, count_key in (
        ("latest_reports", "reports"),
        ("latest_connection_profiles", "connection_profiles"),
        ("latest_graph_profiles", "graph_profiles"),
        ("latest_source_documents", "source_documents"),
        ("latest_workflow_runs", "workflow_runs"),
    ):
        projected = getattr(overview, field_name)
        assert len(projected) == over_cap, f"{field_name} was truncated"
        assert overview.counts[count_key] == len(
            projected
        ), f"{field_name} does not match counts[{count_key}]"

    # The audit feed is the deliberate exception and stays capped.
    assert len(overview.latest_audit_events) <= cap


def test_workspace_health_identifies_missing_and_failed_metadata():
    """Workspace health reports setup gaps and failed product entities."""

    repository = FakeProductRepository()
    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )
    repository.workspaces[workspace.workspace_id] = workspace
    profile = create_connection_profile(
        workspace_id=workspace.workspace_id,
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
        last_verification_status=ConnectionVerificationStatus.FAILED,
    )
    repository.connection_profiles.append(profile)
    failed_run = create_workflow_run(
        workspace_id=workspace.workspace_id,
        workflow_mode=WorkflowMode.AGENTIC,
        status=WorkflowRunStatus.FAILED,
    )
    repository.workflow_runs[failed_run.run_id] = failed_run

    health = ProductService(repository).check_workspace_health(workspace.workspace_id)
    issue_codes = {issue["code"] for issue in health.issues}

    assert health.status == "needs_attention"
    assert health.counts["connection_profiles"] == 1
    assert "missing_graph_profile" in issue_codes
    assert "missing_requirement_version" in issue_codes
    assert "failed_connection_verification" in issue_codes
    assert "failed_workflow_runs" in issue_codes


def test_workspace_health_is_healthy_when_core_metadata_exists():
    """Workspace health is healthy when required product metadata is present."""

    repository = FakeProductRepository()
    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )
    repository.workspaces[workspace.workspace_id] = workspace
    profile = create_connection_profile(
        workspace_id=workspace.workspace_id,
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
        last_verification_status=ConnectionVerificationStatus.SUCCESS,
    )
    repository.connection_profiles.append(profile)
    repository.graph_profiles.append(
        create_graph_profile(
            workspace_id=workspace.workspace_id,
            connection_profile_id=profile.connection_profile_id,
            graph_name="CustomerGraph",
        )
    )
    repository.requirement_versions.append(
        create_requirement_version(workspace_id=workspace.workspace_id, version=1)
    )

    health = ProductService(repository).check_workspace_health(workspace.workspace_id)

    assert health.status == "healthy"
    assert health.issues == []


def test_create_connection_profile_stores_secret_references_only():
    """Connection profile creation persists non-secret metadata."""

    repository = FakeProductRepository()
    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )
    repository.workspaces[workspace.workspace_id] = workspace

    profile = ProductService(repository).create_connection_profile(
        workspace_id=workspace.workspace_id,
        name=" Development ",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint=" http://localhost:8529 ",
        database="customer_graph",
        username="root",
        verify_ssl=False,
        secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
    )

    assert profile.connection_profile_id
    assert profile.name == "Development"
    assert profile.endpoint == "http://localhost:8529"
    assert profile.verify_ssl is False
    assert profile.secret_refs == {
        "password": {"kind": "env", "ref": "ARANGO_PASSWORD"}
    }
    assert repository.connection_profiles == [profile]


def test_workflow_dag_view_is_visualizer_ready():
    """Workflow DAG view exposes node and edge fields expected by a UI."""

    repository = FakeProductRepository()
    run = create_workflow_run(
        workspace_id="workspace-1",
        workflow_mode=WorkflowMode.PARALLEL_AGENTIC,
        status=WorkflowRunStatus.RUNNING,
        steps=[
            WorkflowStep(
                step_id="schema_analysis",
                label="Schema Analysis",
                status=WorkflowStepStatus.COMPLETED,
            ),
            WorkflowStep(
                step_id="reporting",
                label="Report Generation",
                status=WorkflowStepStatus.RUNNING,
            ),
        ],
        dag_edges=[
            WorkflowDAGEdge(
                from_step_id="schema_analysis",
                to_step_id="reporting",
            )
        ],
    )
    repository.workflow_runs[run.run_id] = run

    view = ProductService(repository).get_workflow_dag_view(run.run_id)

    assert view.status == "running"
    assert view.workflow_mode == "parallel_agentic"
    assert view.nodes[0]["id"] == "schema_analysis"
    assert view.edges[0]["from"] == "schema_analysis"
    assert view.edges[0]["to"] == "reporting"


def test_publish_report_creates_snapshot_updates_manifest_and_audits():
    """Publishing captures immutable content and records audit lineage."""

    repository = FakeProductRepository()
    report = create_report_manifest(
        workspace_id="workspace-1",
        run_id="run-1",
        title="Graph Report",
        status=ReportStatus.READY,
    )
    repository.reports[report.report_id] = report
    section = create_report_section(
        workspace_id="workspace-1",
        report_id=report.report_id,
        order=1,
        type=ReportSectionType.SUMMARY,
        title="Summary",
        content={"markdown": "Important result."},
    )
    chart = create_chart_spec(
        workspace_id="workspace-1",
        report_id=report.report_id,
        title="Top Scores",
        chart_type=ChartType.BAR,
        data={"rows": [{"name": "A", "score": 0.9}]},
    )
    repository.sections.append(section)
    repository.charts.append(chart)

    bundle = ProductService(repository).publish_report(
        report.report_id,
        actor="analyst@example.com",
    )

    updated_report = repository.reports[report.report_id]
    assert updated_report.status == ReportStatus.PUBLISHED
    assert (
        updated_report.published_snapshot_id
        == repository.snapshots[0].published_snapshot_id
    )
    assert repository.snapshots[0].content_hash.startswith("sha256:")
    assert repository.audit_events[0].action == "publish_report"
    assert bundle.manifest["status"] == "published"
    assert bundle.snapshots[0]["published_by"] == "analyst@example.com"


def _seed_report_for_export(repository: "FakeProductRepository") -> str:
    """Helper that builds a small report with a section + chart + lineage."""

    report = create_report_manifest(
        workspace_id="workspace-1",
        run_id="run-99",
        title="Quarterly Risk Report",
        status=ReportStatus.READY,
        summary="Top-line risk indicators for Q4.",
        version=2,
        requirement_version_id="requirement-version-7",
        analysis_execution_ids=["analysis-execution-42"],
        result_collections=["risk_scores"],
    )
    repository.reports[report.report_id] = report
    repository.sections.append(
        create_report_section(
            workspace_id="workspace-1",
            report_id=report.report_id,
            order=2,
            type=ReportSectionType.SUMMARY,
            title="Findings",
            content={"text": "* Concentration risk in segment **A**."},
            evidence_refs=[{"type": "row", "ref": "risk_scores/123"}],
        )
    )
    repository.sections.append(
        create_report_section(
            workspace_id="workspace-1",
            report_id=report.report_id,
            order=1,
            type=ReportSectionType.SUMMARY,
            title="Overview",
            content={"text": "All segments scored within tolerance except A."},
        )
    )
    repository.charts.append(
        create_chart_spec(
            workspace_id="workspace-1",
            report_id=report.report_id,
            title="Top Scores",
            chart_type=ChartType.BAR,
            data_source="risk_scores",
            data={"rows": [{"name": "A", "score": 0.9}]},
        )
    )
    return report.report_id


def test_export_report_markdown_includes_sections_charts_and_lineage():
    """FR-42 / MVP #14: Markdown export is audit-friendly and self-contained."""

    repository = FakeProductRepository()
    report_id = _seed_report_for_export(repository)

    result = ProductService(repository).export_report(report_id, format="markdown")

    assert result.media_type == "text/markdown; charset=utf-8"
    assert result.fmt == "markdown"
    assert result.filename.endswith(".md")
    body = result.content
    assert body.startswith("# Quarterly Risk Report")
    # Section ordering follows ``order`` (Overview is order=1, Findings order=2).
    assert body.index("### Overview") < body.index("### Findings")
    assert "* Concentration risk in segment **A**." in body
    assert "Top Scores" in body
    assert "## Lineage" in body
    assert "`run-99`" in body
    assert "`requirement-version-7`" in body
    assert "`analysis-execution-42`" in body


def test_export_report_html_is_self_contained_and_escapes_user_content():
    """HTML export embeds inline CSS and never trusts user content as markup."""

    repository = FakeProductRepository()
    report_id = _seed_report_for_export(repository)
    # Inject a section title containing an HTML control character to confirm
    # the renderer escapes user input rather than interpolating it raw.
    repository.sections[0].title = "Findings & <script>"

    result = ProductService(repository).export_report(report_id, format="html")

    assert result.media_type == "text/html; charset=utf-8"
    assert result.fmt == "html"
    assert result.filename.endswith(".html")
    body = result.content
    assert body.startswith("<!DOCTYPE html>")
    assert "<style>" in body
    assert "Findings &amp; &lt;script&gt;" in body
    assert "<script>" not in body.split("</style>")[1]
    assert "Lineage" in body
    assert "run-99" in body


def test_export_report_defaults_to_html_when_format_omitted():
    repository = FakeProductRepository()
    report_id = _seed_report_for_export(repository)

    result = ProductService(repository).export_report(report_id)

    assert result.fmt == "html"
    assert result.media_type.startswith("text/html")


def test_export_report_rejects_unsupported_format():
    repository = FakeProductRepository()
    report_id = _seed_report_for_export(repository)

    with pytest.raises(ValidationError, match="Unsupported report export format"):
        ProductService(repository).export_report(report_id, format="pdf")


def test_export_workspace_bundle_omits_connection_secret_refs():
    """Workspace export gathers metadata while excluding secret references."""

    repository = FakeProductRepository()
    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )
    repository.workspaces[workspace.workspace_id] = workspace
    connection_profile = create_connection_profile(
        workspace_id=workspace.workspace_id,
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
        secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
    )
    repository.connection_profiles.append(connection_profile)
    graph_profile = create_graph_profile(
        workspace_id=workspace.workspace_id,
        connection_profile_id=connection_profile.connection_profile_id,
        graph_name="customer_graph",
    )
    repository.graph_profiles.append(graph_profile)
    repository.source_documents.append(
        create_source_document(
            workspace_id=workspace.workspace_id,
            filename="requirements.md",
            mime_type="text/markdown",
            sha256="abc123",
            storage_mode=DocumentStorageMode.INLINE,
        )
    )
    repository.requirement_interviews.append(
        create_requirement_interview(
            workspace_id=workspace.workspace_id,
            graph_profile_id=graph_profile.graph_profile_id,
        )
    )
    repository.requirement_versions.append(
        create_requirement_version(workspace_id=workspace.workspace_id, version=1)
    )
    run = create_workflow_run(
        workspace_id=workspace.workspace_id,
        workflow_mode=WorkflowMode.AGENTIC,
    )
    repository.workflow_runs[run.run_id] = run
    report = create_report_manifest(
        workspace_id=workspace.workspace_id,
        run_id=run.run_id,
        title="Graph Report",
    )
    repository.reports[report.report_id] = report
    repository.sections.append(
        create_report_section(
            workspace_id=workspace.workspace_id,
            report_id=report.report_id,
            order=1,
            type=ReportSectionType.SUMMARY,
            title="Summary",
        )
    )
    repository.charts.append(
        create_chart_spec(
            workspace_id=workspace.workspace_id,
            report_id=report.report_id,
            title="Top Scores",
            chart_type=ChartType.BAR,
        )
    )
    repository.audit_events.append(
        create_audit_event(
            workspace_id=workspace.workspace_id,
            actor="analyst@example.com",
            action="export_workspace",
            target_type="workspace",
            target_id=workspace.workspace_id,
        )
    )

    bundle = ProductService(repository).export_workspace_bundle(workspace.workspace_id)
    doc = bundle.to_dict()

    assert doc["schema_version"]
    assert doc["workspace"]["workspace_id"] == workspace.workspace_id
    assert len(doc["graph_profiles"]) == 1
    assert len(doc["requirement_interviews"]) == 1
    assert len(doc["reports"]) == 1
    assert doc["analysis_epochs"] == []
    assert doc["analysis_executions"] == []
    assert "secret_refs" not in doc["connection_profiles"][0]
    assert doc["connection_profiles"][0]["secret_ref_keys"] == ["password"]
    assert doc["audit_events"][0]["action"] == "export_workspace"
    # The export action itself is audited but not included in its own bundle.
    export_events = [
        event
        for event in repository.audit_events
        if event.action == "export_workspace_bundle"
    ]
    assert len(export_events) == 1
    assert export_events[0].target_id == workspace.workspace_id


def test_import_workspace_bundle_recreates_exported_metadata_without_audit_by_default():
    """Workspace import recreates bundle metadata and skips audit history by default."""

    source_repository = FakeProductRepository()
    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )
    source_repository.workspaces[workspace.workspace_id] = workspace
    source_repository.connection_profiles.append(
        create_connection_profile(
            workspace_id=workspace.workspace_id,
            name="Development",
            deployment_mode=DeploymentMode.LOCAL,
            endpoint="http://localhost:8529",
            database="customer_graph",
            username="root",
            secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
        )
    )
    run = create_workflow_run(
        workspace_id=workspace.workspace_id,
        workflow_mode=WorkflowMode.AGENTIC,
    )
    source_repository.workflow_runs[run.run_id] = run
    epoch = create_analysis_epoch(
        workspace_id=workspace.workspace_id,
        name="Baseline",
    )
    source_repository.analysis_epochs[epoch.analysis_epoch_id] = epoch
    execution = create_analysis_execution(
        workspace_id=workspace.workspace_id,
        run_id=run.run_id,
        algorithm="pagerank",
        status=AnalysisExecutionStatus.COMPLETED,
        epoch_id=epoch.analysis_epoch_id,
        result_count=3,
    )
    source_repository.analysis_executions[execution.analysis_execution_id] = execution
    report = create_report_manifest(
        workspace_id=workspace.workspace_id,
        run_id=run.run_id,
        title="Graph Report",
    )
    source_repository.reports[report.report_id] = report
    source_repository.sections.append(
        create_report_section(
            workspace_id=workspace.workspace_id,
            report_id=report.report_id,
            order=1,
            type=ReportSectionType.SUMMARY,
            title="Summary",
        )
    )
    source_repository.charts.append(
        create_chart_spec(
            workspace_id=workspace.workspace_id,
            report_id=report.report_id,
            title="Top Scores",
            chart_type=ChartType.BAR,
        )
    )
    source_repository.audit_events.append(
        create_audit_event(
            workspace_id=workspace.workspace_id,
            actor="analyst@example.com",
            action="export_workspace",
            target_type="workspace",
            target_id=workspace.workspace_id,
        )
    )
    # FR-51 names templates explicitly, and use cases became product records in
    # the same FR-19..FR-26 work. The exporter predated both, so an "exported"
    # workspace silently lost them and could not be restored intact.
    use_case = create_use_case(
        workspace_id=workspace.workspace_id,
        title="Identify influential accounts",
    )
    source_repository.use_cases.append(use_case)
    template = create_analysis_template(
        workspace_id=workspace.workspace_id,
        name="PageRank baseline",
    )
    source_repository.analysis_templates.append(template)

    bundle = ProductService(source_repository).export_workspace_bundle(
        workspace.workspace_id
    )
    assert len(bundle.use_cases) == 1
    assert len(bundle.analysis_templates) == 1

    target_repository = FakeProductRepository()
    result = ProductService(target_repository).import_workspace_bundle(bundle)

    assert result.workspace_id == workspace.workspace_id
    assert result.counts["connection_profiles"] == 1
    assert result.counts["workflow_runs"] == 1
    assert result.counts["analysis_epochs"] == 1
    assert result.counts["analysis_executions"] == 1
    assert result.counts["reports"] == 1
    assert result.counts["report_sections"] == 1
    assert result.counts["chart_specs"] == 1
    assert result.counts["audit_events"] == 0
    assert result.counts["use_cases"] == 1
    assert result.counts["analysis_templates"] == 1
    assert [item.title for item in target_repository.use_cases] == [
        "Identify influential accounts"
    ]
    assert [item.name for item in target_repository.analysis_templates] == [
        "PageRank baseline"
    ]
    assert target_repository.workspaces[workspace.workspace_id].project_name == (
        "Graph Analytics"
    )
    assert target_repository.connection_profiles[0].secret_refs == {}
    assert target_repository.reports[report.report_id].title == "Graph Report"
    assert target_repository.analysis_epochs[epoch.analysis_epoch_id].name == "Baseline"
    assert (
        target_repository.analysis_executions[execution.analysis_execution_id].algorithm
        == "pagerank"
    )
    # The bundle's own historical audit events are not replayed (governed by
    # include_audit_events), but the import action itself is always logged.
    assert len(target_repository.audit_events) == 1
    assert target_repository.audit_events[0].action == "import_workspace_bundle"


def test_import_workspace_bundle_rejects_secret_refs():
    """Workspace import refuses bundles that contain secret reference metadata."""

    repository = FakeProductRepository()
    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )
    bundle = {
        "schema_version": "1.0.0",
        "workspace": workspace.to_dict(),
        "connection_profiles": [
            create_connection_profile(
                workspace_id=workspace.workspace_id,
                name="Development",
                deployment_mode=DeploymentMode.LOCAL,
                endpoint="http://localhost:8529",
                database="customer_graph",
                username="root",
                secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
            ).to_dict()
        ],
        "graph_profiles": [],
        "source_documents": [],
        "requirement_interviews": [],
        "requirement_versions": [],
        "workflow_runs": [],
        "reports": [],
        "audit_events": [],
    }

    try:
        ProductService(repository).import_workspace_bundle(bundle)
    except ValidationError as exc:
        assert "secret_refs" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for connection secret_refs")


def test_import_workspace_bundle_rejects_mismatched_workspace_id():
    """Workspace import validates all imported records belong to the bundle workspace."""

    repository = FakeProductRepository()
    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )
    bundle = {
        "schema_version": "1.0.0",
        "workspace": workspace.to_dict(),
        "connection_profiles": [],
        "graph_profiles": [
            create_graph_profile(
                workspace_id="workspace-other",
                connection_profile_id="connection-1",
                graph_name="customer_graph",
            ).to_dict()
        ],
        "source_documents": [],
        "requirement_interviews": [],
        "requirement_versions": [],
        "workflow_runs": [],
        "reports": [],
        "audit_events": [],
    }

    try:
        ProductService(repository).import_workspace_bundle(bundle)
    except ValidationError as exc:
        assert "mismatched workspace_id" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for mismatched workspace_id")


def test_verify_connection_profile_resolves_secret_and_updates_success_status():
    """Connection verification resolves secrets at runtime and stores only status."""

    repository = FakeProductRepository()
    profile = create_connection_profile(
        workspace_id="workspace-1",
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
        secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
    )
    repository.connection_profiles.append(profile)
    connector_calls = []

    def fake_connector(**kwargs):
        connector_calls.append(kwargs)
        return object()

    result = ProductService(
        repository,
        secret_resolver=MappingSecretResolver({"ARANGO_PASSWORD": "resolved-secret"}),
        db_connector=fake_connector,
    ).verify_connection_profile(profile.connection_profile_id)

    updated_profile = repository.get_connection_profile(profile.connection_profile_id)
    assert result.status == "success"
    assert result.error_message is None
    assert (
        updated_profile.last_verification_status == ConnectionVerificationStatus.SUCCESS
    )
    assert updated_profile.last_verified_at is not None
    assert connector_calls[0]["password"] == "resolved-secret"
    assert connector_calls[0]["verify_system"] is True
    assert updated_profile.secret_refs["password"]["ref"] == "ARANGO_PASSWORD"


def _connection_profile_for_gae_test():
    repository = FakeProductRepository()
    profile = create_connection_profile(
        workspace_id="workspace-1",
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
        secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
    )
    repository.connection_profiles.append(profile)
    return repository, profile


def test_verify_connection_profile_reports_gae_status_success(monkeypatch):
    """PRD FR-7: a reachable GAE deployment reports gae_status success.

    Patches the module-level factory (never touches the network / real
    .env credentials — graph_analytics_ai.config.get_arango_config()
    reloads a real .env file on every call, so relying on absent env
    vars here would be unreliable and could reach a live deployment).
    """

    class _FakeGaeConnection:
        def test_connection(self) -> bool:
            return True

    monkeypatch.setattr(
        "graph_analytics_ai.gae_connection.get_gae_connection",
        lambda: _FakeGaeConnection(),
    )

    repository, profile = _connection_profile_for_gae_test()
    result = ProductService(
        repository,
        secret_resolver=MappingSecretResolver({"ARANGO_PASSWORD": "resolved-secret"}),
        db_connector=lambda **_: object(),
    ).verify_connection_profile(profile.connection_profile_id)

    assert result.status == "success"
    assert result.gae_status == {"status": "success"}


def test_verify_connection_profile_reports_gae_status_failure_without_blocking(
    monkeypatch,
):
    """An unreachable GAE deployment never blocks DB verification."""

    def _raise():
        raise RuntimeError("GAE deployment unreachable")

    monkeypatch.setattr("graph_analytics_ai.gae_connection.get_gae_connection", _raise)

    repository, profile = _connection_profile_for_gae_test()
    result = ProductService(
        repository,
        secret_resolver=MappingSecretResolver({"ARANGO_PASSWORD": "resolved-secret"}),
        db_connector=lambda **_: object(),
    ).verify_connection_profile(profile.connection_profile_id)

    # DB verification succeeds regardless of GAE reachability.
    assert result.status == "success"
    assert result.gae_status == {
        "status": "failed",
        "message": "GAE deployment unreachable",
    }


def test_verify_connection_profile_masks_secret_on_failure():
    """Connection verification failure messages do not leak resolved secrets."""

    repository = FakeProductRepository()
    profile = create_connection_profile(
        workspace_id="workspace-1",
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
        secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
    )
    repository.connection_profiles.append(profile)

    def fake_connector(**kwargs):
        raise ConnectionError(f"bad password {kwargs['password']}")

    result = ProductService(
        repository,
        secret_resolver=MappingSecretResolver({"ARANGO_PASSWORD": "resolved-secret"}),
        db_connector=fake_connector,
    ).verify_connection_profile(profile.connection_profile_id, verify_system=False)

    updated_profile = repository.get_connection_profile(profile.connection_profile_id)
    assert result.status == "failed"
    assert "resolved-secret" not in result.error_message
    assert "***MASKED***" in result.error_message
    assert (
        updated_profile.last_verification_status == ConnectionVerificationStatus.FAILED
    )


def test_verify_connection_profile_requires_password_secret_ref():
    """Connection verification requires an explicit password secret reference."""

    repository = FakeProductRepository()
    profile = create_connection_profile(
        workspace_id="workspace-1",
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
    )
    repository.connection_profiles.append(profile)

    try:
        ProductService(
            repository,
            secret_resolver=MappingSecretResolver({}),
            db_connector=lambda **kwargs: object(),
        ).verify_connection_profile(profile.connection_profile_id)
    except ValidationError as exc:
        assert "password" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for missing password secret ref")


def test_discover_graph_profile_threads_force_llm_to_acquire_schema(monkeypatch):
    """PRD FR-58: force_llm reaches acquire_schema, the actual escalation owner."""

    repository = FakeProductRepository()
    profile = create_connection_profile(
        workspace_id="workspace-1",
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
        secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
    )
    repository.connection_profiles.append(profile)

    class FakeExtractor:
        def __init__(self, db, sample_size=100, max_samples_per_collection=3):
            pass

        def extract(self):
            schema = GraphSchema(database_name="customer_graph")
            schema.graph_names = ["CustomerGraph"]
            schema.vertex_collections = {
                "Device": CollectionSchema(
                    name="Device", type=CollectionType.VERTEX, document_count=10
                ),
            }
            schema.edge_collections = {}
            schema.relationships = []
            return schema

    acquire_schema_calls = []

    def fake_acquire_schema(db, **kwargs):
        acquire_schema_calls.append(kwargs)
        raise RuntimeError("stop before real acquisition — force_llm capture is enough")

    import graph_analytics_ai.product.service as service_module

    monkeypatch.setattr(service_module, "acquire_schema", fake_acquire_schema)

    ProductService(
        repository,
        secret_resolver=MappingSecretResolver({"ARANGO_PASSWORD": "resolved-secret"}),
        db_connector=lambda **_: object(),
        schema_extractor_factory=FakeExtractor,
    ).discover_graph_profile(
        connection_profile_id=profile.connection_profile_id,
        graph_name="CustomerGraph",
        force_llm=True,
    )

    assert len(acquire_schema_calls) == 1
    assert acquire_schema_calls[0]["force_llm"] is True


def test_discover_graph_profile_persists_schema_summary():
    """Graph discovery persists a profile from extracted schema metadata."""

    repository = FakeProductRepository()
    profile = create_connection_profile(
        workspace_id="workspace-1",
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
        secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
    )
    repository.connection_profiles.append(profile)
    connector_calls = []

    class FakeExtractor:
        def __init__(self, db, sample_size=100, max_samples_per_collection=3):
            self.db = db
            self.sample_size = sample_size
            self.max_samples_per_collection = max_samples_per_collection

        def extract(self):
            schema = GraphSchema(database_name="customer_graph")
            schema.graph_names = ["CustomerGraph"]
            schema.vertex_collections = {
                "Device": CollectionSchema(
                    name="Device",
                    type=CollectionType.VERTEX,
                    document_count=10,
                ),
                "IP": CollectionSchema(
                    name="IP",
                    type=CollectionType.VERTEX,
                    document_count=5,
                ),
            }
            schema.edge_collections = {
                "connects_to": CollectionSchema(
                    name="connects_to",
                    type=CollectionType.EDGE,
                    document_count=20,
                )
            }
            schema.relationships = [
                Relationship(
                    edge_collection="connects_to",
                    from_collection="Device",
                    to_collection="IP",
                    edge_count=20,
                )
            ]
            return schema

    def fake_connector(**kwargs):
        connector_calls.append(kwargs)
        return object()

    result = ProductService(
        repository,
        secret_resolver=MappingSecretResolver({"ARANGO_PASSWORD": "resolved-secret"}),
        db_connector=fake_connector,
        schema_extractor_factory=FakeExtractor,
    ).discover_graph_profile(
        connection_profile_id=profile.connection_profile_id,
        graph_name="CustomerGraph",
        created_by="analyst@example.com",
        sample_size=25,
    )

    persisted_profile = repository.graph_profiles[0]
    assert result.graph_profile["graph_name"] == "CustomerGraph"
    assert result.schema_summary["statistics"]["total_documents"] == 35
    assert persisted_profile.connection_profile_id == profile.connection_profile_id
    assert persisted_profile.vertex_collections == ["Device", "IP"]
    assert persisted_profile.edge_collections == ["connects_to"]
    assert persisted_profile.edge_definitions[0]["edge_collection"] == "connects_to"
    assert persisted_profile.counts["total_edges"] == 20
    assert persisted_profile.created_by == "analyst@example.com"
    assert connector_calls[0]["password"] == "resolved-secret"


def test_discover_graph_profile_bumps_version_on_rediscovery():
    """PRD FR-11: re-discovering the same graph updates in place, versioned.

    A second discovery of the same (connection_profile, graph_name) must
    NOT create a disconnected duplicate row — it should reuse the same
    graph_profile_id (so existing references stay valid) and bump
    ``version``.
    """

    repository = FakeProductRepository()
    connection_profile = create_connection_profile(
        workspace_id="workspace-1",
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
        secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
    )
    repository.connection_profiles.append(connection_profile)

    class FakeExtractor:
        def __init__(self, db, sample_size=100, max_samples_per_collection=3):
            pass

        def extract(self):
            schema = GraphSchema(database_name="customer_graph")
            schema.graph_names = ["CustomerGraph"]
            schema.vertex_collections = {
                "Device": CollectionSchema(
                    name="Device", type=CollectionType.VERTEX, document_count=10
                ),
            }
            schema.edge_collections = {}
            schema.relationships = []
            return schema

    service = ProductService(
        repository,
        secret_resolver=MappingSecretResolver({"ARANGO_PASSWORD": "resolved-secret"}),
        db_connector=lambda **_: object(),
        schema_extractor_factory=FakeExtractor,
    )

    first = service.discover_graph_profile(
        connection_profile_id=connection_profile.connection_profile_id,
        graph_name="CustomerGraph",
    )
    second = service.discover_graph_profile(
        connection_profile_id=connection_profile.connection_profile_id,
        graph_name="CustomerGraph",
    )

    assert len(repository.graph_profiles) == 1
    assert (
        first.graph_profile["graph_profile_id"]
        == second.graph_profile["graph_profile_id"]
    )
    assert first.graph_profile["version"] == 1
    assert second.graph_profile["version"] == 2


def test_discover_graph_profile_scopes_to_named_graph():
    """Graph discovery scopes vertex/edge collections to the requested named graph."""

    repository = FakeProductRepository()
    profile = create_connection_profile(
        workspace_id="workspace-1",
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
        secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
    )
    repository.connection_profiles.append(profile)

    class FakeExtractor:
        def __init__(self, db, sample_size=100, max_samples_per_collection=3):
            self.db = db

        def extract(self):
            schema = GraphSchema(database_name="customer_graph")
            # Database has 2 graphs but we request only one
            schema.graph_names = ["AdtechGraph", "RagCorpus"]
            schema.vertex_collections = {
                "Device": CollectionSchema(
                    name="Device", type=CollectionType.VERTEX, document_count=10
                ),
                "IP": CollectionSchema(
                    name="IP", type=CollectionType.VERTEX, document_count=5
                ),
                "RagDoc": CollectionSchema(
                    name="RagDoc", type=CollectionType.VERTEX, document_count=99
                ),
            }
            schema.edge_collections = {
                "SEEN_ON_IP": CollectionSchema(
                    name="SEEN_ON_IP", type=CollectionType.EDGE, document_count=20
                ),
                "RagEmbeds": CollectionSchema(
                    name="RagEmbeds", type=CollectionType.EDGE, document_count=300
                ),
            }
            return schema

    class FakeGraphHandle:
        def edge_definitions(self):
            return [
                {
                    "edge_collection": "SEEN_ON_IP",
                    "from_vertex_collections": ["Device"],
                    "to_vertex_collections": ["IP"],
                }
            ]

        def orphan_collections(self):
            return []

    class FakeCollection:
        def __init__(self, count_value):
            self._count_value = count_value

        def count(self):
            return self._count_value

    class FakeDB:
        def graph(self, name):
            assert name == "AdtechGraph"
            return FakeGraphHandle()

        def collection(self, name):
            return FakeCollection({"Device": 10, "IP": 5, "SEEN_ON_IP": 20}[name])

    def fake_connector(**kwargs):
        return FakeDB()

    result = ProductService(
        repository,
        secret_resolver=MappingSecretResolver({"ARANGO_PASSWORD": "resolved-secret"}),
        db_connector=fake_connector,
        schema_extractor_factory=FakeExtractor,
    ).discover_graph_profile(
        connection_profile_id=profile.connection_profile_id,
        graph_name="AdtechGraph",
    )

    persisted_profile = repository.graph_profiles[0]
    assert persisted_profile.graph_name == "AdtechGraph"
    assert persisted_profile.vertex_collections == ["Device", "IP"]
    assert persisted_profile.edge_collections == ["SEEN_ON_IP"]
    assert persisted_profile.counts["total_documents"] == 15
    assert persisted_profile.counts["total_edges"] == 20
    assert persisted_profile.metadata["scope"] == "named_graph"
    assert sorted(persisted_profile.metadata["available_graphs"]) == [
        "AdtechGraph",
        "RagCorpus",
    ]
    assert result.graph_profile["graph_name"] == "AdtechGraph"


def test_list_connection_profile_graphs_returns_metadata_per_graph():
    """Listing graphs returns scoped metadata per named graph, skipping system graphs."""

    repository = FakeProductRepository()
    profile = create_connection_profile(
        workspace_id="workspace-1",
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
        secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
    )
    repository.connection_profiles.append(profile)

    class FakeCollection:
        def __init__(self, count_value):
            self._count_value = count_value

        def count(self):
            return self._count_value

    class FakeDB:
        def graphs(self):
            return [
                {
                    "name": "AdtechGraph",
                    "edge_definitions": [
                        {
                            "edge_collection": "SEEN_ON_IP",
                            "from_vertex_collections": ["Device"],
                            "to_vertex_collections": ["IP"],
                        }
                    ],
                    "orphan_collections": [],
                },
                {
                    "name": "RagCorpus",
                    "edge_definitions": [
                        {
                            "edge_collection": "RagEmbeds",
                            "from_vertex_collections": ["RagDoc"],
                            "to_vertex_collections": ["RagDoc"],
                        }
                    ],
                    "orphan_collections": [],
                },
                {
                    "name": "_viewpointGraph",
                    "edge_definitions": [],
                    "orphan_collections": [],
                },
            ]

        def collection(self, name):
            return FakeCollection(
                {
                    "Device": 10,
                    "IP": 5,
                    "SEEN_ON_IP": 20,
                    "RagDoc": 99,
                    "RagEmbeds": 300,
                }[name]
            )

    def fake_connector(**kwargs):
        return FakeDB()

    result = ProductService(
        repository,
        secret_resolver=MappingSecretResolver({"ARANGO_PASSWORD": "resolved-secret"}),
        db_connector=fake_connector,
    ).list_connection_profile_graphs(profile.connection_profile_id)

    assert result.connection_profile_id == profile.connection_profile_id
    assert result.workspace_id == profile.workspace_id
    assert result.database == profile.database
    names = [graph.name for graph in result.graphs]
    assert names == ["AdtechGraph", "RagCorpus"]
    adtech = result.graphs[0]
    assert adtech.vertex_collections == ["Device", "IP"]
    assert adtech.edge_collections == ["SEEN_ON_IP"]
    assert adtech.vertex_count == 15
    assert adtech.edge_count == 20
    assert adtech.is_system is False


def test_discover_graph_profile_rejects_unknown_requested_graph():
    """Graph discovery validates explicit graph names when named graphs exist."""

    repository = FakeProductRepository()
    profile = create_connection_profile(
        workspace_id="workspace-1",
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
        secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
    )
    repository.connection_profiles.append(profile)

    class FakeExtractor:
        def __init__(self, db, sample_size=100, max_samples_per_collection=3):
            self.db = db

        def extract(self):
            schema = GraphSchema(database_name="customer_graph")
            schema.graph_names = ["CustomerGraph"]
            return schema

    try:
        ProductService(
            repository,
            secret_resolver=MappingSecretResolver(
                {"ARANGO_PASSWORD": "resolved-secret"}
            ),
            db_connector=lambda **kwargs: object(),
            schema_extractor_factory=FakeExtractor,
        ).discover_graph_profile(
            connection_profile_id=profile.connection_profile_id,
            graph_name="MissingGraph",
        )
    except ValidationError as exc:
        assert "MissingGraph" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for unknown graph name")


def test_requirements_copilot_generates_and_approves_draft():
    """Requirements Copilot creates a schema-aware draft and approved version."""

    repository = FakeProductRepository()
    graph_profile = create_graph_profile(
        workspace_id="workspace-1",
        connection_profile_id="connection-1",
        graph_name="CustomerGraph",
        vertex_collections=["Device", "IP"],
        edge_collections=["connects_to"],
        counts={"total_documents": 35, "total_edges": 20},
        metadata={
            "schema_summary": {
                "statistics": {"total_documents": 35},
                "graphs": ["CustomerGraph"],
            }
        },
    )
    repository.graph_profiles.append(graph_profile)
    service = ProductService(repository)

    interview = service.start_requirements_copilot(
        graph_profile_id=graph_profile.graph_profile_id,
        domain="AdTech",
        created_by="analyst@example.com",
    )
    assert interview.domain == "AdTech"
    assert interview.schema_observations["vertex_collections"] == ["Device", "IP"]
    assert interview.questions[0]["id"] == "business_goal"

    service.answer_requirements_copilot_question(
        interview.requirement_interview_id,
        question_id="business_goal",
        answer="Improve audience planning",
        actor="analyst@example.com",
    )
    service.answer_requirements_copilot_question(
        interview.requirement_interview_id,
        question_id="analytics_questions",
        answer="Rank identity clusters\nFind high-risk devices",
        actor="analyst@example.com",
    )
    service.answer_requirements_copilot_question(
        interview.requirement_interview_id,
        question_id="constraints",
        answer="Finish in 15 minutes; include evidence",
        actor="analyst@example.com",
    )

    draft = service.generate_requirements_copilot_draft(
        interview.requirement_interview_id
    )
    updated_interview = repository.get_requirement_interview(
        interview.requirement_interview_id
    )
    assert updated_interview.status == RequirementInterviewStatus.READY_FOR_REVIEW
    assert "Observed Graph Schema" in draft.draft_brd
    assert "Improve audience planning" in draft.draft_brd
    assert any(
        label["label"] == "observed_from_schema" for label in draft.provenance_labels
    )
    assert any(label["label"] == "user_provided" for label in draft.provenance_labels)

    version = service.approve_requirements_copilot_draft(
        interview.requirement_interview_id,
        version=1,
        approved_by="approver@example.com",
    )
    approved_interview = repository.get_requirement_interview(
        interview.requirement_interview_id
    )
    assert approved_interview.status == RequirementInterviewStatus.APPROVED
    assert version.status == RequirementVersionStatus.APPROVED
    assert version.requirement_interview_id == interview.requirement_interview_id
    assert version.objectives[0]["text"] == "Improve audience planning"
    assert version.requirements[0]["text"] == "Rank identity clusters"
    assert version.constraints[0]["text"] == "Finish in 15 minutes"
    assert version.metadata["approved_by"] == "approver@example.com"
    approval_events = [
        event
        for event in repository.audit_events
        if event.action == "approve_requirement_version"
    ]
    assert len(approval_events) == 1
    assert approval_events[0].actor == "approver@example.com"
    assert approval_events[0].target_id == version.requirement_version_id


def test_requirements_copilot_auto_increments_and_supersedes_prior():
    """Approving a new draft auto-increments version and flips priors to SUPERSEDED."""

    repository = FakeProductRepository()
    graph_profile = create_graph_profile(
        workspace_id="workspace-1",
        connection_profile_id="connection-1",
        graph_name="AdtechGraph",
        vertex_collections=["Audience"],
        edge_collections=["targets"],
    )
    repository.graph_profiles.append(graph_profile)
    service = ProductService(repository)

    def _approve(answers, *, expected_version, based_on=None):
        interview = service.start_requirements_copilot(
            graph_profile_id=graph_profile.graph_profile_id,
            domain="AdTech",
            based_on_version_id=based_on,
        )
        for question_id, answer in answers.items():
            service.answer_requirements_copilot_question(
                interview.requirement_interview_id,
                question_id=question_id,
                answer=answer,
            )
        service.generate_requirements_copilot_draft(interview.requirement_interview_id)
        approved = service.approve_requirements_copilot_draft(
            interview.requirement_interview_id,
            approved_by="approver@example.com",
        )
        assert approved.version == expected_version
        return approved, interview

    v1, _ = _approve(
        {
            "business_goal": "Improve audience planning",
            "analytics_questions": "Rank identity clusters",
            "constraints": "Finish in 15 minutes",
        },
        expected_version=1,
    )
    assert v1.status == RequirementVersionStatus.APPROVED
    # The interview's domain ("AdTech") is stamped onto the version's metadata
    # so a subsequent "Reopen Copilot to Produce v(N+1)" can prefill the
    # Domain field instead of forcing the user to retype it.
    assert v1.metadata["domain"] == "AdTech"

    # Reopen pre-populates the new interview from v1's content. Crucially, the
    # caller is NOT passing `domain=` here — the service must inherit it from
    # v1's metadata so the v2 interview is still tagged "AdTech".
    interview_v2 = service.start_requirements_copilot(
        graph_profile_id=graph_profile.graph_profile_id,
        based_on_version_id=v1.requirement_version_id,
    )
    assert interview_v2.domain == "AdTech"
    answer_map = {
        str(answer["question_id"]): str(answer["answer"])
        for answer in interview_v2.answers
    }
    assert answer_map.get("business_goal") == "Improve audience planning"
    assert "Rank identity clusters" in answer_map.get("analytics_questions", "")
    assert interview_v2.metadata["based_on_version_id"] == v1.requirement_version_id
    assert interview_v2.metadata["based_on_version"] == 1

    # Approve a second version (still no explicit version number passed).
    service.answer_requirements_copilot_question(
        interview_v2.requirement_interview_id,
        question_id="business_goal",
        answer="Improve audience planning and personalisation",
    )
    service.generate_requirements_copilot_draft(interview_v2.requirement_interview_id)
    v2 = service.approve_requirements_copilot_draft(
        interview_v2.requirement_interview_id,
        approved_by="approver@example.com",
    )
    assert v2.version == 2
    assert v2.metadata["based_on_version_id"] == v1.requirement_version_id
    assert v2.metadata["based_on_version"] == 1
    # Domain must continue to propagate so v2 → v3 still prefills correctly.
    assert v2.metadata["domain"] == "AdTech"

    # v1 must now be SUPERSEDED, and only v2 should be APPROVED.
    versions = sorted(
        repository.list_requirement_versions("workspace-1"),
        key=lambda item: item.version,
    )
    assert [version.status for version in versions] == [
        RequirementVersionStatus.SUPERSEDED,
        RequirementVersionStatus.APPROVED,
    ]
    assert versions[0].metadata["superseded_by"] == v2.requirement_version_id
    assert "superseded_at" in versions[0].metadata


def test_approved_requirement_version_content_is_immutable():
    """PRD FR-17: editing the content of an APPROVED version is rejected.

    The supersede transition (status -> SUPERSEDED, metadata patch) is the
    one sanctioned mutation and must continue to work; see
    test_requirements_copilot_auto_increments_and_supersedes_prior.
    """

    import dataclasses

    repository = FakeProductRepository()
    version = create_requirement_version(
        workspace_id="workspace-1",
        version=1,
        status=RequirementVersionStatus.APPROVED,
        summary="Original summary",
    )
    repository.requirement_versions.append(version)

    edited = dataclasses.replace(version, summary="Rewritten after approval")
    with pytest.raises(ConflictError):
        repository.update_requirement_version(edited)


def test_requirements_copilot_rejects_collision_on_explicit_version():
    """Passing an existing version explicitly is rejected to prevent silent dupes."""

    repository = FakeProductRepository()
    graph_profile = create_graph_profile(
        workspace_id="workspace-1",
        connection_profile_id="connection-1",
        graph_name="AdtechGraph",
    )
    repository.graph_profiles.append(graph_profile)
    service = ProductService(repository)

    interview = service.start_requirements_copilot(
        graph_profile_id=graph_profile.graph_profile_id,
    )
    service.answer_requirements_copilot_question(
        interview.requirement_interview_id,
        question_id="business_goal",
        answer="Goal",
    )
    service.generate_requirements_copilot_draft(interview.requirement_interview_id)
    service.approve_requirements_copilot_draft(
        interview.requirement_interview_id, version=1
    )

    interview_two = service.start_requirements_copilot(
        graph_profile_id=graph_profile.graph_profile_id,
    )
    service.answer_requirements_copilot_question(
        interview_two.requirement_interview_id,
        question_id="business_goal",
        answer="Goal",
    )
    service.generate_requirements_copilot_draft(interview_two.requirement_interview_id)

    try:
        service.approve_requirements_copilot_draft(
            interview_two.requirement_interview_id, version=1
        )
    except ValidationError as exc:
        assert "v1" in str(exc) or "already exists" in str(exc)
    else:
        raise AssertionError("Expected ValidationError on version collision")


def test_requirements_copilot_approval_requires_draft():
    """Requirements Copilot approval requires generated draft content."""

    repository = FakeProductRepository()
    graph_profile = create_graph_profile(
        workspace_id="workspace-1",
        connection_profile_id="connection-1",
        graph_name="CustomerGraph",
    )
    repository.graph_profiles.append(graph_profile)
    interview = ProductService(repository).start_requirements_copilot(
        graph_profile.graph_profile_id
    )

    try:
        ProductService(repository).approve_requirements_copilot_draft(
            interview.requirement_interview_id,
            version=1,
        )
    except ValidationError as exc:
        assert "draft" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for missing draft")


def test_workflow_helpers_create_update_and_expose_recovery_actions():
    """Workflow helpers support visualizer polling and recovery action display.

    Uses TRADITIONAL mode because AGENTIC mode now (PRD v0.4 decision 1)
    ignores user-supplied step labels and replaces them with the
    canonical six-step layout. This test continues to validate the
    free-form labelling path that traditional runs use.
    """

    repository = FakeProductRepository()
    service = ProductService(repository)
    run = service.create_workflow_run_from_steps(
        workspace_id="workspace-1",
        workflow_mode=WorkflowMode.TRADITIONAL,
        steps=[
            WorkflowStep(step_id="schema", label="Schema Analysis"),
            WorkflowStep(step_id="report", label="Report Generation"),
        ],
        dag_edges=[
            WorkflowDAGEdge(from_step_id="schema", to_step_id="report"),
        ],
        metadata={"source": "test"},
    )
    assert run.status == WorkflowRunStatus.QUEUED
    assert repository.workflow_runs[run.run_id].metadata["source"] == "test"

    started = service.start_workflow_run(run.run_id)
    assert started.status == WorkflowRunStatus.RUNNING
    assert started.started_at is not None

    result = service.update_workflow_step(
        run_id=run.run_id,
        step_id="schema",
        status=WorkflowStepStatus.COMPLETED,
        outputs={"collections": ["Device"]},
        artifact_refs=[{"type": "graph_profile", "id": "graph-profile-1"}],
    )
    updated_run = repository.workflow_runs[run.run_id]
    assert updated_run.steps[0].status == WorkflowStepStatus.COMPLETED
    assert updated_run.steps[0].outputs["collections"] == ["Device"]
    assert result.dag_view["nodes"][0]["id"] == "schema"

    failure = service.update_workflow_step(
        run_id=run.run_id,
        step_id="report",
        status=WorkflowStepStatus.FAILED,
        errors=["LLM timeout"],
    )
    assert failure.workflow_run["status"] == "failed"
    assert service.supported_workflow_recovery_actions(run.run_id)["report"] == [
        "retry",
        "open_logs",
    ]

    retry = service.update_workflow_step(
        run_id=run.run_id,
        step_id="report",
        status=WorkflowStepStatus.RUNNING,
    )
    retried_run = repository.workflow_runs[run.run_id]
    assert retry.workflow_run["status"] == "running"
    assert retried_run.steps[1].retry_count == 1


def test_workflow_helper_rejects_invalid_dag_edges():
    """Workflow creation validates DAG edge references.

    Uses TRADITIONAL mode because AGENTIC mode (PRD v0.4 decision 1)
    discards user-supplied steps and edges and seeds the canonical
    six-step layout instead, so it can never see an invalid
    user-supplied edge.
    """

    repository = FakeProductRepository()
    try:
        ProductService(repository).create_workflow_run_from_steps(
            workspace_id="workspace-1",
            workflow_mode=WorkflowMode.TRADITIONAL,
            steps=[WorkflowStep(step_id="schema", label="Schema Analysis")],
            dag_edges=[WorkflowDAGEdge(from_step_id="schema", to_step_id="missing")],
        )
    except ValidationError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for invalid DAG edge")


def test_agentic_run_warns_when_discarding_caller_supplied_steps(caplog):
    """FR-31a's step substitution must announce itself.

    Agentic mode replaces caller-supplied steps with the canonical DAG, whose
    steps start PENDING. A seeder that passes in COMPLETED steps and then marks
    only the run completed produces a run rendering as finished with every step
    "pending" — a self-contradictory screen. The discard is correct; being
    silent about it is not.
    """

    repository = FakeProductRepository()
    service = ProductService(repository)

    with caplog.at_level(logging.WARNING):
        run = service.create_workflow_run_from_steps(
            workspace_id="workspace-1",
            workflow_mode=WorkflowMode.AGENTIC,
            steps=[
                WorkflowStep(
                    step_id="mine",
                    label="My Step",
                    status=WorkflowStepStatus.COMPLETED,
                )
            ],
            dag_edges=[],
        )

    assert any(
        "discarding" in record.message and "FR-31a" in record.message
        for record in caplog.records
    ), "expected a warning naming the discard"

    # The substitution itself is unchanged: canonical steps, all pending.
    assert [step.step_id for step in run.steps] != ["mine"]
    assert all(step.status is WorkflowStepStatus.PENDING for step in run.steps)


def test_agentic_run_does_not_warn_when_no_steps_supplied(caplog):
    """Callers that supply nothing have nothing discarded — stay quiet."""

    repository = FakeProductRepository()
    with caplog.at_level(logging.WARNING):
        ProductService(repository).create_workflow_run_from_steps(
            workspace_id="workspace-1",
            workflow_mode=WorkflowMode.AGENTIC,
            steps=[],
            dag_edges=[],
        )

    assert not [r for r in caplog.records if "discarding" in r.message]


def test_assign_graph_profile_collection_roles_happy_path():
    """PRD FR-10: users can assign analytical roles to a profile's collections."""

    repository = FakeProductRepository()
    graph_profile = create_graph_profile(
        workspace_id="workspace-1",
        connection_profile_id="connection-1",
        graph_name="CustomerGraph",
        vertex_collections=["Person", "Company"],
        edge_collections=["works_at"],
    )
    repository.graph_profiles.append(graph_profile)

    updated = ProductService(repository).assign_graph_profile_collection_roles(
        graph_profile.graph_profile_id,
        collection_roles={
            "entity": ["Person", "Company"],
            "relationship": ["works_at"],
        },
        actor="analyst@example.com",
    )

    assert updated.collection_roles == {
        "entity": ["Person", "Company"],
        "relationship": ["works_at"],
    }
    persisted = repository.get_graph_profile(graph_profile.graph_profile_id)
    assert persisted.collection_roles == updated.collection_roles
    role_events = [
        event
        for event in repository.audit_events
        if event.action == "assign_graph_profile_collection_roles"
    ]
    assert len(role_events) == 1
    assert role_events[0].actor == "analyst@example.com"


def test_assign_graph_profile_collection_roles_rejects_unknown_collection():
    """Roles can only reference collections already discovered on the profile."""

    repository = FakeProductRepository()
    graph_profile = create_graph_profile(
        workspace_id="workspace-1",
        connection_profile_id="connection-1",
        graph_name="CustomerGraph",
        vertex_collections=["Person"],
        edge_collections=[],
    )
    repository.graph_profiles.append(graph_profile)

    with pytest.raises(ValidationError):
        ProductService(repository).assign_graph_profile_collection_roles(
            graph_profile.graph_profile_id,
            collection_roles={"entity": ["Person", "NotOnThisProfile"]},
        )


def test_graph_profile_collection_roles_survive_rediscovery():
    """PRD FR-11 + FR-10: re-discovery preserves manually assigned roles."""

    repository = FakeProductRepository()
    connection_profile = create_connection_profile(
        workspace_id="workspace-1",
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
        secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
    )
    repository.connection_profiles.append(connection_profile)

    class FakeExtractor:
        def __init__(self, db, sample_size=100, max_samples_per_collection=3):
            pass

        def extract(self):
            schema = GraphSchema(database_name="customer_graph")
            schema.graph_names = ["CustomerGraph"]
            schema.vertex_collections = {
                "Device": CollectionSchema(
                    name="Device", type=CollectionType.VERTEX, document_count=10
                ),
            }
            schema.edge_collections = {}
            schema.relationships = []
            return schema

    service = ProductService(
        repository,
        secret_resolver=MappingSecretResolver({"ARANGO_PASSWORD": "resolved-secret"}),
        db_connector=lambda **_: object(),
        schema_extractor_factory=FakeExtractor,
    )

    first = service.discover_graph_profile(
        connection_profile_id=connection_profile.connection_profile_id,
        graph_name="CustomerGraph",
    )
    service.assign_graph_profile_collection_roles(
        first.graph_profile["graph_profile_id"],
        collection_roles={"entity": ["Device"]},
    )

    second = service.discover_graph_profile(
        connection_profile_id=connection_profile.connection_profile_id,
        graph_name="CustomerGraph",
    )

    assert second.graph_profile["collection_roles"] == {"entity": ["Device"]}


def test_schema_observations_use_conceptual_schema_when_present():
    """PRD FR-72: the copilot reasons over logical types, not raw collections.

    On an LPG graph the collection names are meaningless to a business
    reviewer ("Entities"/"Relationships"), so the conceptual schema's
    entity/relationship types and the graph purpose must be surfaced.
    """

    repository = FakeProductRepository()
    graph_profile = create_graph_profile(
        workspace_id="workspace-1",
        connection_profile_id="connection-1",
        graph_name="KnowledgeGraph",
        vertex_collections=["Entities"],
        edge_collections=["Relationships"],
        graph_purpose="knowledge_graph",
        conceptual_schema={
            "entities": [
                {"name": "Person", "labels": ["Person"], "properties": []},
                {"name": "Org", "labels": ["Org"], "properties": []},
            ],
            "relationships": [
                {
                    "type": "WORKS_AT",
                    "fromEntity": "Person",
                    "toEntity": "Org",
                    "properties": [],
                }
            ],
            "properties": [],
        },
    )
    repository.graph_profiles.append(graph_profile)
    service = ProductService(repository)

    observations = service._schema_observations_from_graph_profile(graph_profile)

    assert observations["graph_purpose"] == "knowledge_graph"
    assert observations["entity_types"] == ["Person", "Org"]
    assert observations["entity_type_count"] == 2
    assert observations["relationship_types"] == [
        {"type": "WORKS_AT", "from": "Person", "to": "Org"}
    ]
    assert observations["relationship_type_count"] == 1
    # Raw collections are still retained for pre-v0.6 consumers.
    assert observations["vertex_collections"] == ["Entities"]

    interview = service.start_requirements_copilot(
        graph_profile_id=graph_profile.graph_profile_id,
        domain="HR",
    )
    draft = service.generate_requirements_copilot_draft(
        interview.requirement_interview_id
    )
    assert "Entity types (2): Person, Org" in draft.draft_brd
    assert "WORKS_AT (Person→Org)" in draft.draft_brd
    assert "Graph purpose: knowledge_graph" in draft.draft_brd


def test_schema_observations_fall_back_to_collections_for_legacy_profiles():
    """Profiles discovered before v0.6 have no conceptual schema — still work."""

    repository = FakeProductRepository()
    graph_profile = create_graph_profile(
        workspace_id="workspace-1",
        connection_profile_id="connection-1",
        graph_name="LegacyGraph",
        vertex_collections=["Device", "IP"],
        edge_collections=["connects_to"],
    )
    repository.graph_profiles.append(graph_profile)
    service = ProductService(repository)

    observations = service._schema_observations_from_graph_profile(graph_profile)

    assert "entity_types" not in observations
    assert "graph_purpose" not in observations
    assert observations["vertex_collections"] == ["Device", "IP"]

    interview = service.start_requirements_copilot(
        graph_profile_id=graph_profile.graph_profile_id
    )
    draft = service.generate_requirements_copilot_draft(
        interview.requirement_interview_id
    )
    assert "Vertex collections: Device, IP" in draft.draft_brd
    assert "Entity types" not in draft.draft_brd


def _workspace_for_upload(repository):
    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )
    repository.workspaces[workspace.workspace_id] = workspace
    return workspace


def test_upload_source_document_extracts_text_and_audits(monkeypatch):
    """PRD FR-13/FR-14: uploaded documents are parsed and persisted."""

    import base64

    # FR-15 extraction needs an LLM provider; force the unavailable path
    # so this test covers upload + text extraction deterministically.
    monkeypatch.setattr(
        ProductService, "_extract_requirements", staticmethod(lambda _doc: None)
    )

    repository = FakeProductRepository()
    workspace = _workspace_for_upload(repository)
    body = "# Requirements\n\nRank identity clusters by risk.\n"

    document = ProductService(repository).upload_source_document(
        workspace_id=workspace.workspace_id,
        filename="requirements.md",
        content_base64=base64.b64encode(body.encode("utf-8")).decode("ascii"),
        mime_type="text/markdown",
        actor="analyst@example.com",
    )

    assert document.filename == "requirements.md"
    assert document.storage_mode is DocumentStorageMode.EXTRACT_ONLY
    assert "Rank identity clusters" in document.extracted_text
    # sha256 is of the raw bytes, so it round-trips independently of parsing.
    assert document.sha256 == hashlib.sha256(body.encode("utf-8")).hexdigest()
    assert document.metadata["byte_size"] == len(body.encode("utf-8"))
    assert repository.source_documents[0].document_id == document.document_id

    upload_events = [
        event
        for event in repository.audit_events
        if event.action == "upload_source_document"
    ]
    assert len(upload_events) == 1
    assert upload_events[0].actor == "analyst@example.com"


def test_upload_source_document_survives_extraction_failure(monkeypatch):
    """FR-15 extraction is best-effort — an LLM outage must not fail the upload.

    Fails at the real boundary (the extractor itself), not by stubbing out
    the very try/except that provides the resilience.
    """

    import base64

    import graph_analytics_ai.ai.documents.extractor as extractor_module

    class _UnavailableExtractor:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("no LLM provider configured")

    monkeypatch.setattr(
        extractor_module, "RequirementsExtractor", _UnavailableExtractor
    )

    repository = FakeProductRepository()
    workspace = _workspace_for_upload(repository)
    body = "# Notes\n\nSome requirement text.\n"

    document = ProductService(repository).upload_source_document(
        workspace_id=workspace.workspace_id,
        filename="requirements.md",
        content_base64=base64.b64encode(body.encode("utf-8")).decode("ascii"),
    )

    # Upload succeeds and text is still extracted; only the LLM-derived
    # structured summary is absent.
    assert "Some requirement text." in document.extracted_text
    assert "extracted_requirements" not in document.metadata
    assert repository.source_documents[0].document_id == document.document_id


def test_upload_source_document_rejects_unsupported_type():
    """Only the PRD's listed document types are accepted (FR-13)."""

    import base64

    repository = FakeProductRepository()
    workspace = _workspace_for_upload(repository)

    with pytest.raises(ValidationError) as exc_info:
        ProductService(repository).upload_source_document(
            workspace_id=workspace.workspace_id,
            filename="malware.exe",
            content_base64=base64.b64encode(b"MZ").decode("ascii"),
        )
    assert "Unsupported document type" in str(exc_info.value)


def test_upload_source_document_rejects_invalid_base64():
    """A malformed payload is a client error, not a 500."""

    repository = FakeProductRepository()
    workspace = _workspace_for_upload(repository)

    with pytest.raises(ValidationError) as exc_info:
        ProductService(repository).upload_source_document(
            workspace_id=workspace.workspace_id,
            filename="requirements.md",
            content_base64="not-valid-base64!!!",
        )
    assert "base64" in str(exc_info.value)


def test_upload_source_document_rejects_empty_content():
    """An empty upload is rejected rather than persisted as a stub row."""

    repository = FakeProductRepository()
    workspace = _workspace_for_upload(repository)

    with pytest.raises(ValidationError) as exc_info:
        ProductService(repository).upload_source_document(
            workspace_id=workspace.workspace_id,
            filename="requirements.md",
            content_base64="",
        )
    assert "empty" in str(exc_info.value)


def _catalog_service_fixture():
    repository = FakeProductRepository()
    workspace = create_workspace(
        customer_name="Example",
        project_name="Catalog",
        environment="test",
    )
    repository.create_workspace(workspace)
    run = create_workflow_run(
        workspace_id=workspace.workspace_id,
        workflow_mode=WorkflowMode.AGENTIC,
        requirement_version_id="requirement-1",
        graph_profile_id="graph-1",
        template_ids=["template-1", "template-2"],
    )
    repository.create_workflow_run(run)
    return repository, ProductService(repository), workspace, run


def test_record_analysis_execution_updates_run_epoch_and_search():
    """FR-31/46: catalog writes populate run lineage and searchable epoch rows."""

    repository, service, workspace, run = _catalog_service_fixture()
    epoch = service.create_analysis_epoch(
        workspace_id=workspace.workspace_id,
        name="Baseline",
        tags=["monthly"],
    )

    execution = service.record_analysis_execution(
        run_id=run.run_id,
        algorithm="pagerank",
        status=AnalysisExecutionStatus.COMPLETED,
        template_id="template-1",
        use_case_id="use-case-1",
        epoch_id=epoch.analysis_epoch_id,
        result_count=12,
        performance_metrics={"execution_time_seconds": 2.0},
    )

    persisted_run = repository.get_workflow_run(run.run_id)
    persisted_epoch = repository.get_analysis_epoch(epoch.analysis_epoch_id)
    matches = service.list_analysis_executions(
        workspace_id=workspace.workspace_id,
        algorithm="pagerank",
        status="completed",
        epoch_id=epoch.analysis_epoch_id,
    )
    stats = service.get_analysis_catalog_stats(workspace.workspace_id)

    assert persisted_run.analysis_execution_ids == [execution.analysis_execution_id]
    assert persisted_epoch.analysis_execution_ids == [execution.analysis_execution_id]
    assert persisted_epoch.analysis_count == 1
    assert matches == [execution]
    assert stats["execution_count"] == 1
    assert stats["epoch_count"] == 1
    assert stats["executions_by_status"] == {"completed": 1}
    assert stats["executions_by_algorithm"] == {"pagerank": 1}


def test_compare_and_lineage_cover_report_to_requirement_chain():
    """FR-47/48: comparisons retain full report-to-requirement lineage."""

    repository, service, workspace, run = _catalog_service_fixture()
    first = service.record_analysis_execution(
        run_id=run.run_id,
        algorithm="pagerank",
        template_id="template-1",
        use_case_id="use-case-1",
        result_count=10,
        performance_metrics={"execution_time_seconds": 5.0},
    )
    second = service.record_analysis_execution(
        run_id=run.run_id,
        algorithm="pagerank",
        template_id="template-2",
        use_case_id="use-case-1",
        result_count=16,
        performance_metrics={"execution_time_seconds": 3.0},
    )
    report = create_report_manifest(
        workspace_id=workspace.workspace_id,
        run_id=run.run_id,
        title="Results",
        analysis_execution_ids=[second.analysis_execution_id],
    )
    repository.create_report_manifest(report)

    comparison = service.compare_analysis_executions(
        workspace.workspace_id,
        [first.analysis_execution_id, second.analysis_execution_id],
    )
    lineage = service.get_analysis_lineage(second.analysis_execution_id)

    assert comparison["deltas"][1]["result_count"] == 6
    assert (
        comparison["deltas"][1]["performance_metrics"]["execution_time_seconds"] == -2.0
    )
    assert lineage["reports"][0]["report_id"] == report.report_id
    assert lineage["template_id"] == "template-2"
    assert lineage["use_case_id"] == "use-case-1"
    assert lineage["requirement_version_id"] == "requirement-1"


def test_record_workflow_analysis_executions_is_idempotent_by_job_id():
    """A supervisor retry does not duplicate catalog rows for one GAE job."""

    from datetime import datetime, timezone
    from types import SimpleNamespace

    repository, service, _workspace, run = _catalog_service_fixture()
    job = SimpleNamespace(
        job_id="gae-job-1",
        template_name="PageRank",
        algorithm="pagerank",
        result_collection="pagerank_results",
        result_count=2,
        execution_time_seconds=1.25,
        submitted_at=datetime.now(timezone.utc),
        started_at=None,
        completed_at=datetime.now(timezone.utc),
        error_message=None,
        metadata={},
    )
    result = SimpleNamespace(
        job=job,
        success=True,
        results=[{"vertex": "a"}, {"vertex": "b"}],
        error=None,
        warnings=[],
        metrics={},
    )
    template = SimpleNamespace(
        name="PageRank",
        use_case_id="use-case-1",
        algorithm=SimpleNamespace(parameters={"damping": 0.85}),
        config=SimpleNamespace(to_dict=lambda: {"graph_name": "graph"}),
    )
    state = SimpleNamespace(execution_results=[result], templates=[template])

    first = service.record_workflow_analysis_executions(run.run_id, state)
    second = service.record_workflow_analysis_executions(run.run_id, state)

    assert len(first) == 1
    assert second == []
    assert len(repository.analysis_executions) == 1
    assert first[0].metadata["gae_job_id"] == "gae-job-1"


# ---------------------------------------------------------------------------
# Use cases and analysis templates (FR-19..FR-26)
# ---------------------------------------------------------------------------


def _workspace_for_use_cases(repository):
    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )
    repository.workspaces[workspace.workspace_id] = workspace
    return workspace


def test_create_use_case_starts_as_draft_and_audits():
    """PRD FR-19: users can author a use case by hand."""

    repository = FakeProductRepository()
    workspace = _workspace_for_use_cases(repository)

    use_case = ProductService(repository).create_use_case(
        workspace_id=workspace.workspace_id,
        title="Find fraud rings",
        use_case_type="community",
        priority="high",
        actor="analyst@example.com",
    )

    assert use_case.status is UseCaseStatus.DRAFT
    # Approval is a separate, audited decision — creating never approves.
    assert use_case.origin is UseCaseOrigin.MANUAL
    assert use_case.priority == "high"
    assert repository.use_cases[0].use_case_id == use_case.use_case_id
    assert any(event.action == "create_use_case" for event in repository.audit_events)


def test_use_case_review_lifecycle_and_terminal_archive():
    """PRD FR-20: approve/reject/archive are audited; archive is terminal."""

    repository = FakeProductRepository()
    workspace = _workspace_for_use_cases(repository)
    service = ProductService(repository)
    use_case = service.create_use_case(
        workspace_id=workspace.workspace_id, title="Rank accounts"
    )

    rejected = service.set_use_case_status(
        use_case.use_case_id, "rejected", review_note="Out of scope", actor="lead"
    )
    assert rejected.status is UseCaseStatus.REJECTED
    assert rejected.review_note == "Out of scope"
    # A rejected use case can be revised and re-submitted.
    service.update_use_case(use_case.use_case_id, title="Rank accounts by risk")
    approved = service.set_use_case_status(use_case.use_case_id, "approved")
    assert approved.status is UseCaseStatus.APPROVED

    service.set_use_case_status(use_case.use_case_id, "archived")
    with pytest.raises(ConflictError):
        service.set_use_case_status(use_case.use_case_id, "approved")


def test_approved_use_case_cannot_be_edited_but_can_be_reprioritized():
    """An approved use case feeds template generation, so content is frozen.

    Priority is not content — a reviewer must be able to re-rank an approved
    backlog without reopening it for edits (FR-20).
    """

    repository = FakeProductRepository()
    workspace = _workspace_for_use_cases(repository)
    service = ProductService(repository)
    use_case = service.create_use_case(
        workspace_id=workspace.workspace_id, title="Detect anomalies"
    )
    service.set_use_case_status(use_case.use_case_id, "approved")

    with pytest.raises(ConflictError):
        service.update_use_case(use_case.use_case_id, title="Something else")

    reprioritized = service.set_use_case_priority(use_case.use_case_id, "critical")
    assert reprioritized.priority == "critical"


def test_create_use_case_rejects_unknown_type_and_priority():
    repository = FakeProductRepository()
    workspace = _workspace_for_use_cases(repository)
    service = ProductService(repository)

    with pytest.raises(ValidationError):
        service.create_use_case(
            workspace_id=workspace.workspace_id, title="X", use_case_type="telepathy"
        )
    with pytest.raises(ValidationError):
        service.create_use_case(
            workspace_id=workspace.workspace_id, title="X", priority="urgent-ish"
        )


def test_editing_a_draft_template_mutates_it_in_place():
    """PRD FR-23: algorithm parameters are editable before approval."""

    repository = FakeProductRepository()
    workspace = _workspace_for_use_cases(repository)
    service = ProductService(repository)
    template = service.create_analysis_template(
        workspace_id=workspace.workspace_id,
        name="PageRank",
        algorithm="pagerank",
        parameters={"damping_factor": 0.85},
    )

    edited = service.update_analysis_template(
        template.analysis_template_id, parameters={"damping_factor": 0.9}
    )

    assert edited.analysis_template_id == template.analysis_template_id
    assert edited.version == 1
    assert edited.parameters == {"damping_factor": 0.9}
    assert len(repository.analysis_templates) == 1


def test_editing_an_approved_template_creates_a_new_version():
    """PRD FR-25: approved templates are immutable and versioned.

    A completed run must still resolve the exact row it executed, so editing
    supersedes rather than mutates.
    """

    repository = FakeProductRepository()
    workspace = _workspace_for_use_cases(repository)
    service = ProductService(repository)
    v1 = service.create_analysis_template(
        workspace_id=workspace.workspace_id,
        name="PageRank",
        algorithm="pagerank",
        parameters={"damping_factor": 0.85},
    )
    service.approve_analysis_template(v1.analysis_template_id, actor="approver")

    v2 = service.update_analysis_template(
        v1.analysis_template_id, parameters={"damping_factor": 0.5}, actor="analyst"
    )

    assert v2.analysis_template_id != v1.analysis_template_id
    assert v2.version == 2
    assert v2.status is AnalysisTemplateStatus.DRAFT
    # Same lineage: "this template" is stable across versions.
    assert v2.lineage_id == v1.lineage_id

    stored_v1 = service.get_analysis_template(v1.analysis_template_id)
    assert stored_v1.status is AnalysisTemplateStatus.SUPERSEDED
    assert stored_v1.superseded_by == v2.analysis_template_id
    # The executed configuration is untouched.
    assert stored_v1.parameters == {"damping_factor": 0.85}

    versions = service.get_analysis_template_versions(v2.analysis_template_id)
    assert [item.version for item in versions] == [1, 2]
    # Superseded rows are hidden from the default listing.
    listed = service.list_analysis_templates(workspace.workspace_id)
    assert [item.analysis_template_id for item in listed] == [v2.analysis_template_id]


def test_only_draft_templates_can_be_approved():
    repository = FakeProductRepository()
    workspace = _workspace_for_use_cases(repository)
    service = ProductService(repository)
    template = service.create_analysis_template(
        workspace_id=workspace.workspace_id, name="WCC", algorithm="wcc"
    )
    service.approve_analysis_template(template.analysis_template_id)

    with pytest.raises(ConflictError):
        service.approve_analysis_template(template.analysis_template_id)


def test_import_template_dictionary_ignores_unknown_keys_and_executes_nothing():
    """PRD FR-26: import supported template dictionaries without executing code.

    Only the whitelisted fields are read. A payload naming a Python type or
    shell command is inert data — it is recorded as ignored, never resolved,
    imported, or run.
    """

    repository = FakeProductRepository()
    workspace = _workspace_for_use_cases(repository)

    imported = ProductService(repository).import_analysis_templates(
        workspace_id=workspace.workspace_id,
        templates=[
            {
                "name": "WCC",
                "algorithm": "wcc",
                "parameters": {"max_iterations": 20},
                "__class__": "os.system",
                "cmd": "rm -rf /",
                "eval": "__import__('os').system('id')",
            }
        ],
        actor="analyst@example.com",
    )

    assert len(imported) == 1
    template = imported[0]
    assert template.name == "WCC"
    assert template.algorithm == "wcc"
    assert template.parameters == {"max_iterations": 20}
    # Importing is not approving — everything lands as a draft for review.
    assert template.status is AnalysisTemplateStatus.DRAFT
    assert template.metadata["ignored_keys"] == ["__class__", "cmd", "eval"]
    # The hostile keys never became attributes of the persisted record.
    assert "cmd" not in template.to_dict()
    assert "__class__" not in template.to_dict()


def test_import_template_dictionary_rejects_malformed_entries():
    repository = FakeProductRepository()
    workspace = _workspace_for_use_cases(repository)
    service = ProductService(repository)

    with pytest.raises(ValidationError):
        service.import_analysis_templates(
            workspace_id=workspace.workspace_id, templates=[{"algorithm": "wcc"}]
        )
    with pytest.raises(ValidationError):
        service.import_analysis_templates(
            workspace_id=workspace.workspace_id,
            templates=[
                {"name": "X", "algorithm": "wcc", "parameters": "not-an-object"}
            ],
        )


def test_browse_catalog_returns_real_templates_and_use_cases():
    """PRD FR-45: templates and use cases are browsable records, not bare IDs."""

    repository = FakeProductRepository()
    workspace = _workspace_for_use_cases(repository)
    service = ProductService(repository)
    use_case = service.create_use_case(
        workspace_id=workspace.workspace_id, title="Find fraud rings"
    )
    service.create_analysis_template(
        workspace_id=workspace.workspace_id,
        name="PageRank",
        algorithm="pagerank",
        use_case_id=use_case.use_case_id,
    )

    catalog = service.browse_analysis_catalog(workspace.workspace_id)

    assert [item["title"] for item in catalog["use_cases"]] == ["Find fraud rings"]
    assert [item["name"] for item in catalog["templates"]] == ["PageRank"]
    assert catalog["unresolved_template_ids"] == []
    assert catalog["unresolved_use_case_ids"] == []


def test_workflow_dag_view_derives_step_artifact_refs():
    """FR-37: step nodes link to the artifacts that step produced.

    Nothing in the product code ever wrote ``WorkflowStep.artifact_refs`` —
    only tests did — so every step of every real run reported "Artifacts: 0".
    The DAG view now derives the refs from the run's own record.
    """

    repository = FakeProductRepository()
    run = create_workflow_run(
        workspace_id="workspace-1",
        workflow_mode=WorkflowMode.AGENTIC,
        status=WorkflowRunStatus.COMPLETED,
        graph_profile_id="graph-profile-1",
        steps=[
            WorkflowStep(step_id="schema_analysis", label="Schema Analysis"),
            WorkflowStep(step_id="reporting", label="Reporting"),
        ],
        dag_edges=[
            WorkflowDAGEdge(from_step_id="schema_analysis", to_step_id="reporting")
        ],
    )
    repository.workflow_runs[run.run_id] = run

    # Reports carry `run_id` themselves; the run's own `report_ids` is empty,
    # which is exactly the shape the seeded AdTech workspace has.
    for index in range(3):
        manifest = create_report_manifest(
            workspace_id="workspace-1",
            run_id=run.run_id,
            title=f"Report {index}",
        )
        repository.reports[manifest.report_id] = manifest
    unrelated = create_report_manifest(
        workspace_id="workspace-1",
        run_id="run-somewhere-else",
        title="Not this run",
    )
    repository.reports[unrelated.report_id] = unrelated

    view = ProductService(repository).get_workflow_dag_view(run.run_id)
    nodes = {node["id"]: node for node in view.nodes}

    assert nodes["schema_analysis"]["artifact_refs"] == [
        {"type": "graph_profile", "id": "graph-profile-1"}
    ]
    assert nodes["schema_analysis"]["artifact_count"] == 1

    reporting_refs = nodes["reporting"]["artifact_refs"]
    assert len(reporting_refs) == 3
    assert {ref["type"] for ref in reporting_refs} == {"report"}
    assert unrelated.report_id not in {ref["id"] for ref in reporting_refs}
    # Titles beat bare UUIDs in the step detail panel.
    assert {ref["label"] for ref in reporting_refs} == {
        "Report 0",
        "Report 1",
        "Report 2",
    }
    assert nodes["reporting"]["artifact_count"] == 3


def test_workflow_dag_view_prefers_stored_artifact_refs():
    """Derivation is a fallback: real per-step provenance is never overwritten."""

    repository = FakeProductRepository()
    stored = [{"type": "analysis_execution", "id": "execution-explicit"}]
    run = create_workflow_run(
        workspace_id="workspace-1",
        workflow_mode=WorkflowMode.AGENTIC,
        status=WorkflowRunStatus.COMPLETED,
        graph_profile_id="graph-profile-1",
        steps=[
            WorkflowStep(
                step_id="schema_analysis",
                label="Schema Analysis",
                artifact_refs=stored,
            )
        ],
        dag_edges=[],
    )
    repository.workflow_runs[run.run_id] = run

    view = ProductService(repository).get_workflow_dag_view(run.run_id)

    assert view.nodes[0]["artifact_refs"] == stored


def _document_with_extraction(repository, workspace, payload):
    document = create_source_document(
        workspace_id=workspace.workspace_id,
        filename="brd.md",
        mime_type="text/markdown",
        sha256="abc123",
        storage_mode=DocumentStorageMode.EXTRACT_ONLY,
        extracted_text="# Requirements",
        metadata={"extracted_requirements_draft": payload},
    )
    repository.create_source_document(document)
    return document


_EXTRACTION_PAYLOAD = {
    "summary": "Build an identity graph.",
    "objectives": [
        {
            "id": "OBJ-1",
            "text": "Achieve data autonomy",
            "source": "document_extraction",
        }
    ],
    "requirements": [
        {
            "id": "REQ-1",
            "text": "Stitch devices to IPs",
            "source": "document_extraction",
        }
    ],
    "constraints": [
        {"id": "CON-1", "text": "Must run on GAE", "source": "document_extraction"}
    ],
}


def test_promote_extracted_requirements_creates_approvable_draft():
    """FR-15: extracted requirements reach an approvable RequirementVersion.

    Extraction ran on upload and was persisted, but nothing could consume it —
    there was no path from an uploaded document to a requirement version, so
    the extracted content was effectively write-only.
    """

    repository = FakeProductRepository()
    workspace = _workspace_for_upload(repository)
    document = _document_with_extraction(repository, workspace, _EXTRACTION_PAYLOAD)
    service = ProductService(repository)

    version = service.promote_extracted_requirements(
        document.document_id, actor="arthur"
    )

    # DRAFT, not APPROVED: machine extraction is a proposal, so the
    # workspace's single active version must not change without a human.
    assert version.status is RequirementVersionStatus.DRAFT
    assert version.version == 1
    assert version.document_ids == [document.document_id]
    assert version.summary == "Build an identity graph."
    # The content survives — the lossy to_summary_dict() shape could not have
    # produced this, which is what blocked promotion before.
    assert [item["text"] for item in version.requirements] == ["Stitch devices to IPs"]
    assert [item["text"] for item in version.objectives] == ["Achieve data autonomy"]
    assert [item["text"] for item in version.constraints] == ["Must run on GAE"]
    assert version.metadata["source"] == "document_extraction"
    assert version.metadata["source_document_id"] == document.document_id


def test_promote_extracted_requirements_without_extraction_is_actionable():
    """No LLM at upload time means nothing to promote — say so clearly."""

    repository = FakeProductRepository()
    workspace = _workspace_for_upload(repository)
    document = create_source_document(
        workspace_id=workspace.workspace_id,
        filename="brd.md",
        mime_type="text/markdown",
        sha256="abc123",
        storage_mode=DocumentStorageMode.EXTRACT_ONLY,
        extracted_text="# Requirements",
    )
    repository.create_source_document(document)

    with pytest.raises(ValidationError, match="no extracted requirements"):
        ProductService(repository).promote_extracted_requirements(document.document_id)


def test_approve_requirement_version_supersedes_the_prior_active_set():
    """A promoted draft can be activated, keeping exactly one APPROVED version.

    The Copilot's approve path works from an interview, so a version promoted
    from document extraction had no way to be activated at all.
    """

    repository = FakeProductRepository()
    workspace = _workspace_for_upload(repository)
    prior = create_requirement_version(
        workspace_id=workspace.workspace_id,
        version=1,
        status=RequirementVersionStatus.APPROVED,
        summary="Earlier approved set",
    )
    repository.create_requirement_version(prior)
    document = _document_with_extraction(repository, workspace, _EXTRACTION_PAYLOAD)
    service = ProductService(repository)

    draft = service.promote_extracted_requirements(document.document_id)
    assert draft.version == 2

    approved = service.approve_requirement_version(
        draft.requirement_version_id, approved_by="arthur"
    )

    assert approved.status is RequirementVersionStatus.APPROVED
    assert approved.approved_at is not None
    assert approved.metadata["approved_by"] == "arthur"

    refreshed_prior = repository.get_requirement_version(prior.requirement_version_id)
    assert refreshed_prior.status is RequirementVersionStatus.SUPERSEDED
    assert refreshed_prior.metadata["superseded_by"] == draft.requirement_version_id

    active = [
        version
        for version in repository.list_requirement_versions(workspace.workspace_id)
        if version.status is RequirementVersionStatus.APPROVED
    ]
    assert len(active) == 1


def test_approve_requirement_version_rejects_non_draft():
    """Superseded/archived versions must not be silently reactivated."""

    repository = FakeProductRepository()
    workspace = _workspace_for_upload(repository)
    superseded = create_requirement_version(
        workspace_id=workspace.workspace_id,
        version=1,
        status=RequirementVersionStatus.SUPERSEDED,
        summary="Old",
    )
    repository.create_requirement_version(superseded)

    with pytest.raises(ValidationError, match="Only DRAFT"):
        ProductService(repository).approve_requirement_version(
            superseded.requirement_version_id
        )
