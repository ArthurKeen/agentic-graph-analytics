"""Integration tests for product ArangoDB storage."""

import os

import pytest
from arango import ArangoClient

from graph_analytics_ai.product import (
    ChartType,
    ConnectionVerificationStatus,
    DeploymentMode,
    DocumentStorageMode,
    ProductArangoStorage,
    ProductRepository,
    RequirementInterviewStatus,
    RequirementVersionStatus,
    ReportSectionType,
    ReportStatus,
    WorkspaceStatus,
    WorkflowDAGEdge,
    WorkflowMode,
    WorkflowRunStatus,
    WorkflowStep,
    WorkflowStepStatus,
    create_audit_event,
    create_chart_spec,
    create_connection_profile,
    create_graph_profile,
    create_published_snapshot,
    create_report_manifest,
    create_report_section,
    create_requirement_interview,
    create_requirement_version,
    create_source_document,
    create_workflow_run,
    create_workspace,
)
from graph_analytics_ai.product.constants import (
    AUDIT_EVENTS_COLLECTION,
    CHART_SPECS_COLLECTION,
    CONNECTION_PROFILES_COLLECTION,
    DOCUMENTS_COLLECTION,
    GRAPH_PROFILES_COLLECTION,
    PRODUCT_COLLECTIONS,
    PUBLISHED_SNAPSHOTS_COLLECTION,
    REPORT_MANIFESTS_COLLECTION,
    REPORT_SECTIONS_COLLECTION,
    REQUIREMENT_INTERVIEWS_COLLECTION,
    REQUIREMENT_VERSIONS_COLLECTION,
    WORKFLOW_RUNS_COLLECTION,
    WORKSPACES_COLLECTION,
)


pytestmark = pytest.mark.skipif(
    not os.getenv("ARANGO_TEST_URL"), reason="ArangoDB test instance not configured"
)


@pytest.fixture(scope="module")
def arango_db():
    """Create test database connection."""

    url = os.getenv("ARANGO_TEST_URL", "http://localhost:8529")
    username = os.getenv("ARANGO_TEST_USERNAME", "root")
    password = os.getenv("ARANGO_TEST_PASSWORD", "test")
    db_name = os.getenv("ARANGO_TEST_DB", "_system")

    client = ArangoClient(hosts=url)
    db = client.db(db_name, username=username, password=password)

    yield db


@pytest.fixture
def storage(arango_db):
    """Create product storage and clear product collections."""

    storage = ProductArangoStorage(arango_db, auto_initialize=True)
    storage.reset(confirm=True)
    storage.initialize_collections()

    yield storage

    storage.reset(confirm=True)
    storage.close()


def test_initialize_product_collections(arango_db):
    """Product storage creates all product collections idempotently."""

    storage = ProductArangoStorage(arango_db, auto_initialize=False)
    storage.initialize_collections()
    storage.initialize_collections()

    for collection_name in PRODUCT_COLLECTIONS:
        assert arango_db.has_collection(collection_name)


def test_workspace_and_connection_profile_crud(storage):
    """Repository supports workspace and connection profile CRUD."""

    repository = ProductRepository(storage)
    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )

    workspace_id = repository.create_workspace(workspace)
    restored_workspace = repository.get_workspace(workspace_id)

    assert restored_workspace.workspace_id == workspace_id
    assert restored_workspace.status == WorkspaceStatus.ACTIVE

    profile = create_connection_profile(
        workspace_id=workspace_id,
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
        secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
        last_verification_status=ConnectionVerificationStatus.UNKNOWN,
    )

    profile_id = repository.create_connection_profile(profile)
    restored_profile = repository.get_connection_profile(profile_id)
    profiles = repository.list_connection_profiles(workspace_id)

    assert restored_profile.connection_profile_id == profile_id
    assert restored_profile.secret_refs["password"]["ref"] == "ARANGO_PASSWORD"
    assert [p.connection_profile_id for p in profiles] == [profile_id]


def test_reset_only_truncates_product_collections(storage, arango_db):
    """Reset clears product collections without touching catalog collection names."""

    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )
    storage.insert_workspace(workspace)
    assert arango_db.collection(WORKSPACES_COLLECTION).count() == 1

    profile = create_connection_profile(
        workspace_id=workspace.workspace_id,
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
    )
    storage.insert_connection_profile(profile)
    assert arango_db.collection(CONNECTION_PROFILES_COLLECTION).count() == 1

    storage.reset(confirm=True)

    assert arango_db.collection(WORKSPACES_COLLECTION).count() == 0
    assert arango_db.collection(CONNECTION_PROFILES_COLLECTION).count() == 0


