"""
GAE (Graph Analytics Engine) tools.

Tools:
  - list_gae_engines  – list actively running GAE engines
  - run_analysis      – run a single named algorithm directly via GAEOrchestrator
  - cleanup_engines   – stop and remove idle/stale GAE engines
"""

from typing import Any, Dict, List, Optional

from graph_analytics_ai import GAEManager  # noqa: F401 – imported for patching
from graph_analytics_ai.config import get_gae_config  # noqa: F401 – imported for patching
from ..server import mcp


# ---------------------------------------------------------------------------
# list_gae_engines
# ---------------------------------------------------------------------------
@mcp.tool()
def list_gae_engines() -> list:
    """List currently active Graph Analytics Engine (GAE) instances.

    Returns a list of engine summary dicts (id, status, algorithm, created_at).
    """
    gae_config = get_gae_config()
    manager = GAEManager(gae_config)

    try:
        engines = manager.list_engines()
    except Exception as exc:
        return [{"error": str(exc)}]

    out = []
    for eng in engines or []:
        if isinstance(eng, dict):
            out.append(eng)
        else:
            out.append(
                {
                    "id": getattr(eng, "id", None) or getattr(eng, "engine_id", None),
                    "status": str(getattr(eng, "status", "")),
                    "algorithm": getattr(eng, "algorithm", None),
                    "created_at": str(getattr(eng, "created_at", "")),
                }
            )
    return out


# ---------------------------------------------------------------------------
# run_analysis
# ---------------------------------------------------------------------------
@mcp.tool()
def run_analysis(
    graph_name: str,
    algorithm: str,
    vertex_collections: Optional[List[str]] = None,
    edge_collections: Optional[List[str]] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> dict:
    """Run a single graph algorithm directly via the GAE orchestrator.

    This is a synchronous, lower-level call compared to start_workflow.
    Suitable for running a single well-known algorithm without the full
    AI planning pipeline.

    Args:
        graph_name: Name of the ArangoDB named graph.
        algorithm: Algorithm to run. Supported: pagerank, wcc, scc,
            label_propagation, betweenness_centrality.
        vertex_collections: Optional list of vertex collections to include.
        edge_collections: Optional list of edge collections to traverse.
        parameters: Optional algorithm-specific parameter overrides (dict).

    Returns a dict with keys: status, algorithm, result_collection,
        duration_ms, node_count, edge_count, and any algorithm outputs.
    """
    from graph_analytics_ai import GAEOrchestrator, AnalysisConfig
    from graph_analytics_ai.db_connection import get_db_connection
    from graph_analytics_ai.config import get_gae_config

    db = get_db_connection()
    gae_config = get_gae_config()

    config = AnalysisConfig(
        graph_name=graph_name,
        algorithm=algorithm,
        vertex_collections=vertex_collections or [],
        edge_collections=edge_collections or [],
        parameters=parameters or {},
    )

    orchestrator = GAEOrchestrator(db=db, gae_config=gae_config)
    result = orchestrator.run_analysis(config)

    if hasattr(result, "to_dict"):
        return result.to_dict()
    elif isinstance(result, dict):
        return result
    return {"status": str(getattr(result, "status", "unknown")), "raw": str(result)}


# ---------------------------------------------------------------------------
# cleanup_engines
# ---------------------------------------------------------------------------
@mcp.tool()
def cleanup_engines(dry_run: bool = True) -> dict:
    """Stop and remove idle or stale GAE engine instances.

    Args:
        dry_run: If True (default), report what would be cleaned up without
            actually deleting anything. Set to False to perform the cleanup.

    Returns a dict with keys: cleaned_up (list of engine ids), dry_run.
    """
    gae_config = get_gae_config()
    manager = GAEManager(gae_config)

    try:
        engines = manager.list_engines() or []
        idle_ids = []
        for eng in engines:
            eid = eng.get("id") if isinstance(eng, dict) else getattr(eng, "id", None)
            status = (eng.get("status") if isinstance(eng, dict) else str(getattr(eng, "status", ""))).lower()
            if status in ("idle", "stopped", "error"):
                idle_ids.append(eid)

        if not dry_run:
            for eid in idle_ids:
                try:
                    manager.delete_engine(eid)
                except Exception:
                    pass

        return {"cleaned_up": idle_ids, "dry_run": dry_run}
    except Exception as exc:
        return {"error": str(exc), "dry_run": dry_run}
