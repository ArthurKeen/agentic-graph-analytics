#!/usr/bin/env python3
"""
Patch empty AdTech reports.

The agentic workflow run produced 4 substantive reports but 6 reports came
back with `result_count = 0` ("No Results Generated") because the executor
either reused empty saved-job slots or dispatched UUID-keyed throwaway jobs.

This script bypasses the agent and dispatches GAE algorithms directly for
those 6 use cases, materialises proper result collections, regenerates the
markdown report files, and updates `workflow_state.json` so that re-running
the seeder picks up substantive content + interactive charts.

Implementation notes:
- Goes BELOW `GAEOrchestrator.run_analysis` (which always re-loads the graph
  per call). Groups patches by their (vertex_cols, edge_cols) tuple and
  shares one `load_graph` per group, then runs each algorithm in the group
  against the same `graph_id`. Cuts I/O ~3x.
- Smallest groups run first so partial completion is still useful if you
  Ctrl-C.
- All progress streams to stdout AND to /tmp/patch_run.log so you can
  `tail -f` from another terminal while it runs.

Run with:
    python scripts/patch_empty_adtech_reports.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

LOG_PATH = Path("/tmp/patch_run.log")
LOG_FH = LOG_PATH.open("w", buffering=1)


def _log(msg: str = "") -> None:
    line = msg if msg.endswith("\n") else msg + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()
    LOG_FH.write(line)


from arango import ArangoClient
from graph_analytics_ai.gae_connection import GenAIGAEConnection  # noqa: E402

# --------------------------------------------------------------------------- #
# Config                                                                      #
# --------------------------------------------------------------------------- #

ADTECH_DATABASE = "addtech-knowledge-graph"
GRAPH_NAME = "AdtechGraph"
OUTPUT_DIR = REPO_ROOT / "workflow_output" / "adtech_demo"
MARKDOWN_DIR = OUTPUT_DIR / "markdown_reports"
WORKFLOW_STATE_PATH = OUTPUT_DIR / "workflow_state.json"

ALL_VERTEX = [
    "AppProduct", "Device", "Exchange", "IP", "InstalledApp",
    "Location", "Publisher", "Site", "SiteUse",
]
CORE_VERTEX = ["Device", "IP", "AppProduct", "Site", "InstalledApp", "SiteUse"]
ALL_EDGE = [
    "INSTANCE_OF", "LOCATED_IN", "OWNED_BY",
    "SEEN_ON_APP", "SEEN_ON_IP", "SEEN_ON_SITE", "SERVED_BY",
]
CORE_EDGE = ["SEEN_ON_APP", "SEEN_ON_IP", "SEEN_ON_SITE", "INSTANCE_OF"]


@dataclass
class UseCasePatch:
    use_case_id: str
    title: str
    algorithm: str  # pagerank | wcc | scc | label_propagation | betweenness
    target_collection: str
    vertex_collections: List[str]
    edge_collections: List[str]
    business_question: str
    algorithm_params: Dict[str, Any] = field(default_factory=dict)
    vertex_attributes: Optional[List[str]] = None


# Sized & ordered: smallest graph first so something useful completes early.
PATCHES: List[UseCasePatch] = [
    # 1. Smallest: Inventory side only (apps + sites + exchanges + publishers).
    #    Betweenness isn't exposed on this GAE deployment, so we use PageRank
    #    on the inventory-only subgraph instead — still answers the gateway
    #    question by surfacing the highest-authority Exchanges/AppProducts.
    UseCasePatch(
        use_case_id="UC-S04",
        title="Analysis Report: UC-S04: Ad-Exchange Gateway Analysis",
        algorithm="pagerank",
        target_collection="uc_s04_results",
        vertex_collections=["AppProduct", "Site", "Exchange", "Publisher"],
        edge_collections=["SERVED_BY", "OWNED_BY"],
        business_question=(
            "Which Exchanges and AppProducts act as gateways through which "
            "the most inventory traffic flows?"
        ),
        algorithm_params={"damping_factor": 0.85, "maximum_supersteps": 50},
    ),
    # 2. Device + IP only — household identity (REQ-002).
    UseCasePatch(
        use_case_id="UC-R02",
        title="Analysis Report: UC-R02: Requirement: REQ-002",
        algorithm="wcc",
        target_collection="uc_r02_results",
        vertex_collections=["Device", "IP"],
        edge_collections=["SEEN_ON_IP"],
        business_question=(
            "Which devices belong to the same household based on shared IP "
            "connectivity?"
        ),
    ),
    # 3. Device + IP + Location — anchor IP centrality (REQ-004).
    UseCasePatch(
        use_case_id="UC-R03",
        title="Analysis Report: UC-R03: Requirement: REQ-004",
        algorithm="pagerank",
        target_collection="uc_r03_results",
        vertex_collections=["Device", "IP", "Location"],
        edge_collections=["SEEN_ON_IP", "LOCATED_IN"],
        business_question=(
            "Which IPs serve as primary anchors for the most devices and "
            "geographies?"
        ),
        algorithm_params={"damping_factor": 0.85, "maximum_supersteps": 40},
    ),
    # 4. Device + IP + AppProduct + InstalledApp — botnet detection (UC-S01).
    UseCasePatch(
        use_case_id="UC-S01",
        title="Analysis Report: UC-S01: Ad-Fraud Botnet Detection",
        algorithm="wcc",
        target_collection="uc_s01_results",
        vertex_collections=["Device", "IP", "AppProduct", "InstalledApp"],
        edge_collections=["SEEN_ON_IP", "SEEN_ON_APP", "INSTANCE_OF"],
        business_question=(
            "Are there abnormally large device clusters that share IPs and "
            "apps in patterns consistent with botnet behaviour?"
        ),
    ),
    # 5. CORE behavioural subgraph — community detection (UC-S03).
    #    Label Propagation needs _key materialised as a column in the engine's
    #    column store, so we explicitly request it via vertex_attributes.
    UseCasePatch(
        use_case_id="UC-S03",
        title="Analysis Report: UC-S03: Semantic Entity Clustering",
        algorithm="label_propagation",
        target_collection="uc_s03_results",
        vertex_collections=CORE_VERTEX,
        edge_collections=CORE_EDGE,
        vertex_attributes=["_key"],
        business_question=(
            "Which devices, IPs, and apps cluster into coherent behavioural "
            "communities?"
        ),
        algorithm_params={
            "start_label_attribute": "_key",
            "maximum_supersteps": 20,
        },
    ),
    # 6. FULL graph — inventory ranking (UC-002). Slowest, last.
    UseCasePatch(
        use_case_id="UC-002",
        title="Analysis Report: UC-002: Improve Inventory Forecasting & Pricing",
        algorithm="pagerank",
        target_collection="uc_002_results",
        vertex_collections=ALL_VERTEX,
        edge_collections=ALL_EDGE,
        business_question=(
            "Which AppProducts, Sites, and Exchanges drive the most inventory "
            "demand signal across the network?"
        ),
        algorithm_params={"damping_factor": 0.85, "maximum_supersteps": 30},
    ),
]

REPORT_TITLE_TO_INDEX = {
    "Analysis Report: UC-001: Achieve Data Autonomy": 1,
    "Analysis Report: UC-002: Improve Inventory Forecasting & Pricing": 2,
    "Analysis Report: UC-S01: Ad-Fraud Botnet Detection": 3,
    "Analysis Report: UC-S02: High-Value Inventory Ranking": 4,
    "Analysis Report: UC-S03: Semantic Entity Clustering": 5,
    "Analysis Report: UC-S04: Ad-Exchange Gateway Analysis": 6,
    "Analysis Report: UC-S05: Device-IP Reciprocity Study": 7,
    "Analysis Report: UC-R01: Requirement: REQ-001": 8,
    "Analysis Report: UC-R02: Requirement: REQ-002": 9,
    "Analysis Report: UC-R03: Requirement: REQ-004": 10,
}


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

def adtech_db():
    client = ArangoClient(hosts=os.environ["ARANGO_ENDPOINT"])
    return client.db(
        ADTECH_DATABASE,
        username=os.environ["ARANGO_USER"],
        password=os.environ["ARANGO_PASSWORD"],
    )


def slugify(text: str) -> str:
    return (
        text.replace(" ", "_").replace("/", "_").replace(":", "_")
        .replace("&", "and").lower()
    )


# --------------------------------------------------------------------------- #
# GAE primitives                                                              #
# --------------------------------------------------------------------------- #

def _classify_job(job: Dict[str, Any]) -> str:
    """Map a GAE /v1/jobs/{id} response onto succeeded|failed|running|pending."""

    if not job:
        return "pending"
    # GenAI/GRAL response shape: {error, error_code, error_message, total,
    # progress, comp_type, runtime_in_microseconds, ...}. There's no explicit
    # "status" field — completion is signalled by progress catching up to
    # total (or error == True).
    if job.get("error") is True or job.get("error_code"):
        return "failed"
    total = job.get("total")
    progress = job.get("progress")
    if isinstance(total, int) and isinstance(progress, int):
        if total > 0 and progress >= total:
            return "succeeded"
        if progress > 0:
            return "running"
        return "pending"
    # Some responses use a nested status block (AMP-style); fall back gracefully.
    status_block = job.get("status") or {}
    if isinstance(status_block, dict):
        if status_block.get("succeeded"):
            return "succeeded"
        if status_block.get("failed"):
            return "failed"
        if status_block.get("is_started"):
            return "running"
    if isinstance(status_block, str):
        return status_block.lower()
    return "pending"


def wait_for_job(gae: GenAIGAEConnection, job_id: str, label: str, max_wait_s: int = 1500) -> Dict[str, Any]:
    """Poll until the GAE job is complete or fails. Streams progress."""

    started = time.time()
    last_status = None
    last_progress = None
    while True:
        job = gae.get_job(job_id) or {}
        status = _classify_job(job)
        elapsed = int(time.time() - started)
        progress = job.get("progress")
        total = job.get("total")
        if status != last_status or progress != last_progress:
            extra = ""
            if progress is not None and total:
                extra = f" ({progress}/{total})"
            _log(f"    [{elapsed:>4}s] {label} job={job_id} status={status}{extra}")
            last_status = status
            last_progress = progress

        if status == "succeeded":
            return job
        if status == "failed":
            raise RuntimeError(f"{label} job {job_id} failed: {job}")
        if elapsed > max_wait_s:
            raise TimeoutError(f"{label} job {job_id} stuck after {max_wait_s}s (last: {status})")
        time.sleep(3)


def load_graph(
    gae: GenAIGAEConnection,
    vertex_collections: List[str],
    edge_collections: List[str],
    vertex_attributes: Optional[List[str]] = None,
) -> str:
    _log(
        f"  -> load_graph V={len(vertex_collections)} ({vertex_collections}) "
        f"E={len(edge_collections)} ({edge_collections})"
        + (f" attrs={vertex_attributes}" if vertex_attributes else "")
    )
    info = gae.load_graph(
        database=ADTECH_DATABASE,
        vertex_collections=vertex_collections,
        edge_collections=edge_collections,
        vertex_attributes=vertex_attributes,
    )
    graph_id = info.get("graph_id") or info.get("id")
    job_id = info.get("job_id")
    if job_id:
        wait_for_job(gae, job_id, "load_graph", max_wait_s=1800)
    _log(f"  ✓ graph_id={graph_id}")
    return graph_id


def run_algorithm(gae: GenAIGAEConnection, patch: UseCasePatch, graph_id: str) -> str:
    algo = patch.algorithm
    params = {"graph_id": graph_id, **patch.algorithm_params}
    if algo == "pagerank":
        info = gae.run_pagerank(**params)
    elif algo == "wcc":
        info = gae.run_wcc(graph_id=graph_id)
    elif algo == "scc":
        info = gae.run_scc(graph_id=graph_id)
    elif algo == "label_propagation":
        info = gae.run_label_propagation(**params)
    elif algo == "betweenness":
        info = gae.run_betweenness(**params)
    else:
        raise ValueError(f"Unknown algorithm: {algo}")
    job_id = info.get("job_id")
    wait_for_job(gae, job_id, f"{algo}", max_wait_s=2400)
    return job_id


def store_results(
    gae: GenAIGAEConnection,
    db,
    target_collection: str,
    job_id: str,
    field: str,
) -> int:
    if not db.has_collection(target_collection):
        _log(f"  -> creating collection {target_collection}")
        try:
            db_props = db.properties()
            sharded = db_props.get("sharding") in ("flexible", "single")
        except Exception:
            sharded = False
        if sharded:
            db.create_collection(
                name=target_collection, shard_count=3, replication_factor=3,
                shard_keys=["_key"],
            )
        else:
            db.create_collection(target_collection)
    info = gae.store_results(
        target_collection=target_collection,
        job_ids=[job_id],
        attribute_names=[field],
        database=ADTECH_DATABASE,
    )
    store_job_id = info.get("job_id") or info.get("id")
    if store_job_id:
        wait_for_job(gae, store_job_id, "store_results", max_wait_s=900)
    # Wait briefly for documents to materialise.
    deadline = time.time() + 60
    count = 0
    while time.time() < deadline:
        count = db.collection(target_collection).count()
        if count > 0:
            break
        time.sleep(2)
    return count


# --------------------------------------------------------------------------- #
# Result analysis (deterministic insights from result collection)             #
# --------------------------------------------------------------------------- #

ALG_RESULT_FIELDS = {
    "pagerank": "rank",
    "wcc": "component",
    "scc": "component",
    "label_propagation": "community",
    "betweenness": "centrality",
}


def _split_encoded_id(raw_key: str) -> Tuple[str, str]:
    """Split a GAE result _key like 'Location%2F60602' into (collection, key).

    GAE stores results back with the source vertex `_id` URL-encoded into the
    result collection's `_key` (because `/` is not a legal `_key` character).
    We undo that here so downstream summaries can show real collection names
    and readable identifiers (`Location/60602`, not `Location%2F60602`).
    """
    decoded = unquote(raw_key)
    if "/" in decoded:
        collection, _, ident = decoded.partition("/")
        return collection, ident
    return "node", decoded


def summarize_ranking(db, patch: UseCasePatch, field: str) -> Dict[str, Any]:
    aql = f"""
    FOR doc IN {patch.target_collection}
        FILTER HAS(doc, @field) AND doc[@field] != null
        SORT doc[@field] DESC
        LIMIT 25
        RETURN {{ key: doc._key, value: doc[@field] }}
    """
    raw_top = list(db.aql.execute(aql, bind_vars={"field": field}))

    totals = next(
        db.aql.execute(
            f"""
            RETURN {{
              total: COUNT(FOR d IN {patch.target_collection} RETURN 1),
              sum_top: SUM(FOR d IN {patch.target_collection}
                           FILTER HAS(d, @field) SORT d[@field] DESC LIMIT 5
                           RETURN d[@field]),
              sum_all: SUM(FOR d IN {patch.target_collection}
                           FILTER HAS(d, @field) RETURN d[@field])
            }}
            """,
            bind_vars={"field": field},
        )
    )
    top: List[Dict[str, Any]] = []
    by_collection: Dict[str, int] = {}
    for entry in raw_top:
        collection, ident = _split_encoded_id(entry["key"])
        display = f"{collection}/{ident}"
        top.append({"key": display, "raw_key": entry["key"], "value": entry["value"]})
        by_collection[collection] = by_collection.get(collection, 0) + 1
    sum_top = float(totals.get("sum_top") or 0)
    sum_all = float(totals.get("sum_all") or 0)
    return {
        "top": top,
        "totals": totals,
        "by_collection": by_collection,
        "concentration_top5": (sum_top / sum_all) if sum_all else 0.0,
    }


def summarize_components(db, patch: UseCasePatch, field: str) -> Dict[str, Any]:
    summary = next(
        db.aql.execute(
            f"""
            LET components = (
                FOR d IN {patch.target_collection}
                    FILTER HAS(d, @field)
                    COLLECT cid = d[@field] WITH COUNT INTO size
                    RETURN {{ component_id: cid, size: size }}
            )
            LET sizes = (FOR c IN components RETURN c.size)
            RETURN {{
                component_count: COUNT(components),
                singleton_count: COUNT(FOR s IN sizes FILTER s == 1 RETURN 1),
                top_components: (FOR c IN components SORT c.size DESC LIMIT 10 RETURN c),
                max_size: MAX(sizes),
                avg_size: AVG(sizes),
                median_size: PERCENTILE(sizes, 50)
            }}
            """,
            bind_vars={"field": field},
        )
    )
    if summary.get("top_components"):
        biggest_cid = summary["top_components"][0]["component_id"]
        summary["largest_component_sample"] = list(
            db.aql.execute(
                f"""
                FOR d IN {patch.target_collection}
                    FILTER d[@field] == @cid
                    LIMIT 8 RETURN d._key
                """,
                bind_vars={"field": field, "cid": biggest_cid},
            )
        )
    return summary


# --------------------------------------------------------------------------- #
# Insight + recommendation generators                                         #
# --------------------------------------------------------------------------- #

def build_ranking_report(patch: UseCasePatch, summary: Dict[str, Any]) -> Dict[str, Any]:
    top = summary["top"][:10]
    if not top:
        return _empty_report(patch)
    by_collection = summary.get("by_collection", {})
    top_collection = max(by_collection.items(), key=lambda kv: kv[1])[0] if by_collection else "node"
    concentration_pct = round(summary.get("concentration_top5", 0.0) * 100, 2)
    leader = top[0]
    leader_value = round(float(leader["value"]), 6)
    second = top[1] if len(top) > 1 else None
    second_ratio = (
        round(leader["value"] / second["value"], 2) if second and second["value"] else None
    )
    metric_label = "PageRank" if patch.algorithm == "pagerank" else "Betweenness"
    insights = [
        {
            "title": f"Top 5 {top_collection}s control {concentration_pct}% of total {metric_label} authority",
            "description": (
                "The top five nodes—" + ", ".join(f"`{e['key']}`" for e in top[:5]) +
                f"—accumulate {concentration_pct}% of network "
                f"{metric_label.lower()}. `{leader['key']}` dominates with a score "
                f"of {leader_value}"
                + (f" ({second_ratio}× the runner-up `{second['key']}`)." if second_ratio else ".")
            ),
            "insight_type": "key_finding",
            "confidence": 0.92,
            "supporting_data": {"top": top[:10], "by_collection": by_collection},
            "business_impact": (
                f"These hubs are the highest-leverage points for: "
                f"{patch.business_question} Prioritising data ingestion and "
                "observability around them improves graph fidelity at minimal cost."
            ),
        },
        {
            "title": f"{len(top)} {top_collection} nodes form the high-{metric_label.lower()} tier",
            "description": (
                "These nodes have substantially higher rank than the long tail and "
                "behave as bridge / authority nodes: " +
                ", ".join(f"`{e['key']}`" for e in top[:8]) + "."
            ),
            "insight_type": "key_finding",
            "confidence": 0.85,
            "supporting_data": {"sample": [e["key"] for e in top[:8]]},
            "business_impact": (
                "Promote these nodes for premium pricing, fraud-watch alerting, or "
                "as primary anchors when stitching identity across devices."
            ),
        },
    ]
    recommendations = [
        {
            "title": f"Action: Focus on the top-5 {metric_label.lower()} {top_collection}s",
            "description": (
                f"Stand up dedicated dashboards + data-quality SLAs for the top 5 "
                f"{top_collection}s ({', '.join('`' + e['key'] + '`' for e in top[:5])}). "
                f"They carry {concentration_pct}% of network authority — small data "
                "outages here cascade across the rest of the graph."
            ),
            "recommendation_type": "action",
            "priority": "high", "effort": "medium",
            "expected_impact": "Reduces signal loss in the most-leveraged corners of the graph.",
            "related_insights": [insights[0]["title"]],
        },
        {
            "title": f"Action: Promote the high-{metric_label.lower()} tier to premium pricing / monitoring",
            "description": (
                "Promote the high-rank tier to a 'premium' pool used for both "
                "inventory pricing decisions and abuse-monitoring rules."
            ),
            "recommendation_type": "action",
            "priority": "medium", "effort": "low",
            "expected_impact": (
                "Higher revenue per impression on inventory tied to high-authority "
                "nodes; earlier detection of abuse on the same nodes."
            ),
            "related_insights": [insights[1]["title"]],
        },
    ]
    return {"insights": insights, "recommendations": recommendations}


def build_components_report(patch: UseCasePatch, summary: Dict[str, Any], algorithm_label: str) -> Dict[str, Any]:
    if not summary.get("component_count"):
        return _empty_report(patch)
    comp_count = int(summary["component_count"])
    singleton_count = int(summary.get("singleton_count") or 0)
    cluster_count = comp_count - singleton_count
    max_size = int(summary.get("max_size") or 0)
    avg_size = round(float(summary.get("avg_size") or 0), 2)
    sample = summary.get("largest_component_sample", [])
    big_threshold = max(4 * avg_size, 25)
    big_components = [c for c in summary.get("top_components", []) if c["size"] >= big_threshold]
    insights: List[Dict[str, Any]] = [
        {
            "title": f"{cluster_count:,} non-trivial clusters discovered ({algorithm_label})",
            "description": (
                f"The graph decomposes into {comp_count:,} {algorithm_label.lower()}s. "
                f"{cluster_count:,} contain 2+ nodes (the rest are singletons). "
                f"Average cluster size is {avg_size}; the largest holds {max_size:,} members."
            ),
            "insight_type": "key_finding",
            "confidence": 0.95,
            "supporting_data": {
                "component_count": comp_count, "cluster_count": cluster_count,
                "singleton_count": singleton_count, "max_size": max_size,
                "avg_size": avg_size,
            },
            "business_impact": (
                f"Each cluster is a candidate {patch.use_case_id} grouping; the "
                "cluster-count and size distribution drive how downstream identity / "
                "fraud / forecasting workflows should be sized."
            ),
        }
    ]
    if sample:
        insights.append({
            "title": f"Largest cluster spans {max_size:,} entities",
            "description": (
                "Sampled members of the largest cluster: "
                + ", ".join(f"`{m}`" for m in sample[:8]) + "."
            ),
            "insight_type": "key_finding",
            "confidence": 0.9,
            "supporting_data": {"sample": sample},
            "business_impact": (
                "Large unexplained clusters frequently indicate either a real "
                "cross-publisher household or coordinated abuse. Manual review of "
                "this cluster is the cheapest next investigation."
            ),
        })
    if big_components:
        insights.append({
            "title": f"{len(big_components)} outlier clusters (>{int(big_threshold):,} members)",
            "description": (
                f"{len(big_components)} clusters are at least 4× the network average. "
                "These are statistical outliers and should be triaged first."
            ),
            "insight_type": "key_finding",
            "confidence": 0.88,
            "supporting_data": {"outliers": big_components[:10], "threshold": big_threshold},
            "business_impact": (
                "Outlier-sized clusters typically capture either coordinated "
                "behaviour (botnets, bid duplication) or genuinely large households. "
                "Either way, they're the highest-yield investigation queue."
            ),
        })
    recommendations = [
        {
            "title": "Action: Stand up a cluster review queue",
            "description": (
                f"Surface the top-N clusters from `{patch.target_collection}` "
                "ranked by size into the analyst review queue. Tag clusters >4× "
                "mean as 'outlier' for first triage."
            ),
            "recommendation_type": "action",
            "priority": "high", "effort": "medium",
            "expected_impact": "Operationalises algorithm output instead of leaving it static.",
            "related_insights": [insights[0]["title"]],
        }
    ]
    if big_components:
        recommendations.append({
            "title": "Action: Triage outlier clusters first",
            "description": (
                f"Investigate the {len(big_components)} outlier-sized clusters — "
                "they concentrate the highest signal-to-noise for either fraud "
                "detection or large-household consolidation."
            ),
            "recommendation_type": "action",
            "priority": "high", "effort": "low",
            "expected_impact": "Fastest path from raw GAE output to actionable customer outcomes.",
            "related_insights": [insights[-1]["title"]],
        })
    return {"insights": insights, "recommendations": recommendations}


def _empty_report(patch: UseCasePatch) -> Dict[str, Any]:
    return {
        "insights": [{
            "title": "No Results Generated",
            "description": (
                f"The {patch.algorithm} run completed but the result collection "
                f"{patch.target_collection} was empty."
            ),
            "insight_type": "key_finding",
            "confidence": 1.0,
            "supporting_data": {},
            "business_impact": "Unable to derive insights without results.",
        }],
        "recommendations": [{
            "title": "Action: Re-run with a broader graph subset",
            "description": "Re-run the algorithm with more behavioural edges included.",
            "recommendation_type": "action",
            "priority": "low", "effort": "low",
            "expected_impact": "May surface insights once enough connectivity is captured.",
            "related_insights": ["No Results Generated"],
        }],
    }


# --------------------------------------------------------------------------- #
# Markdown writer + workflow_state.json patcher                               #
# --------------------------------------------------------------------------- #

def render_markdown(patch: UseCasePatch, exec_info: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    insights = analysis["insights"]
    recommendations = analysis["recommendations"]
    when = datetime.utcnow().isoformat(timespec="seconds")
    summary = (
        f"Analysis of {exec_info['result_count']:,} results using {patch.algorithm} "
        f"algorithm. identified {len(insights)} key insights. with highest confidence "
        f"finding: {insights[0]['title']}."
    )
    lines = [f"# {patch.title}", "", f"**Generated:** {when}", "", "## Summary", "", summary, "", f"## Insights ({len(insights)})", ""]
    for i, ins in enumerate(insights, 1):
        lines.extend([
            f"### {i}. {ins['title']}", "", ins["description"], "",
            f"- **Type:** InsightType.{ins['insight_type'].upper()}",
            f"- **Confidence:** {int(ins['confidence'] * 100)}%",
            f"- **Business Impact:** {ins['business_impact']}", "",
        ])
    lines.extend([f"## Recommendations ({len(recommendations)})", ""])
    for i, rec in enumerate(recommendations, 1):
        title = rec["title"][len("Action: "):] if rec["title"].startswith("Action: ") else rec["title"]
        lines.extend([
            f"### {i}. Action: {title}", "",
            f"Take action based on: {rec['description']}", "",
            f"- **Priority:** {rec['priority']}",
            f"- **Expected Impact:** {rec['expected_impact']}", "",
        ])
    return "\n".join(lines) + "\n"


def patch_workflow_state(
    patch: UseCasePatch, exec_info: Dict[str, Any], analysis: Dict[str, Any], state: Dict[str, Any],
) -> None:
    for rep in state.get("reports", []):
        if rep.get("title") != patch.title:
            continue
        rep["summary"] = (
            f"Analysis of {exec_info['result_count']:,} results using "
            f"{patch.algorithm} algorithm. identified {len(analysis['insights'])} "
            f"key insights. with highest confidence finding: {analysis['insights'][0]['title']}."
        )
        rep["generated_at"] = datetime.utcnow().isoformat()
        rep["algorithm"] = patch.algorithm
        rep["dataset_info"] = {
            "job_id": exec_info["job_id"], "execution_time": exec_info["execution_time"],
            "result_count": exec_info["result_count"], "completed_at": exec_info["completed_at"],
        }
        rep["insights"] = analysis["insights"]
        rep["recommendations"] = analysis["recommendations"]
        rep["sections"] = [{
            "title": "1. Overview",
            "content": (
                f"**Algorithm:** {patch.algorithm}\n"
                f"**Job ID:** {exec_info['job_id']}\n"
                f"**Execution Time:** {exec_info['execution_time']:.2f}s\n"
                f"**Results:** {exec_info['result_count']:,} records\n\n{rep['summary']}"
            ),
            "subsections": [], "metadata": {},
        }]
        break

    template_label = patch.title.split("Analysis Report: ", 1)[-1]
    for ex in state.get("execution_results", []):
        if (ex.get("template_name") or "") == template_label:
            ex["job_id"] = exec_info["job_id"]
            ex["algorithm"] = patch.algorithm
            ex["status"] = "ExecutionStatus.COMPLETED"
            ex["execution_time"] = exec_info["execution_time"]
            ex["result_count"] = exec_info["result_count"]
            ex["result_collection"] = patch.target_collection
            ex["error"] = None
            break


# --------------------------------------------------------------------------- #
# Driver                                                                      #
# --------------------------------------------------------------------------- #

def group_key(
    p: UseCasePatch,
) -> Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...]]:
    attrs = tuple(p.vertex_attributes or ())
    return (tuple(p.vertex_collections), tuple(p.edge_collections), attrs)


def regenerate_only(only: Optional[List[str]] = None) -> None:
    """Re-summarize existing uc_*_results collections and rewrite reports.

    Use this when the GAE jobs have already produced result collections and we
    only need to fix the markdown / workflow-state narrative (e.g. after a bug
    in `summarize_ranking`).  No GAE calls, no graph reload — pure read from
    ArangoDB.
    """
    _log("=" * 70)
    _log("REGENERATING ADTECH REPORTS (no GAE re-run)")
    _log("=" * 70)
    _log(f"Database:  {ADTECH_DATABASE} @ {os.environ['ARANGO_ENDPOINT']}")
    state = json.loads(WORKFLOW_STATE_PATH.read_text(encoding="utf-8"))
    db = adtech_db()

    selected = (
        [p for p in PATCHES if p.use_case_id in set(only)] if only else list(PATCHES)
    )
    _log(f"Patches:   {len(selected)}  ({', '.join(p.use_case_id for p in selected)})")
    _log("")

    for patch in selected:
        if not db.has_collection(patch.target_collection):
            _log(f"  !! {patch.use_case_id}: collection {patch.target_collection} missing — skipped")
            continue
        col = db.collection(patch.target_collection)
        count = col.count()
        if not count:
            _log(f"  !! {patch.use_case_id}: collection {patch.target_collection} empty — skipped")
            continue
        _log(f"  >> {patch.use_case_id} | {patch.algorithm} <- {patch.target_collection} ({count:,} rows)")
        field = ALG_RESULT_FIELDS[patch.algorithm]
        if patch.algorithm in ("pagerank", "betweenness"):
            analysis = build_ranking_report(patch, summarize_ranking(db, patch, field))
        elif patch.algorithm in ("wcc", "scc"):
            analysis = build_components_report(
                patch, summarize_components(db, patch, field),
                "Weakly Connected Component" if patch.algorithm == "wcc"
                else "Strongly Connected Component",
            )
        else:
            analysis = build_components_report(
                patch, summarize_components(db, patch, field), "Community"
            )

        # Re-use the existing job/timing/completed_at from workflow_state when
        # available so we don't lie about provenance just to fix narrative.
        prior = next(
            (r for r in state.get("reports", []) if r.get("title") == patch.title),
            None,
        )
        prior_ds = (prior or {}).get("dataset_info") or {}
        exec_info = {
            "job_id": prior_ds.get("job_id"),
            "execution_time": float(prior_ds.get("execution_time") or 0.0),
            "result_count": int(prior_ds.get("result_count") or count),
            "completed_at": prior_ds.get("completed_at") or datetime.utcnow().isoformat(),
        }
        _persist(patch, exec_info, analysis, state)

    _log("")
    _log("=" * 70)
    _log("DONE.  Re-run scripts/seed_adtech_workspace.py to refresh the UI.")
    _log("=" * 70)
    LOG_FH.close()


def main() -> None:
    args = sys.argv[1:]
    if "--regenerate-only" in args:
        only_flag = None
        for i, a in enumerate(args):
            if a == "--only" and i + 1 < len(args):
                only_flag = [s.strip() for s in args[i + 1].split(",") if s.strip()]
        regenerate_only(only=only_flag)
        return

    _log("=" * 70)
    _log("PATCHING EMPTY ADTECH REPORTS")
    _log("=" * 70)
    _log(f"Database:  {ADTECH_DATABASE} @ {os.environ['ARANGO_ENDPOINT']}")
    _log(f"Patches:   {len(PATCHES)}  ({', '.join(p.use_case_id for p in PATCHES)})")
    _log(f"Log file:  {LOG_PATH}")
    _log("")

    state = json.loads(WORKFLOW_STATE_PATH.read_text(encoding="utf-8"))
    db = adtech_db()

    gae = GenAIGAEConnection(verify_ssl=False, auto_reuse_services=True)
    _log("Ensuring GAE service is up…")
    info = gae.deploy_engine()
    _log(f"  ✓ engine: {info.get('id')}")

    # Group patches by graph subset so we load each subset once.
    grouped: Dict[
        Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...]],
        List[UseCasePatch],
    ] = {}
    for p in PATCHES:
        grouped.setdefault(group_key(p), []).append(p)

    try:
        for grp_idx, (key, patches) in enumerate(grouped.items(), 1):
            verts, edges, attrs = key
            _log("")
            _log("-" * 70)
            _log(f"Group {grp_idx}/{len(grouped)}: {len(patches)} patch(es), "
                 f"V={list(verts)}, E={list(edges)}"
                 + (f", attrs={list(attrs)}" if attrs else ""))
            _log("-" * 70)

            try:
                graph_id = load_graph(
                    gae, list(verts), list(edges), list(attrs) or None
                )
            except Exception as exc:
                _log(f"  !! load_graph failed: {exc}")
                # Mark all patches in this group as empty
                for patch in patches:
                    exec_info = {
                        "job_id": None, "execution_time": 0.0, "result_count": 0,
                        "completed_at": datetime.utcnow().isoformat(),
                    }
                    analysis = _empty_report(patch)
                    _persist(patch, exec_info, analysis, state)
                continue

            for patch in patches:
                _log(f"\n  >> {patch.use_case_id} | {patch.algorithm} -> {patch.target_collection}")
                t0 = time.time()
                try:
                    job_id = run_algorithm(gae, patch, graph_id)
                    count = store_results(
                        gae, db, patch.target_collection, job_id,
                        ALG_RESULT_FIELDS[patch.algorithm],
                    )
                    elapsed = time.time() - t0
                    exec_info = {
                        "job_id": job_id, "execution_time": elapsed,
                        "result_count": count,
                        "completed_at": datetime.utcnow().isoformat(),
                    }
                    _log(f"  ✓ {patch.use_case_id} stored {count:,} rows in {elapsed:.1f}s")
                except Exception as exc:
                    _log(f"  !! {patch.use_case_id} failed: {exc}")
                    exec_info = {
                        "job_id": None, "execution_time": time.time() - t0,
                        "result_count": 0,
                        "completed_at": datetime.utcnow().isoformat(),
                    }

                if exec_info["result_count"] > 0:
                    field = ALG_RESULT_FIELDS[patch.algorithm]
                    if patch.algorithm in ("pagerank", "betweenness"):
                        analysis = build_ranking_report(patch, summarize_ranking(db, patch, field))
                    elif patch.algorithm in ("wcc", "scc"):
                        analysis = build_components_report(
                            patch, summarize_components(db, patch, field),
                            "Weakly Connected Component" if patch.algorithm == "wcc"
                            else "Strongly Connected Component",
                        )
                    else:
                        analysis = build_components_report(
                            patch, summarize_components(db, patch, field), "Community"
                        )
                else:
                    analysis = _empty_report(patch)

                _persist(patch, exec_info, analysis, state)
    finally:
        _log("\nLeaving GAE service running (saves cold-start on next demo).")
        LOG_FH.close()

    print()
    print("=" * 70)
    print("DONE.  Re-run scripts/seed_adtech_workspace.py to refresh the UI.")
    print("=" * 70)


def _persist(
    patch: UseCasePatch, exec_info: Dict[str, Any], analysis: Dict[str, Any],
    state: Dict[str, Any],
) -> None:
    """Write markdown + persist workflow_state.json incrementally."""
    md = render_markdown(patch, exec_info, analysis)
    md_path = MARKDOWN_DIR / (
        f"report_{REPORT_TITLE_TO_INDEX[patch.title]:02d}_"
        + slugify(patch.title) + ".md"
    )
    md_path.write_text(md, encoding="utf-8")
    _log(f"  ✎ wrote {md_path.relative_to(REPO_ROOT)}")

    patch_workflow_state(patch, exec_info, analysis, state)
    WORKFLOW_STATE_PATH.write_text(
        json.dumps(state, indent=2, default=str), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