def test_graph_document_interview_and_requirement_version_crud(storage, arango_db):
    """Repository supports next-slice product objects."""

    repository = ProductRepository(storage)
    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )
    repository.create_workspace(workspace)
    profile = create_connection_profile(
        workspace_id=workspace.workspace_id,
        name="Development",
        deployment_mode=DeploymentMode.LOCAL,
        endpoint="http://localhost:8529",
        database="customer_graph",
        username="root",
    )
    repository.create_connection_profile(profile)

    graph_profile = create_graph_profile(
        workspace_id=workspace.workspace_id,
        connection_profile_id=profile.connection_profile_id,
        graph_name="customer_graph",
        vertex_collections=["Device", "IP"],
        edge_collections=["connects_to"],
    )
    graph_profile_id = repository.create_graph_profile(graph_profile)
    restored_graph_profile = repository.get_graph_profile(graph_profile_id)
    assert restored_graph_profile.graph_name == "customer_graph"
    assert arango_db.collection(GRAPH_PROFILES_COLLECTION).count() == 1

    document = create_source_document(
        workspace_id=workspace.workspace_id,
        filename="requirements.md",
        mime_type="text/markdown",
        sha256="abc123",
        storage_mode=DocumentStorageMode.INLINE,
        extracted_text="Find influential entities.",
    )
    document_id = repository.create_source_document(document)
    restored_document = repository.get_source_document(document_id)
    assert restored_document.sha256 == "abc123"
    assert arango_db.collection(DOCUMENTS_COLLECTION).count() == 1

    interview = create_requirement_interview(
        workspace_id=workspace.workspace_id,
        graph_profile_id=graph_profile_id,
        status=RequirementInterviewStatus.READY_FOR_REVIEW,
        draft_brd="# Draft",
    )
    interview_id = repository.create_requirement_interview(interview)
    restored_interview = repository.get_requirement_interview(interview_id)
    assert restored_interview.draft_brd == "# Draft"
    assert arango_db.collection(REQUIREMENT_INTERVIEWS_COLLECTION).count() == 1

    version = create_requirement_version(
        workspace_id=workspace.workspace_id,
        version=1,
        status=RequirementVersionStatus.APPROVED,
        document_ids=[document_id],
        requirement_interview_id=interview_id,
        summary="Analyze influence.",
    )
    version_id = repository.create_requirement_version(version)
    restored_version = repository.get_requirement_version(version_id)
    assert restored_version.status == RequirementVersionStatus.APPROVED
    assert restored_version.requirement_interview_id == interview_id
    assert arango_db.collection(REQUIREMENT_VERSIONS_COLLECTION).count() == 1

    assert len(repository.list_graph_profiles(workspace.workspace_id)) == 1
    assert len(repository.list_source_documents(workspace.workspace_id)) == 1
    assert len(repository.list_requirement_interviews(workspace.workspace_id)) == 1
    assert len(repository.list_requirement_versions(workspace.workspace_id)) == 1


def test_workflow_run_crud(storage, arango_db):
    """Repository supports workflow run persistence for visualizer polling."""

    repository = ProductRepository(storage)
    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )
    repository.create_workspace(workspace)

    run = create_workflow_run(
        workspace_id=workspace.workspace_id,
        workflow_mode=WorkflowMode.AGENTIC,
        status=WorkflowRunStatus.QUEUED,
        steps=[
            WorkflowStep(
                step_id="schema_analysis",
                label="Schema Analysis",
                status=WorkflowStepStatus.PENDING,
            ),
            WorkflowStep(
                step_id="reporting",
                label="Report Generation",
                status=WorkflowStepStatus.PENDING,
            ),
        ],
        dag_edges=[
            WorkflowDAGEdge(
                from_step_id="schema_analysis",
                to_step_id="reporting",
                label="produces inputs",
            )
        ],
    )

    run_id = repository.create_workflow_run(run)
    restored = repository.get_workflow_run(run_id)
    assert restored.workflow_mode == WorkflowMode.AGENTIC
    assert restored.steps[0].step_id == "schema_analysis"
    assert restored.dag_edges[0].to_step_id == "reporting"
    assert arango_db.collection(WORKFLOW_RUNS_COLLECTION).count() == 1

    restored.status = WorkflowRunStatus.RUNNING
    restored.steps[0].status = WorkflowStepStatus.COMPLETED
    repository.update_workflow_run(restored)

    updated = repository.get_workflow_run(run_id)
    assert updated.status == WorkflowRunStatus.RUNNING
    assert updated.steps[0].status == WorkflowStepStatus.COMPLETED
    assert [r.run_id for r in repository.list_workflow_runs(workspace.workspace_id)] == [
        run_id
    ]


