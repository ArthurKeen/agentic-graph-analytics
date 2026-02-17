"""
Result selection for execution result sampling.

GAE algorithms can produce very large result sets. Downstream workflows (LLM analysis,
charts, and reporting) typically operate on a capped subset for cost/performance.
This module provides a small abstraction to deterministically and/or meaningfully
choose that subset, instead of relying on storage iteration order.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any, Dict, List, Optional, Tuple

from arango.database import StandardDatabase

from ...gae_orchestrator import ALGORITHM_RESULT_FIELDS
from .models import ResultSelectionConfig, ResultSelectionStrategy


class ResultSelector:
    """Build and run an AQL query to fetch a selected subset of results."""

    @staticmethod
    def default_selection_for_algorithm(
        algorithm: str, *, max_results: int
    ) -> ResultSelectionConfig:
        algo = (algorithm or "").lower().strip()
        field = ALGORITHM_RESULT_FIELDS.get(algo)

        # Score-like algorithms: use top-k by score field.
        if algo in {"pagerank", "betweenness"} and field:
            return ResultSelectionConfig(
                strategy=ResultSelectionStrategy.TOP_K,
                sort_field=field,
                sort_desc=True,
            )

        # Group/label algorithms: prefer largest groups by frequency.
        if algo in {"wcc", "scc", "label_propagation"} and field:
            return ResultSelectionConfig(
                strategy=ResultSelectionStrategy.LARGEST_GROUPS,
                group_field=field,
                groups=min(10, max(1, max_results)),
                per_group=None,
            )

        # Fallback: preserve legacy behavior.
        return ResultSelectionConfig(strategy=ResultSelectionStrategy.STORAGE_FIRST)

    @staticmethod
    def _aql_for_storage_first() -> str:
        return "FOR doc IN @@coll LIMIT @limit RETURN doc"

    @staticmethod
    def _aql_for_top_k(*, desc: bool) -> str:
        direction = "DESC" if desc else "ASC"
        # Dynamic attribute access: doc[@field]
        return (
            "FOR doc IN @@coll "
            "LET v = doc[@field] "
            f"SORT v {direction} "
            "LIMIT @limit "
            "RETURN doc"
        )

    @staticmethod
    def _aql_for_random() -> str:
        # Note: RAND() is not seedable in a portable way. If a deterministic sample
        # is needed, consider implementing a hash-based order on _key + seed.
        return "FOR doc IN @@coll SORT RAND() LIMIT @limit RETURN doc"

    @staticmethod
    def _aql_for_largest_groups() -> str:
        # Fetch top groups by count, then take up to per_group from each group.
        # Overall cap is applied by (a) per_group derived from limit and (b) a final
        # LIMIT @limit to protect against over-fetch and to keep bind-vars aligned.
        return (
            "LET topGroups = ("
            "  FOR doc IN @@coll "
            "    COLLECT g = doc[@group_field] WITH COUNT INTO c "
            "    SORT c DESC "
            "    LIMIT @groups "
            "    RETURN g"
            ") "
            "LET selected = ("
            "  FOR g IN topGroups "
            "    FOR doc IN @@coll "
            "      FILTER doc[@group_field] == g "
            "      LIMIT @per_group "
            "      RETURN doc"
            ") "
            "FOR doc IN selected "
            "LIMIT @limit "
            "RETURN doc"
        )

    @classmethod
    def select_results(
        cls,
        db: StandardDatabase,
        *,
        collection_name: str,
        algorithm: str,
        limit: int,
        selection: Optional[ResultSelectionConfig],
    ) -> Tuple[List[Dict[str, Any]], ResultSelectionConfig]:
        """
        Select result documents according to a strategy.

        Returns:
            (results, effective_selection)
        """
        effective = selection or cls.default_selection_for_algorithm(
            algorithm, max_results=limit
        )

        if limit <= 0:
            return [], effective

        bind_vars: Dict[str, Any] = {"@coll": collection_name, "limit": int(limit)}

        if effective.strategy == ResultSelectionStrategy.STORAGE_FIRST:
            query = cls._aql_for_storage_first()

        elif effective.strategy == ResultSelectionStrategy.TOP_K:
            # If sort_field isn't provided, fall back to storage-first.
            if not effective.sort_field:
                query = cls._aql_for_storage_first()
            else:
                query = cls._aql_for_top_k(desc=effective.sort_desc)
                bind_vars["field"] = effective.sort_field

        elif effective.strategy == ResultSelectionStrategy.RANDOM:
            query = cls._aql_for_random()

        elif effective.strategy == ResultSelectionStrategy.LARGEST_GROUPS:
            if not effective.group_field:
                query = cls._aql_for_storage_first()
            else:
                # Compute per-group size so groups * per_group >= limit
                groups = max(1, int(effective.groups or 1))
                per_group = (
                    int(effective.per_group)
                    if effective.per_group and effective.per_group > 0
                    else int(math.ceil(limit / groups))
                )
                query = cls._aql_for_largest_groups()
                bind_vars.update(
                    {
                        "group_field": effective.group_field,
                        "groups": groups,
                        "per_group": per_group,
                    }
                )
                # Record derived values so caller can report what happened.
                effective = replace(effective, groups=groups, per_group=per_group)

        else:
            # Unknown strategy -> legacy
            query = cls._aql_for_storage_first()

        results = list(db.aql.execute(query, bind_vars=bind_vars))
        if len(results) > limit:
            results = results[:limit]
        return results, effective

