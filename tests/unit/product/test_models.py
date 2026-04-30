"""Unit tests for product metadata models."""

from graph_analytics_ai.product import (
    ChartType,
    ConnectionProfile,
    ConnectionVerificationStatus,
    DeploymentMode,
    DocumentStorageMode,
    GraphProfile,
    RequirementInterview,
    RequirementInterviewStatus,
    RequirementVersion,
    RequirementVersionStatus,
    ReportSectionType,
    ReportStatus,
    SourceDocument,
    Workspace,
    WorkspaceStatus,
    WorkflowDAGEdge,
    WorkflowMode,
    WorkflowRun,
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
from graph_analytics_ai.product.exceptions import ValidationError


def test_workspace_round_trip():
    """Workspace documents round-trip through dict serialization."""

    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
        description="Test workspace",
        tags=["demo"],
        metadata={"vertical": "AdTech"},
    )

    doc = workspace.to_dict()
    restored = Workspace.from_dict(doc)

    assert doc["_key"] == workspace.workspace_id
    assert restored.workspace_id == workspace.workspace_id
    assert restored.status == WorkspaceStatus.ACTIVE
    assert restored.tags == ["demo"]
    assert restored.metadata["vertical"] == "AdTech"


def test_connection_profile_round_trip_allows_secret_references():
    """Connection profiles store secret references, not resolved secret values."""

    profile = create_connection_profile(
        workspace_id="workspace-1",
        name="Production",
        deployment_mode=DeploymentMode.AMP,
        endpoint="https://example.com:8529",
        database="customer_graph",
        username="svc-aga",
        secret_refs={
            "password": {"kind": "env", "ref": "AGA_CUSTOMER_PASSWORD"},
            "graph_api_secret": {"kind": "vault", "ref": "secret/path"},
        },
        last_verification_status=ConnectionVerificationStatus.SUCCESS,
    )

    doc = profile.to_dict()
    restored = ConnectionProfile.from_dict(doc)

    assert doc["_key"] == profile.connection_profile_id
    assert restored.deployment_mode == DeploymentMode.AMP
    assert restored.last_verification_status == ConnectionVerificationStatus.SUCCESS
    assert restored.secret_refs["password"]["ref"] == "AGA_CUSTOMER_PASSWORD"


def test_workspace_rejects_secret_like_metadata_keys():
    """Product metadata rejects fields that look like resolved secrets."""

    workspace = create_workspace(
        customer_name="Example Customer",
        project_name="Graph Analytics",
        environment="dev",
        metadata={"password": "do-not-store"},
    )

    try:
        workspace.to_dict()
    except ValidationError as exc:
        assert "password" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for secret-like metadata")


def test_graph_profile_round_trip():
    """Graph profiles preserve schema and role metadata."""

    profile = create_graph_profile(
        workspace_id="workspace-1",
        connection_profile_id="connection-1",
        graph_name="customer_graph",
        vertex_collections=["Device", "IP"],
        edge_collections=["connects_to"],
        edge_definitions=[
            {
                "edge_collection": "connects_to",
                "from_vertex_collections": ["Device"],
                "to_vertex_collections": ["IP"],
            }
        ],
        collection_roles={"core": ["Device", "IP"], "satellite": ["Location"]},
        counts={"vertices": 10, "edges": 20},
    )

    restored = GraphProfile.from_dict(profile.to_dict())

    assert restored.graph_profile_id == profile.graph_profile_id
    assert restored.graph_name == "customer_graph"
    assert restored.collection_roles["core"] == ["Device", "IP"]
    assert restored.counts["edges"] == 20


def test_source_document_round_trip():
    """Source documents preserve hashes and extracted content references."""

    document = create_source_document(
        workspace_id="workspace-1",
        filename="requirements.md",
        mime_type="text/markdown",
        sha256="abc123",
        storage_mode=DocumentStorageMode.INLINE,
        extracted_text="Find influential entities.",
    )

    restored = SourceDocument.from_dict(document.to_dict())

    assert restored.document_id == document.document_id
    assert restored.storage_mode == DocumentStorageMode.INLINE
    assert restored.extracted_text == "Find influential entities."


def test_requirement_interview_round_trip():
    """Requirement interviews preserve copilot draft and provenance."""

    interview = create_requirement_interview(
        workspace_id="workspace-1",
        graph_profile_id="graph-profile-1",
        status=RequirementInterviewStatus.READY_FOR_REVIEW,
        domain="AdTech",
        questions=[{"id": "q1", "text": "What decision should this support?"}],
        answers=[{"question_id": "q1", "text": "Audience planning"}],
        schema_observations={"collections": ["Device", "IP"]},
        draft_brd="# Business Requirements",
        provenance_labels=[
            {"path": "summary", "label": "user_provided"},
            {"path": "collections", "label": "observed_from_schema"},
        ],
    )

    restored = RequirementInterview.from_dict(interview.to_dict())

    assert restored.status == RequirementInterviewStatus.READY_FOR_REVIEW
    assert restored.schema_observations["collections"] == ["Device", "IP"]
    assert restored.provenance_labels[1]["label"] == "observed_from_schema"