def test_report_and_audit_crud(storage, arango_db):
    """Repository supports report rendering metadata and audit events."""

    repository = ProductRepository(storage)
    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
    )
    repository.create_workspace(workspace)
    run = create_workflow_run(
        workspace_id=workspace.workspace_id,
        workflow_mode=WorkflowMode.AGENTIC,
        status=WorkflowRunStatus.COMPLETED,
    )
    run_id = repository.create_workflow_run(run)

    manifest = create_report_manifest(
        workspace_id=workspace.workspace_id,
        run_id=run_id,
        title="Audience Graph Analysis",
        status=ReportStatus.READY,
        summary="Dynamic report summary.",
    )
    report_id = repository.create_report_manifest(manifest)
    restored_manifest = repository.get_report_manifest(report_id)
    assert restored_manifest.status == ReportStatus.READY
    assert arango_db.collection(REPORT_MANIFESTS_COLLECTION).count() == 1

    section = create_report_section(
        workspace_id=workspace.workspace_id,
        report_id=report_id,
        order=1,
        type=ReportSectionType.SUMMARY,
        title="Summary",
        content={"markdown": "Report body."},
    )
    section_id = repository.create_report_section(section)
    restored_section = repository.get_report_section(section_id)
    assert restored_section.content["markdown"] == "Report body."
    assert arango_db.collection(REPORT_SECTIONS_COLLECTION).count() == 1

    chart = create_chart_spec(
        workspace_id=workspace.workspace_id,
        report_id=report_id,
        title="Top Scores",
        chart_type=ChartType.BAR,
        data_source={"collection": "analysis_results"},
        encoding={"x": "name", "y": "score"},
    )
    chart_id = repository.create_chart_spec(chart)
    restored_chart = repository.get_chart_spec(chart_id)
    assert restored_chart.chart_type == ChartType.BAR
    assert arango_db.collection(CHART_SPECS_COLLECTION).count() == 1

    snapshot = create_published_snapshot(
        workspace_id=workspace.workspace_id,
        report_id=report_id,
        title="Audience Graph Analysis",
        published_by="analyst@example.com",
        content_hash="sha256:abc123",
        rendered_snapshot={"report_id": report_id},
    )
    snapshot_id = repository.create_published_snapshot(snapshot)
    restored_snapshot = repository.get_published_snapshot(snapshot_id)
    assert restored_snapshot.content_hash == "sha256:abc123"
    assert arango_db.collection(PUBLISHED_SNAPSHOTS_COLLECTION).count() == 1

    event = create_audit_event(
        workspace_id=workspace.workspace_id,
        actor="analyst@example.com",
        action="publish_report",
        target_type="report",
        target_id=report_id,
    )
    repository.create_audit_event(event)
    assert arango_db.collection(AUDIT_EVENTS_COLLECTION).count() == 1

    manifest.section_ids = [section_id]
    manifest.chart_ids = [chart_id]
    manifest.published_snapshot_id = snapshot_id
    manifest.status = ReportStatus.PUBLISHED
    repository.update_report_manifest(manifest)

    updated_manifest = repository.get_report_manifest(report_id)
    assert updated_manifest.status == ReportStatus.PUBLISHED
    assert updated_manifest.published_snapshot_id == snapshot_id
    assert [r.report_id for r in repository.list_report_manifests(workspace.workspace_id)] == [
        report_id
    ]
    assert [s.section_id for s in repository.list_report_sections(report_id)] == [
        section_id
    ]
    assert [c.chart_id for c in repository.list_chart_specs(report_id)] == [chart_id]
    assert [
        s.published_snapshot_id for s in repository.list_published_snapshots(report_id)
    ] == [snapshot_id]
    assert [e.audit_event_id for e in repository.list_audit_events(workspace.workspace_id)] == [
        event.audit_event_id
    ]

