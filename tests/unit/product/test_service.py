"""Unit tests for product UI application services."""

from graph_analytics_ai.product import (
    ChartType,
    ProductService,
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

    def list_graph_profiles(self, workspace_id):
        return [
            profile for profile in self.graph_profiles if profile.workspace_id == workspace_id
        ]

    def create_graph_profile(self, profile):
        self.graph_profiles.append(profile)
        return profile.graph_profile_id

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

    def list_requirement_interviews(self, workspace_id):
        return [
            interview
            for interview in self.requirement_interviews
            if interview.workspace_id == workspace_id
        ]

    def create_requirement_interview(self, interview):
        self.requirement_interviews.append(interview)
        return interview.requirement_interview_id

    def list_workflow_runs(self, workspace_id):
        return [
            run for run in self.workflow_runs.values() if run.workspace_id == workspace_id
        ]

    def create_workflow_run(self, run):
        self.workflow_runs[run.run_id] = run
        return run.run_id

    def get_workflow_run(self, run_id):
        return self.workflow_runs[run_id]

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
    assert overview.latest_workflow_runs[0]["run_id"] == run.run_id
    assert overview.latest_reports[0]["report_id"] == report.report_id
    assert overview.latest_audit_events[0]["action"] == "create_report"


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