def test_requirement_version_round_trip():
    """Requirement versions preserve approval and lineage references."""

    version = create_requirement_version(
        workspace_id="workspace-1",
        version=1,
        status=RequirementVersionStatus.APPROVED,
        document_ids=["document-1"],
        analysis_requirements_id="analysis-req-1",
        requirement_interview_id="requirement-interview-1",
        summary="Analyze influence.",
        objectives=[{"id": "OBJ-1", "text": "Rank important nodes"}],
        requirements=[{"id": "REQ-1", "text": "Generate PageRank"}],
        constraints=[{"id": "CON-1", "text": "Finish in 15 minutes"}],
    )

    restored = RequirementVersion.from_dict(version.to_dict())

    assert restored.status == RequirementVersionStatus.APPROVED
    assert restored.document_ids == ["document-1"]
    assert restored.analysis_requirements_id == "analysis-req-1"
    assert restored.requirements[0]["id"] == "REQ-1"


def test_workflow_run_round_trip_with_visualizer_dag():
    """Workflow runs preserve visual DAG step state and artifact refs."""

    run = create_workflow_run(
        workspace_id="workspace-1",
        workflow_mode=WorkflowMode.PARALLEL_AGENTIC,
        status=WorkflowRunStatus.RUNNING,
        requirement_version_id="requirement-version-1",
        graph_profile_id="graph-profile-1",
        template_ids=["template-1"],
        steps=[
            WorkflowStep(
                step_id="schema_analysis",
                label="Schema Analysis",
                status=WorkflowStepStatus.COMPLETED,
                agent_name="SchemaAgent",
                artifact_refs=[
                    {"type": "graph_profile", "id": "graph-profile-1"},
                ],
            ),
            WorkflowStep(
                step_id="requirements_extraction",
                label="Requirements Extraction",
                status=WorkflowStepStatus.RUNNING,
                agent_name="RequirementsAgent",
                retry_count=1,
                warnings=["Awaiting user confirmation"],
            ),
        ],
        dag_edges=[
            WorkflowDAGEdge(
                from_step_id="schema_analysis",
                to_step_id="requirements_extraction",
            )
        ],
        analysis_execution_ids=["execution-1"],
        metadata={"poll_revision": 1},
    )

    restored = WorkflowRun.from_dict(run.to_dict())

    assert restored.workflow_mode == WorkflowMode.PARALLEL_AGENTIC
    assert restored.status == WorkflowRunStatus.RUNNING
    assert restored.steps[0].status == WorkflowStepStatus.COMPLETED
    assert restored.steps[1].retry_count == 1
    assert restored.dag_edges[0].from_step_id == "schema_analysis"
    assert restored.analysis_execution_ids == ["execution-1"]


def test_report_manifest_round_trip():
    """Report manifests preserve lineage for dynamic report rendering."""

    manifest = create_report_manifest(
        workspace_id="workspace-1",
        run_id="run-1",
        title="Audience Graph Analysis",
        status=ReportStatus.READY,
        summary="High influence identity clusters.",
        section_ids=["section-1"],
        chart_ids=["chart-1"],
        requirement_version_id="requirement-version-1",
        analysis_execution_ids=["execution-1"],
        result_collections=["analysis_results"],
    )

    restored = manifest.from_dict(manifest.to_dict())

    assert restored.status == ReportStatus.READY
    assert restored.section_ids == ["section-1"]
    assert restored.result_collections == ["analysis_results"]


def test_report_section_and_chart_spec_round_trip():
    """Report sections and chart specs preserve structured rendering data."""

    section = create_report_section(
        workspace_id="workspace-1",
        report_id="report-1",
        order=1,
        type=ReportSectionType.INSIGHT,
        title="Key Findings",
        content={"markdown": "Cluster A has high centrality."},
        evidence_refs=[{"type": "query", "id": "query-1"}],
    )
    chart = create_chart_spec(
        workspace_id="workspace-1",
        report_id="report-1",
        title="Top Nodes",
        chart_type=ChartType.BAR,
        data_source={"collection": "analysis_results"},
        encoding={"x": "node", "y": "score"},
    )

    restored_section = section.from_dict(section.to_dict())
    restored_chart = chart.from_dict(chart.to_dict())

    assert restored_section.type == ReportSectionType.INSIGHT
    assert restored_section.evidence_refs[0]["id"] == "query-1"
    assert restored_chart.chart_type == ChartType.BAR
    assert restored_chart.encoding["y"] == "score"


def test_published_snapshot_and_audit_event_round_trip():
    """Published snapshots and audit events preserve immutable UI records."""

    snapshot = create_published_snapshot(
        workspace_id="workspace-1",
        report_id="report-1",
        title="Audience Graph Analysis",
        published_by="analyst@example.com",
        content_hash="sha256:abc123",
        rendered_snapshot={"sections": [{"title": "Summary"}]},
        export_uris={"pdf": "s3://bucket/report.pdf"},
    )
    audit_event = create_audit_event(
        workspace_id="workspace-1",
        actor="analyst@example.com",
        action="publish_report",
        target_type="report",
        target_id="report-1",
        details={"snapshot_id": snapshot.published_snapshot_id},
    )

    restored_snapshot = snapshot.from_dict(snapshot.to_dict())
    restored_event = audit_event.from_dict(audit_event.to_dict())

    assert restored_snapshot.content_hash == "sha256:abc123"
    assert restored_snapshot.export_uris["pdf"] == "s3://bucket/report.pdf"
    assert restored_event.action == "publish_report"
    assert restored_event.details["snapshot_id"] == snapshot.published_snapshot_id

