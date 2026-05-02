#!/usr/bin/env python3
"""
AdTech Knowledge Graph - Agentic Demo Runner

Runs the agentic workflow against the `addtech-knowledge-graph` database
using the generic AdTech business requirements document. Generates
markdown + interactive HTML reports under `workflow_output/adtech_demo/`.

Reads connection settings from the project `.env`:
    ARANGO_DATABASE=addtech-knowledge-graph
    ARANGO_ENDPOINT=https://prod.demo.pilot.arango.ai
    ARANGO_USER=root
    ARANGO_PASSWORD=...
    GAE_DEPLOYMENT_MODE=self_managed

Run with:
    python scripts/run_adtech_demo.py
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the repo root regardless of cwd.
REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

from graph_analytics_ai.ai.agents.runner import AgenticWorkflowRunner
from graph_analytics_ai.ai.agents.constants import AgentDefaults, AgentNames
from graph_analytics_ai.ai.agents.specialized import ReportingAgent
from graph_analytics_ai.db_connection import get_db_connection


# ---------------------------------------------------------------------------
# Graph configuration for the AdTech demo
# ---------------------------------------------------------------------------
# Discovered via `db.graphs()` on `addtech-knowledge-graph`.
GRAPH_NAME = "AdtechGraph"

# Primary business entities. WCC / Label Propagation / SCC focus on these.
CORE_COLLECTIONS = [
    "Device",        # Connected TV / mobile / tablet devices
    "IP",            # IP addresses (candidate household anchors)
    "AppProduct",    # Streaming apps / OTT products (inventory)
    "Site",          # Sites / domains (inventory)
    "InstalledApp",  # Behavioral: device <-> app usage
    "SiteUse",       # Behavioral: device <-> site visits
]

# Reference / metadata collections. Excluded from clustering (WCC/SCC/LPA),
# included for ranking algorithms (PageRank / Betweenness).
SATELLITE_COLLECTIONS = [
    "Location",   # Geographic reference data (connects everything)
    "Publisher",  # Publisher metadata
    "Exchange",   # Exchange reference data
]


def configure_reporting_quality() -> None:
    """Tune the reporting agent for ad-tech-grade insights."""
    os.environ.setdefault("GAE_PLATFORM_REPORTING_MIN_CONFIDENCE", "0.2")
    os.environ.setdefault("GAE_PLATFORM_REPORTING_USE_REASONING", "true")
    os.environ.setdefault("GAE_PLATFORM_MAX_LLM_INSIGHTS_PER_REPORT", "5")
    os.environ.setdefault("GAE_PLATFORM_USE_LLM_REPORTING", "true")


def main() -> None:
    print("=" * 70)
    print("ADTECH KNOWLEDGE GRAPH - AGENTIC DEMO")
    print("=" * 70)

    configure_reporting_quality()

    requirements_file = Path(
        "/Users/arthurkeen/code/premion-graph-analytics/docs/AdTech_business_requirements.md"
    )
    if not requirements_file.exists():
        raise SystemExit(f"Requirements file not found: {requirements_file}")

    output_dir = REPO_ROOT / "workflow_output" / "adtech_demo"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nDatabase:      {os.getenv('ARANGO_DATABASE')}")
    print(f"Endpoint:      {os.getenv('ARANGO_ENDPOINT')}")
    print(f"Graph:         {GRAPH_NAME}")
    print(f"Requirements:  {requirements_file}")
    print(f"Output:        {output_dir}")
    print(f"Core:          {', '.join(CORE_COLLECTIONS)}")
    print(f"Satellite:     {', '.join(SATELLITE_COLLECTIONS)}")

    db = get_db_connection()
    print(f"Connected to:  {db.name} ({len(db.collections())} collections)")

    AgentDefaults.MAX_EXECUTIONS = 10

    runner = AgenticWorkflowRunner(
        db_connection=db,
        graph_name=GRAPH_NAME,
        core_collections=CORE_COLLECTIONS,
        satellite_collections=SATELLITE_COLLECTIONS,
    )

    runner.agents[AgentNames.REPORTING_SPECIALIST] = ReportingAgent(
        llm_provider=runner.llm_provider,
        trace_collector=runner.trace_collector,
        industry="adtech",
    )
    runner.orchestrator.agents = runner.agents

    print("\nRunning agentic workflow (schema -> requirements -> use cases ->")
    print("templates -> GAE execution -> LLM reporting)...\n")

    final_state = asyncio.run(
        runner.run_async(
            input_documents=[str(requirements_file)],
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
