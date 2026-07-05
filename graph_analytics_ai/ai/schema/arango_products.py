"""Public Autograph / Arango-product detector facade.

This module is a thin shim over the canonical detector that lives
in :mod:`schema_analyzer.arango_products` (upstream
``arangodb-schema-analyzer``). The shim's job is to:

* **Prefer the upstream module** so any improvements made there
  (new product detectors, refined heuristics, bug fixes) flow into
  ``agentic-graph-analytics`` immediately on an analyzer upgrade.
* **Fall back to the in-tree implementation** in
  :mod:`graph_analytics_ai.ai.schema._arango_products_local` when
  the upstream version is missing - older analyzer installs that
  pre-date the ``arango_products`` module, or environments where
  ``arangodb-schema-analyzer`` isn't installed at all.

Consumers (service layer, agents, tests) should always import from
**this** module, never from either implementation directly. The
selected backend is logged once at import time and recorded on the
module-level ``ARANGO_PRODUCTS_BACKEND`` constant for diagnostics.

The two implementations expose the same public surface
(``ArangoProductReport``, ``AutographProject``,
``detect_arango_products``) plus the test-only ``_match_suffix``
helper, so swapping backends is type- and behaviour-equivalent.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

ARANGO_PRODUCTS_BACKEND: str
"""Which implementation backed this import (``"upstream"`` or ``"local"``)."""

try:
    from schema_analyzer.arango_products import (  # type: ignore[import-not-found]
        ArangoProductReport,
        AutographProject,
        _match_suffix,
        detect_arango_products,
    )

    ARANGO_PRODUCTS_BACKEND = "upstream"
    logger.debug(
        "Using upstream Autograph detector from schema_analyzer.arango_products"
    )
except ImportError:
    from ._arango_products_local import (  # noqa: F401
        ArangoProductReport,
        AutographProject,
        _match_suffix,
        detect_arango_products,
    )

    ARANGO_PRODUCTS_BACKEND = "local"
    logger.debug(
        "schema_analyzer.arango_products unavailable; using local fallback "
        "Autograph detector"
    )


__all__ = [
    "ARANGO_PRODUCTS_BACKEND",
    "ArangoProductReport",
    "AutographProject",
    "detect_arango_products",
]
