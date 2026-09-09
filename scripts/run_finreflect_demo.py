#!/usr/bin/env python3
"""
FinReflectKG - Agentic Demo Runner

Runs the agentic workflow against the FinReflectKG corporate-disclosure knowledge
graph (S&P 500 10-K filings, FY2014-2024) and generates markdown + interactive
HTML reports under ``workflow_output/finreflect_demo/``.

The FinReflect graph differs structurally from the AdTech demo in two ways that
this script has to account for:

1. It is a single-vertex / single-edge labeled property graph. There is one
   ``Node`` collection and one ``relations`` collection; the semantics live in
   their ``type`` properties. So ``CORE_COLLECTIONS`` is just ``["Node"]`` and
   there are no satellite collections to exclude -- the core/satellite split that
   shapes the AdTech run has nothing to bite on here. Type-level differentiation
   is handled downstream by FR-74 typed LPG projections.

2. The topology is a star radiating from ``ORG``: filing companies are ~0.73% of
   vertices but the source of nearly every high-volume edge class. Whole-graph
   PageRank therefore ranks concepts correctly and companies near the bottom.
   The reporting vertical (``corporate_disclosure``) is primed for this so the
   LLM does not misread out-degree as importance.

Reads connection settings from the project ``.env``, overriding the database:
    ARANGO_ENDPOINT=https://prod.demo.pilot.arango.ai
    ARANGO_USER=root
    ARANGO_PASSWORD=...

Run with:
    python scripts/run_finreflect_demo.py                    # FinReflectKgTemporal
    FINREFLECT_DB=FinReflectKgOneShard python scripts/run_finreflect_demo.py
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

# Target database. Defaults to the temporal build, which additionally carries
# pre-computed per-year PageRank (`gae_pr_<year>`) and time-travel snapshots
# (`tt_snap_<year>`) supporting the influence-drift use case (BRD section 7).
TARGET_DB = os.environ.get("FINREFLECT_DB", "FinReflectKgTemporal")
os.environ["ARANGO_DATABASE"] = TARGET_DB

from graph_analytics_ai.ai.agents.runner import AgenticWorkflowRunner
from graph_analytics_ai.ai.agents.constants import AgentDefaults, AgentNames
from graph_analytics_ai.ai.agents.specialized import ReportingAgent
from graph_analytics_ai.db_connection import get_db_connection


# ---------------------------------------------------------------------------
# Graph configuration
# ---------------------------------------------------------------------------
# Named graph differs per build; both define `relations` from [Node] to [Node].
GRAPH_BY_DB = {
    "FinReflectKgTemporal": "FinReflectKgTemporal",
    "FinReflectKgOneShard": "FinReflectKG",
}

# Single-vertex LPG: the one business entity collection.
CORE_COLLECTIONS = ["Node"]

# Nothing to exclude -- there is no separate reference/metadata vertex
# collection. `chunks` (source text) and the `gae_pr_*` / `tt_snap_*` result
# collections are deliberately outside the named graph and must not be loaded
# as vertices.
SATELLITE_COLLECTIONS: list = []

# Not part of the named graph; listed so the intent is explicit and greppable.
EXCLUDED_COLLECTIONS = [
    "chunks",           # 1.4M source-text passages, joined via relations.chunkKey
    "bnodes",
    "arango_cypher_schema_cache",
]

REQUIREMENTS_FILE = REPO_ROOT / "docs" / "FinReflectKG_business_requirements.md"


def configure_reporting_quality() -> None:
    """Tune the reporting agent for disclosure-analysis-grade insights."""
    os.environ.setdefault("GAE_PLATFORM_REPORTING_MIN_CONFIDENCE", "0.2")
    os.environ.setdefault("GAE_PLATFORM_REPORTING_USE_REASONING", "true")
    os.environ.setdefault("GAE_PLATFORM_MAX_LLM_INSIGHTS_PER_REPORT", "5")
    os.environ.setdefault("GAE_PLATFORM_USE_LLM_REPORTING", "true")


def main() -> None:
    print("=" * 70)
    print("FINREFLECTKG CORPORATE DISCLOSURE - AGENTIC DEMO")
    print("=" * 70)

    configure_reporting_quality()

    if not REQUIREMENTS_FILE.exists():
        raise SystemExit(f"Requirements file not found: {REQUIREMENTS_FILE}")

    graph_name = GRAPH_BY_DB.get(TARGET_DB)
    if graph_name is None:
        raise SystemExit(
            f"No named graph mapping for database '{TARGET_DB}'. "
            f"Known: {', '.join(sorted(GRAPH_BY_DB))}"
        )

    output_dir = REPO_ROOT / "workflow_output" / "finreflect_demo"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nDatabase:      {TARGET_DB}")
    print(f"Endpoint:      {os.getenv('ARANGO_ENDPOINT')}")
    print(f"Graph:         {graph_name}")
    print(f"Requirements:  {REQUIREMENTS_FILE}")
    print(f"Output:        {output_dir}")
    print(f"Core:          {', '.join(CORE_COLLECTIONS)}")
    print(f"Excluded:      {', '.join(EXCLUDED_COLLECTIONS)}")

    db = get_db_connection()
    print(f"Connected to:  {db.name} ({len(db.collections())} collections)")

    # Fail loudly rather than running a workflow against a graph that is not
    # there -- both target databases were empty shells until restored.
    graphs = {g["name"] for g in db.graphs()}
    if graph_name not in graphs:
        raise SystemExit(
            f"Named graph '{graph_name}' not found in {db.name}. "
            f"Present: {sorted(graphs) or '(none)'}. "
            "Run scripts/restore_finreflect_dumps.sh first."
        )
    for coll in CORE_COLLECTIONS:
        count = db.collection(coll).count()
        print(f"  {coll}: {count:,} documents")
        if count == 0:
            raise SystemExit(f"Collection '{coll}' is empty -- restore incomplete.")
    print(f"  relations: {db.collection('relations').count():,} documents")

    AgentDefaults.MAX_EXECUTIONS = 10

    runner = AgenticWorkflowRunner(
        db_connection=db,
        graph_name=graph_name,
        core_collections=CORE_COLLECTIONS,
        satellite_collections=SATELLITE_COLLECTIONS,
    )

    # `fintech` would be the obvious vertical but it is written for payments and
    # transaction networks (accounts, money mules, AML) -- none of which exist
    # here. `corporate_disclosure` is primed for the ORG-star topology and the
    # extraction-quality dimension instead.
    runner.agents[AgentNames.REPORTING_SPECIALIST] = ReportingAgent(
        llm_provider=runner.llm_provider,
        trace_collector=runner.trace_collector,
        industry="corporate_disclosure",
    )
    runner.orchestrator.agents = runner.agents

    print("\nRunning agentic workflow (schema -> requirements -> use cases ->")
    print("templates -> GAE execution -> LLM reporting)...\n")

    final_state = asyncio.run(
        runner.run_async(
            input_documents=[str(REQUIREMENTS_FILE)],
            max_executions=10,
            enable_parallelism=True,
        )
    )

    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
    print(f"Current step:    {final_state.current_step}")
    print(f"Completed:       {', '.join(final_state.completed_steps)}")
    print(f"Executions:      {len(final_state.execution_results)}")
    print(f"Reports:         {len(final_state.reports)}")
    print(f"Errors:          {len(final_state.errors)}")

    state_file = output_dir / "workflow_state.json"
    runner.export_state(final_state, str(state_file))
    print(f"State saved:     {state_file}")

    md_dir = output_dir / "markdown_reports"
    md_dir.mkdir(parents=True, exist_ok=True)
    runner.export_reports(final_state, str(md_dir))
    print(f"Markdown:        {md_dir}")

    try:
        from graph_analytics_ai.ai.reporting import HTMLReportFormatter

        html_dir = output_dir / "html_reports"
        html_dir.mkdir(parents=True, exist_ok=True)
        html_formatter = HTMLReportFormatter()

        for i, report in enumerate(final_state.reports, 1):
            charts = report.metadata.get("charts", {})
            html_content = html_formatter.format_report(report, charts=charts)
            slug = report.title.replace(" ", "_").replace("/", "_").lower()
            (html_dir / f"report_{i:02d}_{slug}.html").write_text(
                html_content, encoding="utf-8"
            )
        print(f"HTML reports:    {html_dir}")
    except ImportError:
        print("HTML reports:    skipped (install plotly to enable)")

    if final_state.reports:
        print("\nGenerated reports:")
        for i, r in enumerate(final_state.reports, 1):
            print(f"  {i:2d}. {r.title}  "
                  f"(insights={len(r.insights)}, "
                  f"recs={len(r.recommendations)})")


if __name__ == "__main__":
    main()
