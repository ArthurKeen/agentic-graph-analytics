"""
Analytics Catalog tools.

Tools:
  - list_epochs         – recent AnalysisEpoch records
  - get_epoch           – full detail for one epoch
  - query_executions    – paginated execution search with filters
  - get_lineage         – complete lineage for an execution
  - get_catalog_stats   – summary statistics
"""

from typing import Optional

from ..server import mcp


def _get_catalog():
    """Build an AnalysisCatalog connected to the current database."""
    from graph_analytics_ai.db_connection import get_db_connection
    from graph_analytics_ai.catalog import AnalysisCatalog
    from graph_analytics_ai.catalog.storage import ArangoDBStorage

    db = get_db_connection()
    storage = ArangoDBStorage(db)
    return AnalysisCatalog(storage), storage


# ---------------------------------------------------------------------------
# list_epochs
# ---------------------------------------------------------------------------
@mcp.tool()
def list_epochs(limit: int = 20) -> list:
    """List the most recent analysis epochs tracked in the catalog.

    Args:
        limit: Maximum number of epochs to return (default 20).

    Returns a list of epoch summary dicts (id, name, status, created_at).
    """
    from graph_analytics_ai.catalog import CatalogQueries, EpochFilter

    _, storage = _get_catalog()
    queries = CatalogQueries(storage)
    result = queries.query_with_pagination(
        filter=EpochFilter(),
        page=1,
        page_size=limit,
    )
    epochs = result.items if hasattr(result, "items") else result
    out = []
    for e in epochs:
        out.append(
            {
                "id": getattr(e, "id", None) or getattr(e, "epoch_id", None),
                "name": getattr(e, "name", None),
                "status": str(getattr(e, "status", "")),
                "created_at": str(getattr(e, "created_at", "")),
                "execution_count": getattr(e, "execution_count", None),
            }
        )
    return out


# ---------------------------------------------------------------------------
# get_epoch
# ---------------------------------------------------------------------------
@mcp.tool()
def get_epoch(epoch_id: str) -> dict:
    """Get full details for a single analysis epoch.

    Args:
        epoch_id: The ID of the epoch to retrieve.
    """
    catalog, _ = _get_catalog()
    epoch = catalog.get_epoch(epoch_id)
    if epoch is None:
        return {"error": f"Epoch {epoch_id!r} not found"}
    return {
        "id": getattr(epoch, "id", None) or getattr(epoch, "epoch_id", None),
        "name": getattr(epoch, "name", None),
        "status": str(getattr(epoch, "status", "")),
        "tags": getattr(epoch, "tags", []),
        "created_at": str(getattr(epoch, "created_at", "")),
        "metadata": getattr(epoch, "metadata", {}),
    }


# ---------------------------------------------------------------------------
# query_executions
# ---------------------------------------------------------------------------
@mcp.tool()
def query_executions(
    algorithm: Optional[str] = None,
    epoch_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Search execution records in the analytics catalog.

    Args:
        algorithm: Filter by algorithm name (e.g. 'pagerank', 'wcc').
        epoch_id: Filter by epoch ID.
        status: Filter by execution status string (e.g. 'completed', 'failed').
        page: Page number (1-indexed, default 1).
        page_size: Results per page (default 20).

    Returns a dict with keys: items, total, page, page_size.
    """
    from graph_analytics_ai.catalog import CatalogQueries, ExecutionFilter

    _, storage = _get_catalog()
    queries = CatalogQueries(storage)

    f = ExecutionFilter()
    if algorithm:
        f.algorithm = algorithm
    if epoch_id:
        f.epoch_id = epoch_id
    if status:
        f.status = status

    result = queries.query_with_pagination(filter=f, page=page, page_size=page_size)
    items = result.items if hasattr(result, "items") else result
    return {
        "items": [
            {
                "id": getattr(e, "id", None) or getattr(e, "execution_id", None),
                "algorithm": getattr(e, "algorithm", None),
                "status": str(getattr(e, "status", "")),
                "epoch_id": getattr(e, "epoch_id", None),
                "started_at": str(getattr(e, "started_at", "")),
                "duration_ms": getattr(e, "duration_ms", None),
            }
            for e in items
        ],
        "total": getattr(result, "total", len(items)),
        "page": page,
        "page_size": page_size,
    }


# ---------------------------------------------------------------------------
# get_lineage
# ---------------------------------------------------------------------------
@mcp.tool()
def get_lineage(execution_id: str) -> dict:
    """Get the complete lineage chain for an execution.

    Traces backwards through: Execution → Template → Use Case → Requirements.

    Args:
        execution_id: The ID of the execution to trace lineage for.
    """
    from graph_analytics_ai.catalog import LineageTracker
    from graph_analytics_ai.catalog.storage import ArangoDBStorage
    from graph_analytics_ai.db_connection import get_db_connection

    db = get_db_connection()
    storage = ArangoDBStorage(db)
    tracker = LineageTracker(storage)
    lineage = tracker.get_complete_lineage(execution_id)

    if lineage is None:
        return {"error": f"No lineage found for execution {execution_id!r}"}

    return (
        lineage.to_dict()
        if hasattr(lineage, "to_dict")
        else {"execution_id": execution_id, "lineage": str(lineage)}
    )


# ---------------------------------------------------------------------------
# get_catalog_stats
# ---------------------------------------------------------------------------
@mcp.tool()
def get_catalog_stats() -> dict:
    """Return summary statistics for the analytics catalog.

    Includes epoch count, execution count, algorithm breakdown, and more.
    """
    from graph_analytics_ai.catalog import CatalogManager
    from graph_analytics_ai.catalog.storage import ArangoDBStorage
    from graph_analytics_ai.db_connection import get_db_connection

    db = get_db_connection()
    storage = ArangoDBStorage(db)
    manager = CatalogManager(storage)
    stats = manager.get_statistics() if hasattr(manager, "get_statistics") else {}

    return stats if isinstance(stats, dict) else (stats.to_dict() if hasattr(stats, "to_dict") else str(stats))
