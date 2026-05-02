#!/usr/bin/env python3
"""Seed a real `addtech-knowledge-graph` workspace into the Product API.

Bypasses the Create Workspace / Create Connection Profile click-through
in the UI by creating the metadata directly through the in-process Product
Service. After running, open the printed `workspaceId` URL to land on a
fully populated workspace with:

  * a workspace ("AdTech Demo")
  * a connection profile pointing at addtech-knowledge-graph (verified)
  * a graph profile for AdtechGraph (with vertex/edge collections discovered)
  * the AdTech business requirements doc as an inline source document
  * a completed workflow run with 6 agent steps
  * one report per markdown file under
    workflow_output/adtech_demo/markdown_reports/

Usage:
    python scripts/seed_adtech_workspace.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

# Product metadata lives in a separate database. The running FastAPI server
# was started with this same override (`ARANGO_DATABASE=aga_workspace`).
os.environ["ARANGO_DATABASE"] = "aga_workspace"

# So `_graph_view` resolves when run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from arango import ArangoClient

from _graph_view import (
    build_components_graph_html,
    build_pagerank_graph_html,
)
from graph_analytics_ai.product.factory import create_product_service
from graph_analytics_ai.product.models import (
    ChartType,
    DeploymentMode,
    DocumentStorageMode,
    ReportSectionType,
    RequirementVersionStatus,
    Workspace,
    WorkflowDAGEdge,
    WorkflowMode,
    WorkflowRunStatus,
    WorkflowStep,
    WorkflowStepStatus,
    create_audit_event,
    create_chart_spec,
    create_report_manifest,
    create_report_section,
    create_requirement_version,
    create_source_document,
)


# --------------------------------------------------------------------------- #
# Configuration                                                               #
# --------------------------------------------------------------------------- #
ADTECH_ENDPOINT = os.environ["ARANGO_ENDPOINT"]
ADTECH_DATABASE = "addtech-knowledge-graph"
ADTECH_USER = os.environ["ARANGO_USER"]
ADTECH_GRAPH = "AdtechGraph"

REQUIREMENTS_DOC = Path(
    "/Users/arthurkeen/code/premion-graph-analytics/docs/AdTech_business_requirements.md"
)
REPORTS_DIR = REPO_ROOT / "workflow_output" / "adtech_demo" / "markdown_reports"
WORKFLOW_STATE_PATH = (
    REPO_ROOT / "workflow_output" / "adtech_demo" / "workflow_state.json"
)

WORKSPACE_DB = "aga_workspace"
ADTECH_WORKSPACE_ID = "workspace-adtech-demo"

# Edge collections of `AdtechGraph`, used by graph-view chart builders to
# resolve neighborhoods around top-N nodes / component members. Mirrors the
# graph definition discovered against `addtech-knowledge-graph`.
ADTECH_EDGE_COLLECTIONS = [
    "INSTANCE_OF",
    "LOCATED_IN",
    "OWNED_BY",
    "SEEN_ON_APP",
    "SEEN_ON_IP",
    "SEEN_ON_SITE",
    "SERVED_BY",
]

WORKFLOW_STEP_PLAN = [
    ("schema-analyst", "Schema Analysis", "SchemaAnalyst"),
    ("requirements-analyst", "Requirements Extraction", "RequirementsAnalyst"),
    ("use-case-expert", "Use Case Generation", "UseCaseExpert"),
    ("template-engineer", "Template Generation", "TemplateEngineer"),
    ("execution-specialist", "GAE Execution", "ExecutionSpecialist"),
    ("reporting-specialist", "Report Generation", "ReportingSpecialist"),
]


# --------------------------------------------------------------------------- #
# Approved requirement version (extracted from the AdTech BRD)                #
# --------------------------------------------------------------------------- #
ADTECH_REQUIREMENTS_SUMMARY = (
    "Build a proprietary CTV/OTT Household & Identity Graph from the AdTech "
    "Company's no-bid logs to achieve identity-resolution data autonomy, "
    "stitching ~330M devices to ~120M residential IPs into stable household "
    "clusters (PHIDs) and enabling cross-device attribution, look-alike "
    "segmentation, fraud filtering, and inventory forecasting on top of "
    "ArangoDB's Graph Analytics Engine."
)

ADTECH_OBJECTIVES = [
    {
        "id": "OBJ-001",
        "title": "Achieve identity-resolution data autonomy",
        "description": (
            "Reduce dependence on third-party identity providers (Liveramp, "
            "Cadent) by deriving household identity from internal no-bid logs."
        ),
        "provenance": "extracted_from_brd",
    },
    {
        "id": "OBJ-002",
        "title": "Build a stable Household ID (PHID)",
        "description": (
            "Stitch ~330M unique devices to ~120M residential IPs to define a "
            "Household ID (PHID) usable across all targeting and attribution."
        ),
        "provenance": "extracted_from_brd",
    },
    {
        "id": "OBJ-003",
        "title": "Enable cross-device attribution",
        "description": (
            "Trace CTV impressions to mobile/web conversions inside the same "
            "household to prove campaign ROI."
        ),
        "provenance": "extracted_from_brd",
    },
    {
        "id": "OBJ-004",
        "title": "Lower targeting costs via in-house look-alikes",
        "description": (
            "Generate proprietary look-alike segments using behavioral graph "
            "propagation as a cheaper alternative to third-party data products."
        ),
        "provenance": "extracted_from_brd",
    },
    {
        "id": "OBJ-005",
        "title": "Improve inventory forecasting and pricing",
        "description": (
            "Score apps, sites, and exchanges so inventory availability can be "
            "predicted and priced with high confidence for managed-service "
            "campaigns."
        ),
        "provenance": "extracted_from_brd",
    },
]

ADTECH_REQUIREMENTS = [
    {
        "id": "REQ-001",
        "title": "Household Identity Resolution (Stitched View)",
        "description": (
            "Group Devices and IPs into household clusters using Weakly "
            "Connected Components so every Device/IP receives a candidate "
            "PHID."
        ),
        "use_case_type": "community_detection",
        "primary_algorithm": "wcc",
        "vertex_collections": ["Device", "IP"],
        "edge_collections": ["SEEN_ON_IP"],
        "outputs": ["phid"],
        "supports_objectives": ["OBJ-002"],
        "provenance": "extracted_from_brd",
    },
    {
        "id": "REQ-002",
        "title": "Commercial / Fraud IP Filtering",
        "description": (
            "Distinguish residential households from high-cardinality "
            "commercial / bot IPs (airports, coffee shops, universities) by "
            "ranking IPs on degree-style centrality so the WCC step is "
            "constrained to legitimate residential clusters."
        ),
        "use_case_type": "anomaly_detection",
        "primary_algorithm": "pagerank",
        "vertex_collections": ["IP", "Device"],
        "edge_collections": ["SEEN_ON_IP"],
        "outputs": ["ip_type"],
        "thresholds": {"residential_max_degree": 20},
        "supports_objectives": ["OBJ-002"],
        "provenance": "extracted_from_brd",
    },
    {
        "id": "REQ-003",
        "title": "Behavioral Look-alike Segmentation",
        "description": (
            "Propagate viewing-interest labels from labeled Devices to all "
            "Devices in the same household using Label Propagation, so every "
            "device in a PHID inherits a segment_interest tag."
        ),
        "use_case_type": "community_detection",
        "primary_algorithm": "label_propagation",
        "vertex_collections": ["Device", "InstalledApp", "AppProduct"],
        "edge_collections": ["SEEN_ON_APP", "INSTANCE_OF"],
        "outputs": ["segment_interest"],
        "supports_objectives": ["OBJ-004"],
        "provenance": "extracted_from_brd",
    },
    {
        "id": "REQ-004",
        "title": "Cross-Device Influence & Attribution",
        "description": (
            "Establish whether an impression on one device (e.g. CTV) and a "
            "downstream conversion on another device share a path within the "
            "same household graph cluster."
        ),
        "use_case_type": "pathfinding",
        "primary_algorithm": "wcc",
        "vertex_collections": ["Device", "IP", "InstalledApp"],
        "edge_collections": ["SEEN_ON_IP", "SEEN_ON_APP"],
        "outputs": ["is_attributed"],
        "supports_objectives": ["OBJ-003"],
        "provenance": "extracted_from_brd",
    },
    {
        "id": "REQ-005",
        "title": "Content Popularity & Inventory Scoring",
        "description": (
            "Rank AppProduct / Site / Exchange nodes by PageRank weighted by "
            "engagement frequency to surface the highest-value inventory and "
            "predict delivery for managed-service clients."
        ),
        "use_case_type": "centrality",
        "primary_algorithm": "pagerank",
        "vertex_collections": ["AppProduct", "Site", "Exchange"],
        "edge_collections": ["SERVED_BY", "OWNED_BY"],
        "outputs": ["authority_rank"],
        "supports_objectives": ["OBJ-005"],
        "provenance": "extracted_from_brd",
    },
]

ADTECH_CONSTRAINTS = [
    {
        "id": "CON-001",
        "title": "No-bid log ingestion volume",
        "description": (
            "The pipeline must be able to ingest ~16 TB of no-bid logs per day."
        ),
        "provenance": "extracted_from_brd",
    },
    {
        "id": "CON-002",
        "title": "Identity refresh cadence",
        "description": (
            "Device-IP associations must be refreshed at least every two weeks "
            "to keep household clusters stable."
        ),
        "provenance": "extracted_from_brd",
    },
    {
        "id": "CON-003",
        "title": "Graph database platform",
        "description": (
            "The household and identity graph runs on ArangoDB and must use "
            "the Graph Analytics Engine (GAE) for batch graph algorithms."
        ),
        "provenance": "extracted_from_brd",
    },
    {
        "id": "CON-004",
        "title": "Cloud / data-warehouse environment",
        "description": (
            "Source data lives in AWS and Snowflake; production loaders must "
            "remain compatible with that stack."
        ),
        "provenance": "extracted_from_brd",
    },
]


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
def ensure_clean_workspace_db() -> None:
    """Drop and recreate `aga_workspace` so re-seeding starts fresh."""

    client = ArangoClient(hosts=os.environ["ARANGO_ENDPOINT"])
    sys_db = client.db(
        "_system",
        username=os.environ["ARANGO_USER"],
        password=os.environ["ARANGO_PASSWORD"],
    )
    if sys_db.has_database(WORKSPACE_DB):
        sys_db.delete_database(WORKSPACE_DB)
    sys_db.create_database(
        WORKSPACE_DB,
        users=[
            {
                "username": os.environ["ARANGO_USER"],
                "password": os.environ["ARANGO_PASSWORD"],
                "active": True,
            }
        ],
    )


def now() -> datetime:
    return datetime.now(timezone.utc)


def adtech_db_handle():
    """Return a python-arango handle to the addtech-knowledge-graph database."""

    client = ArangoClient(hosts=os.environ["ARANGO_ENDPOINT"])
    return client.db(
        ADTECH_DATABASE,
        username=os.environ["ARANGO_USER"],
        password=os.environ["ARANGO_PASSWORD"],
    )


def load_workflow_report_index() -> Dict[str, Dict[str, Any]]:
    """Map title -> agent-run report dict (algorithm, metadata.charts, …)."""

    if not WORKFLOW_STATE_PATH.exists():
        return {}
    state = json.loads(WORKFLOW_STATE_PATH.read_text(encoding="utf-8"))
    index: Dict[str, Dict[str, Any]] = {}
    for rep in state.get("reports", []):
        title = rep.get("title")
        if title:
            index[title] = rep

    # Map result_collection -> execution result so we can find which collection
    # each report's algorithm wrote into.
    exec_by_template: Dict[str, Dict[str, Any]] = {}
    for ex in state.get("execution_results", []):
        name = ex.get("template_name")
        if name:
            exec_by_template[name] = ex
    for title, rep in index.items():
        prefix, _, template_part = title.partition(":")
        template_name = title.split(": ", 1)[-1] if ": " in title else title
        rep["_execution"] = exec_by_template.get(template_name)
    return index


def build_graph_view_chart(
    db_addtech: Any,
    algorithm: str,
    result_collection: Optional[str],
) -> Optional[str]:
    """Build a Plotly HTML graph view for an algorithm result, when relevant."""

    if not result_collection:
        return None
    if not db_addtech.has_collection(result_collection):
        return None
    if db_addtech.collection(result_collection).count() == 0:
        return None

    algo = (algorithm or "").lower()
    try:
        if algo in {"pagerank", "betweenness"}:
            return build_pagerank_graph_html(
                db_addtech,
                result_collection,
                ADTECH_EDGE_COLLECTIONS,
                top_n=20,
                title=(
                    "PageRank top-20 nodes and 1-hop neighborhood"
                    if algo == "pagerank"
                    else "Betweenness top-20 nodes and 1-hop neighborhood"
                ),
            )
        if algo in {"wcc", "scc", "label_propagation"}:
            return build_components_graph_html(
                db_addtech,
                result_collection,
                ADTECH_EDGE_COLLECTIONS,
                top_components=4,
                members_per_component=8,
                field="community" if algo == "label_propagation" else "component",
                title=(
                    "Top connected components"
                    if algo in {"wcc", "scc"}
                    else "Top label-propagation communities"
                ),
            )
    except Exception as exc:  # noqa: BLE001 - graph view is best-effort
        print(f"  WARN: graph view failed for {algorithm} on {result_collection}: {exc}")
        return None
    return None


def _ingest_charts(
    *,
    service: Any,
    workspace_id: str,
    manifest_id: str,
    title: str,
    workflow_index: Dict[str, Dict[str, Any]],
    db_addtech: Any,
) -> int:
    """Create ChartSpec rows for one report and return the count created."""

    workflow_report = workflow_index.get(title) or {}
    metadata_charts: Dict[str, str] = (
        workflow_report.get("metadata", {}) or {}
    ).get("charts", {}) or {}

    created = 0

    # Pre-rendered Plotly HTML charts produced by the agentic workflow.
    pretty = {
        "top_influencers": "Top influencers (PageRank)",
        "distribution": "Score distribution",
        "cumulative": "Cumulative influence",
        "top_components": "Top components",
        "size_distribution": "Component size distribution",
        "connectivity": "Connectivity overview",
    }
    for key, html in metadata_charts.items():
        if not isinstance(html, str) or not html.strip():
            continue
        chart = create_chart_spec(
            workspace_id=workspace_id,
            report_id=manifest_id,
            title=pretty.get(key, key.replace("_", " ").title()),
            chart_type=ChartType.CUSTOM,
            data={"kind": "plotly_html", "html": html},
            metadata={"source": "workflow_state", "chart_key": key},
        )
        service.repository.create_chart_spec(chart)
        created += 1

    # Interactive node-link graph view derived from the result collection.
    execution = workflow_report.get("_execution") or {}
    algorithm = execution.get("algorithm")
    result_collection = execution.get("result_collection")
    graph_html = build_graph_view_chart(
        db_addtech=db_addtech,
        algorithm=algorithm,
        result_collection=result_collection,
    )
    if graph_html:
        chart = create_chart_spec(
            workspace_id=workspace_id,
            report_id=manifest_id,
            title=f"Interactive graph view ({algorithm})",
            chart_type=ChartType.CUSTOM,
            data={"kind": "plotly_html", "html": graph_html},
            metadata={
                "source": "graph_view",
                "algorithm": algorithm,
                "result_collection": result_collection,
            },
        )
        service.repository.create_chart_spec(chart)
        created += 1

    return created


def parse_markdown_report(path: Path) -> tuple[str, str, list[tuple[str, str]]]:
    """Split a markdown report into (title, summary, [(section_title, body)])."""

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    title = path.stem
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        lines = lines[1:]

    summary = ""
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            summary = stripped
            lines = lines[i + 1:]
            break

    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    current_body: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_body).strip()))
            current_title = line[3:].strip()
            current_body = []
        else:
            current_body.append(line)

    if current_title is not None:
        sections.append((current_title, "\n".join(current_body).strip()))

    if not sections:
        sections.append(("Report", text.strip()))

    return title, summary, sections


# --------------------------------------------------------------------------- #
# Seed                                                                        #
# --------------------------------------------------------------------------- #
def main() -> None:
    print("=" * 70)
    print("SEEDING ADTECH WORKSPACE INTO PRODUCT API")
    print("=" * 70)

    ensure_clean_workspace_db()
    print(f"Reset {WORKSPACE_DB!r} on {ADTECH_ENDPOINT}")

    service = create_product_service()
    print("Product service ready (backed by aga_workspace)")

    # ---- 1. Workspace (pinned ID so the URL stays stable) ---------------- #
    workspace = Workspace(
        workspace_id=ADTECH_WORKSPACE_ID,
        customer_name="AdTech Demo",
        project_name="Household Identity",
        environment="prod",
        description="CTV/OTT household identity resolution against the AdTech "
        "demo cluster (addtech-knowledge-graph / AdtechGraph).",
        tags=["adtech", "ctv", "household-identity"],
    )
    service.repository.create_workspace(workspace)
    service.repository.create_audit_event(
        create_audit_event(
            workspace_id=workspace.workspace_id,
            actor="seed-script",
            action="create_workspace",
            target_type="workspace",
            target_id=workspace.workspace_id,
        )
    )
    print(f"Workspace: {workspace.workspace_id}  ({workspace.customer_name})")

    # ---- 2. Connection profile ------------------------------------------- #
    profile = service.create_connection_profile(
        workspace_id=workspace.workspace_id,
        name="addtech-prod-demo",
        deployment_mode=DeploymentMode.SELF_MANAGED,
        endpoint=ADTECH_ENDPOINT,
        database=ADTECH_DATABASE,
        username=ADTECH_USER,
        verify_ssl=True,
        secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
        metadata={"description": "addtech-knowledge-graph on prod demo pilot"},
    )
    print(f"Connection profile: {profile.connection_profile_id}  -> {ADTECH_DATABASE}")

    # ---- 3. Verify the connection ---------------------------------------- #
    verification = service.verify_connection_profile(profile.connection_profile_id)
    print(f"Verification: {verification.status}")

    # ---- 4. Discover AdtechGraph ----------------------------------------- #
    discovery = service.discover_graph_profile(
        connection_profile_id=profile.connection_profile_id,
        graph_name=ADTECH_GRAPH,
        created_by="seed-script",
    )
    graph_profile_id = discovery.graph_profile["graph_profile_id"]
    vertex_count = len(discovery.graph_profile.get("vertex_collections", []))
    edge_count = len(discovery.graph_profile.get("edge_collections", []))
    print(
        f"Graph profile: {graph_profile_id}  "
        f"({vertex_count} vertex / {edge_count} edge collections)"
    )

    # ---- 5. Source document (requirements) ------------------------------- #
    requirements_text = REQUIREMENTS_DOC.read_text(encoding="utf-8")
    sha = hashlib.sha256(requirements_text.encode("utf-8")).hexdigest()
    document = create_source_document(
        workspace_id=workspace.workspace_id,
        filename=REQUIREMENTS_DOC.name,
        mime_type="text/markdown",
        sha256=sha,
        storage_mode=DocumentStorageMode.INLINE,
        storage_uri=str(REQUIREMENTS_DOC),
        extracted_text=requirements_text,
        uploaded_at=now(),
        metadata={
            "source_path": str(REQUIREMENTS_DOC),
            "chars": len(requirements_text),
        },
    )
    service.repository.create_source_document(document)
    print(f"Source document: {document.document_id}  ({REQUIREMENTS_DOC.name})")

    # ---- 5b. Approved requirement version ------------------------------- #
    requirement_version = create_requirement_version(
        workspace_id=workspace.workspace_id,
        version=1,
        status=RequirementVersionStatus.APPROVED,
        document_ids=[document.document_id],
        summary=ADTECH_REQUIREMENTS_SUMMARY,
        objectives=ADTECH_OBJECTIVES,
        requirements=ADTECH_REQUIREMENTS,
        constraints=ADTECH_CONSTRAINTS,
        approved_at=now(),
        metadata={
            "source_document_id": document.document_id,
            "source_path": str(REQUIREMENTS_DOC),
            "approved_by": "seed-script",
            "provenance": "extracted_from_brd",
        },
    )
    service.repository.create_requirement_version(requirement_version)
    service.repository.create_audit_event(
        create_audit_event(
            workspace_id=workspace.workspace_id,
            actor="seed-script",
            action="approve_requirement_version",
            target_type="requirement_version",
            target_id=requirement_version.requirement_version_id,
            details={
                "version": requirement_version.version,
                "status": requirement_version.status.value,
                "objectives": len(requirement_version.objectives),
                "requirements": len(requirement_version.requirements),
                "source_document_id": document.document_id,
            },
        )
    )
    print(
        f"Requirement version: {requirement_version.requirement_version_id}  "
        f"(v{requirement_version.version}, {requirement_version.status.value}, "
        f"{len(requirement_version.objectives)} objectives / "
        f"{len(requirement_version.requirements)} requirements)"
    )

    # ---- 6. Workflow run ------------------------------------------------- #
    base_time = now()
    workflow_steps: list[WorkflowStep] = []
    for offset, (step_id, label, agent_name) in enumerate(WORKFLOW_STEP_PLAN):
        workflow_steps.append(
            WorkflowStep(
                step_id=step_id,
                label=label,
                status=WorkflowStepStatus.COMPLETED,
                agent_name=agent_name,
                started_at=base_time,
                completed_at=base_time,
                duration_ms=2_000,
                metadata={"index": offset},
            )
        )
    workflow_edges = [
        WorkflowDAGEdge(
            from_step_id=WORKFLOW_STEP_PLAN[i][0],
            to_step_id=WORKFLOW_STEP_PLAN[i + 1][0],
        )
        for i in range(len(WORKFLOW_STEP_PLAN) - 1)
    ]
    run = service.create_workflow_run_from_steps(
        workspace_id=workspace.workspace_id,
        workflow_mode=WorkflowMode.AGENTIC,
        steps=workflow_steps,
        dag_edges=workflow_edges,
        graph_profile_id=graph_profile_id,
        metadata={
            "source": "scripts/run_adtech_demo.py",
            "reports_dir": str(REPORTS_DIR),
        },
    )
    run.status = WorkflowRunStatus.COMPLETED
    run.started_at = base_time
    run.completed_at = base_time
    service.repository.update_workflow_run(run)
    print(f"Workflow run: {run.run_id}  ({len(workflow_steps)} steps, completed)")

    # ---- 7. Reports ------------------------------------------------------ #
    if not REPORTS_DIR.exists():
        print(f"WARNING: {REPORTS_DIR} not found; skipping report ingestion")
        return

    report_files = sorted(REPORTS_DIR.glob("report_*.md"))
    if not report_files:
        print(f"WARNING: no markdown reports found in {REPORTS_DIR}")
        return

    workflow_reports_by_title = load_workflow_report_index()
    db_addtech = adtech_db_handle()

    for report_path in report_files:
        title, summary, sections = parse_markdown_report(report_path)
        manifest = create_report_manifest(
            workspace_id=workspace.workspace_id,
            run_id=run.run_id,
            title=title,
            summary=summary[:500],
            status="ready",
            metadata={"source_file": str(report_path)},
        )
        service.repository.create_report_manifest(manifest)

        for order, (section_title, body) in enumerate(sections):
            section = create_report_section(
                workspace_id=workspace.workspace_id,
                report_id=manifest.report_id,
                order=order,
                type=ReportSectionType.TEXT,
                title=section_title,
                content={"text": body},
            )
            service.repository.create_report_section(section)

        chart_count = _ingest_charts(
            service=service,
            workspace_id=workspace.workspace_id,
            manifest_id=manifest.report_id,
            title=title,
            workflow_index=workflow_reports_by_title,
            db_addtech=db_addtech,
        )

        print(
            f"  Report: {manifest.report_id}  '{title}' "
            f"({len(sections)} sections, {chart_count} charts)"
        )

    # ---- 8. Print URL ---------------------------------------------------- #
    url = f"http://localhost:3000/workspace?workspaceId={workspace.workspace_id}"
    print()
    print("=" * 70)
    print("DONE. Open the workspace UI at:")
    print(f"  {url}")
    print("=" * 70)


if __name__ == "__main__":
    main()
