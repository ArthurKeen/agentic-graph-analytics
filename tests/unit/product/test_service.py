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
