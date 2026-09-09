#!/usr/bin/env python3
"""Seed a FinReflectKG workspace into the Product API.

Bypasses the Create Workspace / Create Connection Profile click-through in the
UI by creating the metadata directly through the in-process Product Service.
After running, open the printed workspace URL to land on a fully populated
workspace with:

  * a workspace ("FinReflectKG Demo")
  * a connection profile pointing at the restored FinReflect database (verified)
  * a graph profile for the named graph (vertex/edge collections discovered)
  * the FinReflectKG business requirements doc as an inline source document
  * an approved requirement version extracted from that doc
  * a completed workflow run with 6 agent steps
  * one report per markdown file under
    workflow_output/finreflect_demo/markdown_reports/

IMPORTANT -- unlike ``seed_adtech_workspace.py``, this script does NOT drop and
recreate ``aga_workspace``. That script's ``ensure_clean_workspace_db()`` wipes
the whole product database, which would destroy the AdTech demo workspace. This
one is additive: it purges only rows belonging to its own pinned workspace id,
so re-seeding is idempotent and the AdTech workspace survives.

Usage:
    python scripts/seed_finreflect_workspace.py
    FINREFLECT_DB=FinReflectKgOneShard python scripts/seed_finreflect_workspace.py
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

# The database being analysed (must already be restored).
FINREFLECT_DATABASE = os.environ.get("FINREFLECT_DB", "FinReflectKgTemporal")

# Product metadata lives in its own database, same as the AdTech seeder.
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
FINREFLECT_ENDPOINT = os.environ["ARANGO_ENDPOINT"]
FINREFLECT_USER = os.environ["ARANGO_USER"]

# Named graph differs per build; both define `relations` from [Node] to [Node].
GRAPH_BY_DB = {
    "FinReflectKgTemporal": "FinReflectKgTemporal",
    "FinReflectKgOneShard": "FinReflectKG",
}
FINREFLECT_GRAPH = GRAPH_BY_DB.get(FINREFLECT_DATABASE, FINREFLECT_DATABASE)

REQUIREMENTS_DOC = REPO_ROOT / "docs" / "FinReflectKG_business_requirements.md"
REPORTS_DIR = REPO_ROOT / "workflow_output" / "finreflect_demo" / "markdown_reports"
WORKFLOW_STATE_PATH = (
    REPO_ROOT / "workflow_output" / "finreflect_demo" / "workflow_state.json"
)

WORKSPACE_DB = "aga_workspace"
FINREFLECT_WORKSPACE_ID = "workspace-finreflect-demo"

# The single edge collection of the FinReflect graph. Used by the graph-view
# chart builders to resolve neighborhoods around top-N nodes / component members.
FINREFLECT_EDGE_COLLECTIONS = ["relations"]

WORKFLOW_STEP_PLAN = [
    ("schema-analyst", "Schema Analysis", "SchemaAnalyst"),
    ("requirements-analyst", "Requirements Extraction", "RequirementsAnalyst"),
    ("use-case-expert", "Use Case Generation", "UseCaseExpert"),
    ("template-engineer", "Template Generation", "TemplateEngineer"),
    ("execution-specialist", "GAE Execution", "ExecutionSpecialist"),
    ("reporting-specialist", "Report Generation", "ReportingSpecialist"),
]

# Product metadata collections that carry a `workspace_id`, purged on re-seed.
WORKSPACE_SCOPED_COLLECTIONS = [
    "aga_analysis_epochs",
    "aga_analysis_executions",
    "aga_analysis_templates",
    "aga_audit_events",
    "aga_chart_specs",
    "aga_collection_roles",
    "aga_connection_profiles",
    "aga_documents",
    "aga_graph_profiles",
    "aga_graph_sets",
    "aga_published_snapshots",
    "aga_report_manifests",
    "aga_report_sections",
    "aga_requirement_interviews",
    "aga_requirement_versions",
    "aga_retention_policies",
    "aga_use_cases",
    "aga_workflow_runs",
    "aga_workspaces",
]


# --------------------------------------------------------------------------- #
# Approved requirement version (extracted from the FinReflectKG BRD)          #
# --------------------------------------------------------------------------- #
FINREFLECT_REQUIREMENTS_SUMMARY = (
    "Derive aggregate intelligence from mandatory corporate disclosure by "
    "analysing FinReflectKG -- a knowledge graph of ~3.1M entities and ~17.5M "
    "typed relationships extracted from S&P 500 10-K SEC filings (FY2014-2024). "
    "Rank disclosure salience and corporate ecosystem position, detect shared "
    "exposures that transmit shocks across unrelated firms, derive a risk "
    "taxonomy from evidence rather than GICS, track disclosure drift across the "
    "decade, and measure extraction quality -- on ArangoDB's Graph Analytics "
    "Engine."
)

FINREFLECT_OBJECTIVES = [
    {
        "id": "OBJ-001",
        "title": "Rank by structural position, not market capitalisation",
        "description": (
            "Identify the firms, materials, geographies, and regulations that "
            "occupy load-bearing positions in the disclosed economy, "
            "independent of index weight or market cap."
        ),
        "provenance": "extracted_from_brd",
    },
    {
        "id": "OBJ-002",
        "title": "Surface concentration risk invisible to portfolio analysis",
        "description": (
            "Detect shared dependencies that multiple otherwise-unrelated "
            "companies independently disclose, and which sector-based "
            "diversification therefore cannot see."
        ),
        "provenance": "extracted_from_brd",
    },
    {
        "id": "OBJ-003",
        "title": "Derive a risk taxonomy from evidence",
        "description": (
            "Let communities of co-disclosed concepts define the thematic map, "
            "instead of imposing a classification standard such as GICS."
        ),
        "provenance": "extracted_from_brd",
    },
    {
        "id": "OBJ-004",
        "title": "Measure the extraction itself",
        "description": (
            "Because the graph is LLM-extracted, use graph structure as a "
            "quality instrument: fragmentation, orphan islands, and reciprocal "
            "duplicate loops are measurable defects."
        ),
        "provenance": "extracted_from_brd",
    },
    {
        "id": "OBJ-005",
        "title": "Track disclosure drift across 2014-2024",
        "description": (
            "Take the same measurement per fiscal year and rank concepts by "
            "magnitude of movement, attributing each shift to the filings that "
            "caused it."
        ),
        "provenance": "extracted_from_brd",
    },
]

FINREFLECT_REQUIREMENTS = [
    {
        "id": "REQ-001",
        "title": "Disclosure Salience Ranking",
        "description": (
            "Rank concepts across the whole graph by PageRank to establish "
            "empirically which financial concepts dominate S&P 500 disclosure. "
            "Universal metrics (revenue, net income) are expected at the top and "
            "serve as the pipeline's correctness anchor."
        ),
        "algorithm": "pagerank",
        "scope": "whole_graph",
        "provenance": "extracted_from_brd",
    },
    {
        "id": "REQ-002",
        "title": "Corporate Ecosystem Influence",
        "description": (
            "Rank organisations by PageRank over an ORG->ORG projection "
            "(has_stake_in, competes_with, partners_with, invests_in, "
            "depends_on). Must NOT run whole-graph: ORG nodes are near-pure "
            "sources, so their score collapses to the damping floor."
        ),
        "algorithm": "pagerank",
        "scope": "org_to_org_projection",
        "provenance": "extracted_from_brd",
    },
    {
        "id": "REQ-003",
        "title": "Thematic Community Detection",
        "description": (
            "Group co-disclosed concepts with Label Propagation over a "
            "concept-type projection. Communities spanning multiple GICS sectors "
            "indicate cross-sector exposure."
        ),
        "algorithm": "label_propagation",
        "scope": "concept_projection",
        "provenance": "extracted_from_brd",
    },
    {
        "id": "REQ-004",
        "title": "Corpus Coherence and Extraction Coverage",
        "description": (
            "Run WCC over the whole graph to determine whether the extracted KG "
            "is one coherent structure or fragmented islands. The "
            "dominant-component share is the trust gate for every other finding."
        ),
        "algorithm": "wcc",
        "scope": "whole_graph",
        "provenance": "extracted_from_brd",
    },
    {
        "id": "REQ-005",
        "title": "Systemic Contagion Chokepoints",
        "description": (
            "Run Betweenness over a curated projection to find entities bridging "
            "otherwise unrelated parts of the disclosed economy. High betweenness "
            "with low salience is the most valuable pattern."
        ),
        "algorithm": "betweenness",
        "scope": "curated_projection",
        "provenance": "extracted_from_brd",
    },
    {
        "id": "REQ-006",
        "title": "Reflexive Dependency Loops",
        "description": (
            "Run SCC over directional dependency and impact edges to find "
            "mutually reachable groups. Components larger than one are feedback "
            "loops or extraction artifacts, separable via chunkKey provenance."
        ),
        "algorithm": "scc",
        "scope": "dependency_projection",
        "provenance": "extracted_from_brd",
    },
    {
        "id": "REQ-007",
        "title": "Disclosure Influence Drift 2014-2024",
        "description": (
            "Run PageRank per year-slice (discriminating on relations.year) and "
            "order concepts by rank movement across the decade."
        ),
        "algorithm": "pagerank",
        "scope": "per_year_slices",
        "provenance": "extracted_from_brd",
    },
]

FINREFLECT_CONSTRAINTS = [
    {
        "id": "CON-001",
        "title": "Read-only analytics",
        "description": (
            "Write algorithm outputs to separate result collections; never "
            "mutate `Node` or `relations`."
        ),
        "provenance": "extracted_from_brd",
    },
    {
        "id": "CON-002",
        "title": "Mandatory type whitelist",
        "description": (
            "`Node.type` has 9,605 distinct values and `relations.type` has "
            "30,535, mostly long-tail near-duplicates. Typed projections must be "
            "constrained to the whitelist in the BRD, or projection "
            "materialisation attempts thousands of collections."
        ),
        "provenance": "extracted_from_brd",
    },
    {
        "id": "CON-003",
        "title": "Exclude source-text chunks",
        "description": (
            "`chunks` holds 1.4M source-text passages and is outside the named "
            "graph. It must never be loaded as a vertex collection; it is for "
            "provenance drill-down only, joined via `relations.chunkKey`."
        ),
        "provenance": "extracted_from_brd",
    },
    {
        "id": "CON-004",
        "title": "Star topology from ORG",
        "description": (
            "Filing companies are ~0.73% of vertices but the source of nearly "
            "every high-volume edge class, so whole-graph PageRank ranks "
            "companies near the bottom. Company ranking requires an explicit "
            "ORG->ORG projection."
        ),
        "provenance": "extracted_from_brd",
    },
    {
        "id": "CON-005",
        "title": "Algorithm execution ordering",
        "description": (
            "Run WCC first (it bounds the others), then PageRank, then Label "
            "Propagation and SCC. Betweenness is the most expensive and runs "
            "last, over a curated projection rather than all 3.1M vertices."
        ),
        "provenance": "extracted_from_brd",
    },
]


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
def workspace_db_handle():
    """Return a python-arango handle to the product metadata database."""

    client = ArangoClient(hosts=os.environ["ARANGO_ENDPOINT"])
    return client.db(
        WORKSPACE_DB,
        username=os.environ["ARANGO_USER"],
        password=os.environ["ARANGO_PASSWORD"],
    )


def purge_prior_seed() -> int:
    """Delete only this workspace's rows, leaving other workspaces intact.

    `seed_adtech_workspace.py` drops the entire `aga_workspace` database to get a
    clean slate. Doing that here would destroy the AdTech demo, so instead we
    scope the delete to our own pinned workspace id.
    """

    db = workspace_db_handle()
    removed = 0
    for coll in WORKSPACE_SCOPED_COLLECTIONS:
        if not db.has_collection(coll):
            continue
        # AQL forbids COLLECT after a data-modification operation, so count
        # via RETURN OLD instead of aggregating.
        cursor = db.aql.execute(
            f"""
            FOR doc IN {coll}
                FILTER doc.workspace_id == @wid
                REMOVE doc IN {coll}
                RETURN OLD._key
            """,
            bind_vars={"wid": FINREFLECT_WORKSPACE_ID},
        )
        removed += len(list(cursor))
    return removed


def now() -> datetime:
    return datetime.now(timezone.utc)


def finreflect_db_handle():
    """Return a python-arango handle to the analysed FinReflect database."""

    client = ArangoClient(hosts=os.environ["ARANGO_ENDPOINT"])
    return client.db(
        FINREFLECT_DATABASE,
        username=os.environ["ARANGO_USER"],
        password=os.environ["ARANGO_PASSWORD"],
    )


def load_workflow_report_index() -> Dict[str, Dict[str, Any]]:
    """Map title -> agent-run report dict (algorithm, metadata.charts, ...)."""

    if not WORKFLOW_STATE_PATH.exists():
        return {}
    state = json.loads(WORKFLOW_STATE_PATH.read_text(encoding="utf-8"))
    index: Dict[str, Dict[str, Any]] = {}
    for rep in state.get("reports", []):
        title = rep.get("title")
        if title:
            index[title] = rep

    exec_by_template: Dict[str, Dict[str, Any]] = {}
    for ex in state.get("execution_results", []):
        name = ex.get("template_name")
        if name:
            exec_by_template[name] = ex
    for title, rep in index.items():
        template_name = title.split(": ", 1)[-1] if ": " in title else title
        rep["_execution"] = exec_by_template.get(template_name)
    return index


def build_graph_view_chart(
    db_finreflect: Any,
    algorithm: str,
    result_collection: Optional[str],
) -> Optional[str]:
    """Build a Plotly HTML graph view for an algorithm result, when relevant."""

    if not result_collection:
        return None
    if not db_finreflect.has_collection(result_collection):
        return None
    if db_finreflect.collection(result_collection).count() == 0:
        return None

    algo = (algorithm or "").lower()
    try:
        if algo in {"pagerank", "betweenness"}:
            return build_pagerank_graph_html(
                db_finreflect,
                result_collection,
                FINREFLECT_EDGE_COLLECTIONS,
                top_n=20,
                title=(
                    "PageRank top-20 entities and 1-hop neighborhood"
                    if algo == "pagerank"
                    else "Betweenness top-20 chokepoints and 1-hop neighborhood"
                ),
            )
        if algo in {"wcc", "scc", "label_propagation"}:
            return build_components_graph_html(
                db_finreflect,
                result_collection,
                FINREFLECT_EDGE_COLLECTIONS,
                top_components=4,
                members_per_component=8,
                field="community" if algo == "label_propagation" else "component",
                title=(
                    "Top connected components"
                    if algo == "wcc"
                    else "Top reflexive dependency loops"
                    if algo == "scc"
                    else "Top disclosure themes"
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
    db_finreflect: Any,
) -> int:
    """Create ChartSpec rows for one report and return the count created."""

    workflow_report = workflow_index.get(title) or {}
    metadata_charts: Dict[str, str] = (
        workflow_report.get("metadata", {}) or {}
    ).get("charts", {}) or {}

    created = 0

    pretty = {
        "top_influencers": "Top entities (PageRank)",
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

    execution = workflow_report.get("_execution") or {}
    algorithm = execution.get("algorithm")
    result_collection = execution.get("result_collection")
    graph_html = build_graph_view_chart(
        db_finreflect=db_finreflect,
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
# Main                                                                        #
# --------------------------------------------------------------------------- #
def main() -> None:
    print("=" * 70)
    print("SEEDING FINREFLECTKG WORKSPACE INTO PRODUCT API")
    print("=" * 70)

    if not REQUIREMENTS_DOC.exists():
        raise SystemExit(f"Requirements doc not found: {REQUIREMENTS_DOC}")

    # Fail fast if the target database was never restored.
    db_finreflect = finreflect_db_handle()
    graphs = {g["name"] for g in db_finreflect.graphs()}
    if FINREFLECT_GRAPH not in graphs:
        raise SystemExit(
            f"Named graph {FINREFLECT_GRAPH!r} not found in {FINREFLECT_DATABASE}. "
            f"Present: {sorted(graphs) or '(none)'}. "
            "Run scripts/restore_finreflect_dumps.sh first."
        )

    removed = purge_prior_seed()
    print(
        f"Purged {removed} prior row(s) for {FINREFLECT_WORKSPACE_ID} "
        f"(other workspaces untouched)"
    )

    service = create_product_service()
    print("Product service ready (backed by aga_workspace)")

    # ---- 1. Workspace (pinned ID so the URL stays stable) ---------------- #
    workspace = Workspace(
        workspace_id=FINREFLECT_WORKSPACE_ID,
        customer_name="FinReflectKG Demo",
        project_name="Corporate Disclosure Intelligence",
        environment="prod",
        description=(
            "Aggregate intelligence over S&P 500 10-K disclosure (FY2014-2024) "
            f"against {FINREFLECT_DATABASE} / {FINREFLECT_GRAPH}."
        ),
        tags=["finreflect", "sec-filings", "corporate-disclosure", "systemic-risk"],
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
        name=f"{FINREFLECT_DATABASE.lower()}-prod-demo",
        deployment_mode=DeploymentMode.SELF_MANAGED,
        endpoint=FINREFLECT_ENDPOINT,
        database=FINREFLECT_DATABASE,
        username=FINREFLECT_USER,
        verify_ssl=True,
        secret_refs={"password": {"kind": "env", "ref": "ARANGO_PASSWORD"}},
        metadata={"description": f"{FINREFLECT_DATABASE} on prod demo pilot"},
    )
    print(
        f"Connection profile: {profile.connection_profile_id}  "
        f"-> {FINREFLECT_DATABASE}"
    )

    # ---- 3. Verify the connection ---------------------------------------- #
    verification = service.verify_connection_profile(profile.connection_profile_id)
    print(f"Verification: {verification.status}")

    # ---- 4. Discover the named graph ------------------------------------- #
    discovery = service.discover_graph_profile(
        connection_profile_id=profile.connection_profile_id,
        graph_name=FINREFLECT_GRAPH,
        created_by="seed-script",
    )
    graph_profile_id = discovery.graph_profile["graph_profile_id"]
    vertex_count = len(discovery.graph_profile.get("vertex_collections", []))
    edge_count = len(discovery.graph_profile.get("edge_collections", []))
    print(
        f"Graph profile: {graph_profile_id}  "
        f"({vertex_count} vertex / {edge_count} edge collections)"
    )

    # ---- 4b. Discover database-scope `default` profile (FR-67b) ---------- #
    default_discovery = service.discover_graph_profile(
        connection_profile_id=profile.connection_profile_id,
        force_database_scope=True,
        created_by="seed-script",
    )
    default_profile_id = default_discovery.graph_profile["graph_profile_id"]
    print(
        f"Default graph profile: {default_profile_id}  "
        f"({len(default_discovery.graph_profile.get('vertex_collections', []))} "
        f"vertex / "
        f"{len(default_discovery.graph_profile.get('edge_collections', []))} edge)"
    )

    # ---- 4c. Pin the named graph as active (FR-67b) ---------------------- #
    service.set_active_graph_profile(
        workspace_id=workspace.workspace_id,
        graph_profile_id=graph_profile_id,
        actor="seed-script",
    )
    print(f"Active graph profile pinned: {graph_profile_id} ({FINREFLECT_GRAPH})")

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

    # ---- 5b. Approved requirement version -------------------------------- #
    requirement_version = create_requirement_version(
        workspace_id=workspace.workspace_id,
        version=1,
        status=RequirementVersionStatus.APPROVED,
        document_ids=[document.document_id],
        summary=FINREFLECT_REQUIREMENTS_SUMMARY,
        objectives=FINREFLECT_OBJECTIVES,
        requirements=FINREFLECT_REQUIREMENTS,
        constraints=FINREFLECT_CONSTRAINTS,
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

    # ---- 6. Workflow run -------------------------------------------------- #
    base_time = now()
    workflow_steps: List[WorkflowStep] = []
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
            "source": "scripts/run_finreflect_demo.py",
            "reports_dir": str(REPORTS_DIR),
            "database": FINREFLECT_DATABASE,
        },
    )
    run.status = WorkflowRunStatus.COMPLETED
    run.started_at = base_time
    run.completed_at = base_time
    # FR-31a: agentic runs substitute the canonical six-step DAG, created
    # `pending`. Stamp those too, or the visualizer shows a finished run whose
    # every step still reads "pending". Canonical order matches the plan 1:1.
    for offset, step in enumerate(run.steps):
        step.status = WorkflowStepStatus.COMPLETED
        step.started_at = base_time
        step.completed_at = base_time
        step.duration_ms = 2_000
        if offset < len(WORKFLOW_STEP_PLAN):
            step.agent_name = WORKFLOW_STEP_PLAN[offset][2]
        step.metadata = {**(step.metadata or {}), "index": offset}
    service.repository.update_workflow_run(run)
    print(f"Workflow run: {run.run_id}  ({len(workflow_steps)} steps, completed)")

    # ---- 7. Reports ------------------------------------------------------- #
    if not REPORTS_DIR.exists():
        print(f"WARNING: {REPORTS_DIR} not found; skipping report ingestion")
        return

    report_files = sorted(REPORTS_DIR.glob("report_*.md"))
    if not report_files:
        print(f"WARNING: no markdown reports found in {REPORTS_DIR}")
        return

    workflow_reports_by_title = load_workflow_report_index()

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
            db_finreflect=db_finreflect,
        )

        print(
            f"  Report: {manifest.report_id}  '{title}' "
            f"({len(sections)} sections, {chart_count} charts)"
        )

    # ---- 8. Print URL ----------------------------------------------------- #
    url = f"http://localhost:3000/workspace?workspaceId={workspace.workspace_id}"
    print()
    print("=" * 70)
    print("DONE. Open the workspace UI at:")
    print(f"  {url}")
    print("=" * 70)


if __name__ == "__main__":
    main()
