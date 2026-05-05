"""Unit tests for product UI application services."""

from graph_analytics_ai.product import (
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
from graph_analytics_ai.product.exceptions import ValidationError
from graph_analytics_ai.product.models import DeploymentMode, DocumentStorageMode
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
        self.requirement_interviews = []
        self.requirement_versions = []
        self.workflow_runs = {}
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
            profile for profile in self.graph_profiles if profile.workspace_id == workspace_id
        ]

    def create_graph_profile(self, profile):
        self.graph_profiles.append(profile)
        return profile.graph_profile_id

    def get_graph_profile(self, graph_profile_id):
        for profile in self.graph_profiles:
            if profile.graph_profile_id == graph_profile_id:
                return profile
        raise KeyError(graph_profile_id)

    def list_source_documents(self, workspace_id):
        return [
            document
            for document in self.source_documents
            if document.workspace_id == workspace_id
        ]

    def create_source_document(self, document):
        self.source_documents.append(document)
        return document.document_id

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
        for index, existing in enumerate(self.requirement_versions):
            if existing.requirement_version_id == version.requirement_version_id:
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
            run for run in self.workflow_runs.values() if run.workspace_id == workspace_id
        ]

    def create_workflow_run(self, run):
        self.workflow_runs[run.run_id] = run
        return run.run_id

    def get_workflow_run(self, run_id):
        return self.workflow_runs[run_id]

    def update_workflow_run(self, run):
        self.workflow_runs[run.run_id] = run
        return run.run_id

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
            report for report in self.reports.values() if report.workspace_id == workspace_id
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
    """FR-17c: every RequirementVersion must appear in the overview.

    The consolidated Requirements asset and its canvas-side version dropdown
    are projected from ``overview.latest_requirement_versions``. If that list
    is truncated by ``recent_limit``, older versions silently disappear from
    the dropdown even though the spec requires that "all historical versions
    remain queryable and individually addressable". Other ``latest_*`` fields
    (reports, workflow runs, etc.) must remain capped because they grow
    unbounded and the cap is a UI affordance, not a correctness requirement.
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

    run = create_workflow_run(
        workspace_id=workspace.workspace_id,
        workflow_mode=WorkflowMode.AGENTIC,
    )
    repository.workflow_runs[run.run_id] = run
    cap = 5
    extra_reports = cap + 3
    for index in range(extra_reports):
        report = create_report_manifest(
            workspace_id=workspace.workspace_id,
            run_id=run.run_id,
            title=f"Report {index}",
        )
        repository.reports[report.report_id] = report

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

    assert len(overview.latest_reports) == cap
    assert overview.counts["reports"] == extra_reports


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
    assert updated_report.published_snapshot_id == repository.snapshots[0].published_snapshot_id
    assert repository.snapshots[0].content_hash.startswith("sha256:")
    assert repository.audit_events[0].action == "publish_report"
    assert bundle.manifest["status"] == "published"
    assert bundle.snapshots[0]["published_by"] == "analyst@example.com"


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
    assert "secret_refs" not in doc["connection_profiles"][0]
    assert doc["connection_profiles"][0]["secret_ref_keys"] == ["password"]
    assert doc["audit_events"][0]["action"] == "export_workspace"


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
    bundle = ProductService(source_repository).export_workspace_bundle(
        workspace.workspace_id
    )

    target_repository = FakeProductRepository()
    result = ProductService(target_repository).import_workspace_bundle(bundle)

    assert result.workspace_id == workspace.workspace_id
    assert result.counts["connection_profiles"] == 1
    assert result.counts["workflow_runs"] == 1
    assert result.counts["reports"] == 1
    assert result.counts["report_sections"] == 1
    assert result.counts["chart_specs"] == 1
    assert result.counts["audit_events"] == 0
    assert target_repository.workspaces[workspace.workspace_id].project_name == (
        "Graph Analytics"
    )
    assert target_repository.connection_profiles[0].secret_refs == {}
    assert target_repository.reports[report.report_id].title == "Graph Report"
    assert target_repository.audit_events == []


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
    assert updated_profile.last_verification_status == ConnectionVerificationStatus.SUCCESS
    assert updated_profile.last_verified_at is not None
    assert connector_calls[0]["password"] == "resolved-secret"
    assert connector_calls[0]["verify_system"] is True
    assert updated_profile.secret_refs["password"]["ref"] == "ARANGO_PASSWORD"


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
    assert updated_profile.last_verification_status == ConnectionVerificationStatus.FAILED


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
                {"Device": 10, "IP": 5, "SEEN_ON_IP": 20, "RagDoc": 99, "RagEmbeds": 300}[
                    name
                ]
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
            secret_resolver=MappingSecretResolver({"ARANGO_PASSWORD": "resolved-secret"}),
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
    assert any(label["label"] == "observed_from_schema" for label in draft.provenance_labels)
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
    service.generate_requirements_copilot_draft(
        interview_two.requirement_interview_id
    )

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
    """Workflow helpers support visualizer polling and recovery action display."""

    repository = FakeProductRepository()
    service = ProductService(repository)
    run = service.create_workflow_run_from_steps(
        workspace_id="workspace-1",
        workflow_mode=WorkflowMode.AGENTIC,
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
    """Workflow creation validates DAG edge references."""

    repository = FakeProductRepository()
    try:
        ProductService(repository).create_workflow_run_from_steps(
            workspace_id="workspace-1",
            workflow_mode=WorkflowMode.AGENTIC,
            steps=[WorkflowStep(step_id="schema", label="Schema Analysis")],
            dag_edges=[WorkflowDAGEdge(from_step_id="schema", to_step_id="missing")],
        )
    except ValidationError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for invalid DAG edge")
