"""
Baseline comparison utilities (catalog epochs).

Discovery Mode can compare the current run against a baseline epoch stored in the
Analysis Catalog. This module:
- Finds a comparable baseline execution in the catalog (same algorithm + template name)
- Fetches baseline results from ArangoDB (bounded sample)
- Computes lightweight, algorithm-specific metrics
- Emits delta insights when metrics shift materially
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..execution.models import ExecutionResult
from ..execution.result_selector import ResultSelector
from .models import Insight, InsightType


@dataclass
class BaselineComparisonResult:
    baseline_execution_id: Optional[str]
    baseline_template_name: Optional[str]
    current_metrics: Dict[str, float]
    baseline_metrics: Dict[str, float]
    deltas: Dict[str, float]
    insights: List[Insight]


def _safe_div(n: float, d: float) -> float:
    if not d:
        return 0.0
    return n / d


def _component_metrics(results: List[Dict[str, Any]]) -> Dict[str, float]:
    comps: Dict[Any, int] = {}
    for r in results:
        comps[r.get("component")] = comps.get(r.get("component"), 0) + 1
    sizes = sorted(comps.values(), reverse=True)
    total = float(len(results) or 0)
    largest = float(sizes[0]) if sizes else 0.0
    singletons = float(sum(1 for s in sizes if s == 1))
    return {
        "component_count": float(len(sizes)),
        "largest_component_size": largest,
        "largest_component_pct": _safe_div(largest, total),
        "singleton_count": singletons,
        "singleton_pct": _safe_div(singletons, float(len(sizes) or 0)),
    }


def _score_concentration_metrics(
    results: List[Dict[str, Any]], score_field: str
) -> Dict[str, float]:
    scored = [
        r
        for r in results
        if isinstance(r.get(score_field), (int, float))
        and r.get(score_field) is not None
    ]
    scored.sort(key=lambda x: x.get(score_field, 0), reverse=True)
    scores = [float(r.get(score_field, 0)) for r in scored]
    total = sum(scores)
    top_10 = sum(scores[:10])
    top_20 = sum(scores[:20])
    return {
        "total_score": float(total),
        "top10_share": _safe_div(float(top_10), float(total)),
        "top20_share": _safe_div(float(top_20), float(total)),
        "max_score": float(scores[0]) if scores else 0.0,
    }


def compute_metrics(algorithm: str, results: List[Dict[str, Any]]) -> Dict[str, float]:
    algorithm = (algorithm or "").lower()
    if algorithm in ("wcc", "scc"):
        return _component_metrics(results)
    if algorithm == "pagerank":
        return _score_concentration_metrics(results, "rank")
    if algorithm == "betweenness":
        return _score_concentration_metrics(results, "centrality")
    if algorithm == "label_propagation":
        # Common field names in datasets: community/label
        community_field = (
            "community" if any("community" in r for r in results) else "label"
        )
        # Reuse component metrics logic with community field remapped
        remapped = [{"component": r.get(community_field)} for r in results]
        return _component_metrics(remapped)
    return {}


def _diff(current: Dict[str, float], baseline: Dict[str, float]) -> Dict[str, float]:
    keys = set(current.keys()) | set(baseline.keys())
    return {k: float(current.get(k, 0.0)) - float(baseline.get(k, 0.0)) for k in keys}


def _deltas_to_insights(
    algorithm: str,
    deltas: Dict[str, float],
    current: Dict[str, float],
    baseline: Dict[str, float],
) -> List[Insight]:
    insights: List[Insight] = []
    algorithm = (algorithm or "").lower()

    # Heuristic thresholds tuned for stability (sampled results)
    if algorithm in ("pagerank", "betweenness"):
        share_delta = deltas.get("top10_share", 0.0)
        if abs(share_delta) >= 0.10:
            direction = "increased" if share_delta > 0 else "decreased"
            insights.append(
                Insight(
                    title=f"Δ Influence Concentration {direction}: top-10 share {baseline.get('top10_share',0):.2f} → {current.get('top10_share',0):.2f}",
                    description=(
                        "Compared to baseline, influence became meaningfully more concentrated in a small set of nodes. "
                        "This can indicate emerging chokepoints or architectural coupling (or improved semantic bridging)."
                    ),
                    insight_type=InsightType.ANOMALY,
                    confidence=0.65,
                    business_impact=(
                        "Review top ranked nodes for ownership/coverage; treat spikes as risk signals and validate extraction drift."
                    ),
                    supporting_data={
                        "deltas": deltas,
                        "current": current,
                        "baseline": baseline,
                    },
                )
            )

    if algorithm in ("wcc", "scc", "label_propagation"):
        largest_pct_delta = deltas.get("largest_component_pct", 0.0)
        comp_delta = deltas.get("component_count", 0.0)
        if abs(largest_pct_delta) >= 0.10 or abs(comp_delta) >= 10:
            insights.append(
                Insight(
                    title=(
                        f"Δ Structure Shift: components {baseline.get('component_count',0):.0f} → {current.get('component_count',0):.0f}, "
                        f"largest share {baseline.get('largest_component_pct',0):.2f} → {current.get('largest_component_pct',0):.2f}"
                    ),
                    description=(
                        "Compared to baseline, the connectivity/community structure shifted materially. "
                        "This can indicate missing links (fragmentation), new bridging edges (consolidation), or extraction/pipeline drift."
                    ),
                    insight_type=InsightType.ANOMALY,
                    confidence=0.6,
                    business_impact=(
                        "Validate data ingestion/extraction changes between epochs and investigate the largest changed components/communities."
                    ),
                    supporting_data={
                        "deltas": deltas,
                        "current": current,
                        "baseline": baseline,
                    },
                )
            )

    return insights


def compare_against_baseline_epoch(
    *,
    catalog: Any,
    db: Any,
    baseline_epoch_id: str,
    execution_result: ExecutionResult,
    result_limit: int = 1000,
) -> BaselineComparisonResult:
    """
    Compare an ExecutionResult against a baseline epoch using the catalog.

    The baseline is selected by:
    - same algorithm
    - same template_name (best-effort)
    - falling back to any execution for that algorithm in the baseline epoch
    """
    job = execution_result.job
    algorithm = job.algorithm

    baseline_execution = None
    baseline_execs = []
    try:
        from ...catalog.models import ExecutionFilter

        baseline_execs = catalog.query_executions(
            filter=ExecutionFilter(epoch_id=baseline_epoch_id, algorithm=algorithm),
            limit=200,
            offset=0,
        )
    except Exception:
        baseline_execs = []

    if baseline_execs:
        # Try to match on template name
        for e in baseline_execs:
            if getattr(e, "template_name", None) == job.template_name:
                baseline_execution = e
                break
        if baseline_execution is None:
            baseline_execution = baseline_execs[0]

    current_metrics = compute_metrics(algorithm, execution_result.results)
    if not baseline_execution or not getattr(
        baseline_execution, "results_location", None
    ):
        return BaselineComparisonResult(
            baseline_execution_id=(
                getattr(baseline_execution, "execution_id", None)
                if baseline_execution
                else None
            ),
            baseline_template_name=(
                getattr(baseline_execution, "template_name", None)
                if baseline_execution
                else None
            ),
            current_metrics=current_metrics,
            baseline_metrics={},
            deltas={},
            insights=[],
        )

    baseline_coll = baseline_execution.results_location
    try:
        baseline_results, _ = ResultSelector.select_results(
            db,
            collection_name=baseline_coll,
            algorithm=algorithm,
            limit=min(result_limit, len(execution_result.results) or result_limit),
            selection=None,
        )
    except Exception:
        baseline_results = []

    baseline_metrics = compute_metrics(algorithm, baseline_results)
    deltas = _diff(current_metrics, baseline_metrics)
    insights = _deltas_to_insights(algorithm, deltas, current_metrics, baseline_metrics)

    return BaselineComparisonResult(
        baseline_execution_id=getattr(baseline_execution, "execution_id", None),
        baseline_template_name=getattr(baseline_execution, "template_name", None),
        current_metrics=current_metrics,
        baseline_metrics=baseline_metrics,
        deltas=deltas,
        insights=insights,
    )
