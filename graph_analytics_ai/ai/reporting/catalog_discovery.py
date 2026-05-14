"""
Catalog-only Discovery Mode.

Generates a consolidated "unknown unknowns" report using:
- Analysis Catalog executions across recent epochs
- Stored result collections (results_location) from prior runs

This intentionally does NOT run new GAE jobs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ...catalog.models import ExecutionFilter
from ..execution.result_selector import ResultSelector
from .algorithm_insights import detect_patterns
from .baseline_comparison import compute_metrics
from .models import AnalysisReport, ReportSection, Insight, InsightType


@dataclass
class CatalogDiscoveryConfig:
    industry: str = "generic"
    graph_name: Optional[str] = None
    since_epochs: int = 5
    baseline_epoch_id: Optional[str] = None
    algorithms: Tuple[str, ...] = (
        "pagerank",
        "betweenness",
        "wcc",
        "scc",
        "label_propagation",
    )
    per_execution_limit: int = 1000
    top_k_hotspots: int = 20


def _diff(current: Dict[str, float], baseline: Dict[str, float]) -> Dict[str, float]:
    keys = set(current.keys()) | set(baseline.keys())
    return {k: float(current.get(k, 0.0)) - float(baseline.get(k, 0.0)) for k in keys}


def _select_epoch_ids(catalog: Any, cfg: CatalogDiscoveryConfig) -> List[str]:
    # Most recent epochs (descending by timestamp)
    epochs = catalog.query_epochs(limit=max(cfg.since_epochs, 1), offset=0)
    epoch_ids = [e.epoch_id for e in epochs if getattr(e, "epoch_id", None)]

    # Ensure explicit baseline is included (if provided)
    if cfg.baseline_epoch_id:
        baseline_id = cfg.baseline_epoch_id
        try:
            by_name = catalog.get_epoch_by_name(cfg.baseline_epoch_id)
            if by_name and getattr(by_name, "epoch_id", None):
                baseline_id = by_name.epoch_id
        except Exception:
            pass

        if baseline_id and baseline_id not in epoch_ids:
            epoch_ids.append(baseline_id)

    # Keep ordering: most recent first; baseline might be appended at end
    return epoch_ids


def _pick_best_execution(execs: List[Any]) -> Optional[Any]:
    if not execs:
        return None
    # execs are already sorted by timestamp desc from storage query
    for e in execs:
        if getattr(e, "status", None) and str(getattr(e, "status")).lower().endswith(
            "completed"
        ):
            return e
    return execs[0]


def _fetch_execution_results(
    db: Any, execution: Any, algorithm: str, limit: int
) -> List[Dict[str, Any]]:
    coll = getattr(execution, "results_location", None)
    if not coll:
        return []
    results, _ = ResultSelector.select_results(
        db, collection_name=coll, algorithm=algorithm, limit=limit, selection=None
    )
    return list(results or [])


def _recurring_hotspots(
    per_epoch_top: List[List[Dict[str, Any]]], top_k: int
) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}
    for epoch_results in per_epoch_top:
        for r in (epoch_results or [])[:top_k]:
            vid = r.get("id") or r.get("_id") or ""
            if not isinstance(vid, str) or not vid:
                continue
            counts[vid] = counts.get(vid, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    return [{"id": vid, "occurrences": c} for vid, c in ranked[:top_k]]


def generate_catalog_discovery_report(
    *,
    catalog: Any,
    db: Any,
    cfg: CatalogDiscoveryConfig,
) -> AnalysisReport:
    epoch_ids = _select_epoch_ids(catalog, cfg)
    if not epoch_ids:
        return AnalysisReport(
            title="Catalog Discovery Report",
            summary="No epochs found in catalog.",
            generated_at=datetime.now(),
            algorithm="catalog_discovery",
            sections=[
                ReportSection(
                    title="0. Discovery Summary",
                    content="No epochs found. Create epochs / track executions, then re-run.",
                )
            ],
        )

    baseline_epoch_id = cfg.baseline_epoch_id or epoch_ids[-1]
    latest_epoch_id = epoch_ids[0]

    insights: List[Insight] = []
    sections: List[ReportSection] = []

    # Summary section (high signal)
    summary_lines = [
        f"**Industry:** {cfg.industry}",
        f"**Graph name filter:** {cfg.graph_name or 'none'}",
        f"**Epochs scanned:** {len(epoch_ids)}",
        f"**Latest epoch:** {latest_epoch_id}",
        f"**Baseline epoch:** {baseline_epoch_id}",
        f"**Algorithms:** {', '.join(cfg.algorithms)}",
    ]
    sections.append(
        ReportSection(title="0. Discovery Summary", content="\n".join(summary_lines))
    )

    for algorithm in cfg.algorithms:
        per_epoch_metrics: List[Tuple[str, Dict[str, float]]] = []
        per_epoch_patterns: List[Tuple[str, List[Dict[str, Any]]]] = []
        per_epoch_top: List[List[Dict[str, Any]]] = []

        for epoch_id in epoch_ids:
            try:
                execs = catalog.query_executions(
                    filter=ExecutionFilter(
                        epoch_id=epoch_id,
                        algorithm=algorithm,
                        graph_name=cfg.graph_name,
                    ),
                    limit=50,
                    offset=0,
                )
            except Exception:
                execs = []

            execution = _pick_best_execution(execs)
            if not execution:
                continue

            try:
                results = _fetch_execution_results(
                    db, execution, algorithm, cfg.per_execution_limit
                )
            except Exception:
                results = []

            if not results:
                continue

            per_epoch_top.append(results[: cfg.top_k_hotspots])
            per_epoch_metrics.append((epoch_id, compute_metrics(algorithm, results)))

            try:
                patterns = detect_patterns(algorithm, cfg.industry, results)
            except Exception:
                patterns = []
            per_epoch_patterns.append((epoch_id, patterns))

        if not per_epoch_metrics:
            sections.append(
                ReportSection(
                    title=f"1. {algorithm}: No comparable executions found",
                    content=(
                        "No catalog executions with stored results were found for the selected epochs.\n"
                        "This can happen if results collections were deleted, or the algorithm wasn’t run."
                    ),
                )
            )
            continue

        # Compute baseline vs latest delta (best-effort)
        latest_metrics = per_epoch_metrics[0][1]
        baseline_metrics = {}
        for eid, m in per_epoch_metrics[::-1]:
            if eid == baseline_epoch_id:
                baseline_metrics = m
                break
        if not baseline_metrics:
            baseline_metrics = per_epoch_metrics[-1][1]

        deltas = _diff(latest_metrics, baseline_metrics)

        # Add delta insight when meaningful (algorithm-specific keys)
        if (
            algorithm in ("pagerank", "betweenness")
            and abs(deltas.get("top10_share", 0)) >= 0.10
        ):
            insights.append(
                Insight(
                    title=f"Δ {algorithm}: top-10 share {baseline_metrics.get('top10_share',0):.2f} → {latest_metrics.get('top10_share',0):.2f}",
                    description="Influence concentration changed materially across epochs (catalog-only comparison).",
                    insight_type=InsightType.ANOMALY,
                    confidence=0.6,
                    supporting_data={
                        "latest_epoch_id": latest_epoch_id,
                        "baseline_epoch_id": baseline_epoch_id,
                        "latest_metrics": latest_metrics,
                        "baseline_metrics": baseline_metrics,
                        "deltas": deltas,
                    },
                )
            )

        if algorithm in ("wcc", "scc", "label_propagation") and (
            abs(deltas.get("largest_component_pct", 0)) >= 0.10
            or abs(deltas.get("component_count", 0)) >= 10
        ):
            insights.append(
                Insight(
                    title=(
                        f"Δ {algorithm}: components {baseline_metrics.get('component_count',0):.0f} → {latest_metrics.get('component_count',0):.0f}, "
                        f"largest share {baseline_metrics.get('largest_component_pct',0):.2f} → {latest_metrics.get('largest_component_pct',0):.2f}"
                    ),
                    description="Connectivity/community structure shifted materially across epochs (catalog-only comparison).",
                    insight_type=InsightType.ANOMALY,
                    confidence=0.6,
                    supporting_data={
                        "latest_epoch_id": latest_epoch_id,
                        "baseline_epoch_id": baseline_epoch_id,
                        "latest_metrics": latest_metrics,
                        "baseline_metrics": baseline_metrics,
                        "deltas": deltas,
                    },
                )
            )

        # Recurring hotspots for centrality-style algorithms
        recurring = []
        if algorithm in ("pagerank", "betweenness"):
            recurring = _recurring_hotspots(per_epoch_top, cfg.top_k_hotspots)

        # Compile section
        lines: List[str] = []
        lines.append(f"**Comparable epochs (with results):** {len(per_epoch_metrics)}")
        lines.append("")
        lines.append("**Latest vs baseline metrics**")
        for k in sorted(set(latest_metrics.keys()) | set(baseline_metrics.keys())):
            lines.append(
                f"- **{k}**: {baseline_metrics.get(k, 0.0):.4f} → {latest_metrics.get(k, 0.0):.4f} (Δ {deltas.get(k, 0.0):+.4f})"
            )
        lines.append("")

        # Latest patterns (best effort)
        latest_patterns = per_epoch_patterns[0][1] if per_epoch_patterns else []
        if latest_patterns:
            lines.append("**Latest epoch patterns**")
            for p in latest_patterns[:5]:
                lines.append(f"- {p.get('title') or p.get('type')}")
            lines.append("")

        if recurring:
            lines.append("**Recurring hotspots (top IDs across epochs)**")
            for r in recurring[:10]:
                lines.append(f"- `{r['id']}` (occurrences: {r['occurrences']})")
            lines.append("")

        sections.append(
            ReportSection(
                title=f"1. {algorithm}: Catalog-only discovery",
                content="\n".join(lines).strip(),
            )
        )

    summary = (
        "Catalog-only discovery completed. This report compares stored results across epochs "
        "to highlight shifts, recurring hotspots, and domain-specific risk patterns."
    )

    return AnalysisReport(
        title="Catalog Discovery Report",
        summary=summary,
        generated_at=datetime.now(),
        algorithm="catalog_discovery",
        insights=insights,
        sections=sections,
        metadata={
            "discovery_mode": True,
            "catalog_only": True,
            "latest_epoch_id": latest_epoch_id,
            "baseline_epoch_id": baseline_epoch_id,
        },
    )
