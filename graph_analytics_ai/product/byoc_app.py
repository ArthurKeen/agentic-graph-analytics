"""Single-process app for the ArangoDB Platform (BYOC).

Locally the workspace runs as two processes: `next dev` on one port and the
product API on another. A BYOC bundle gets one process and one port, so the
API also has to serve the frontend's static export.

Route order is the whole trick. The static mount matches every path, so it is
added *last*: the contract routes, `/healthz` and the docs endpoints are
registered first and win, and only what none of them claim falls through to a
file on disk. Mounting the export first would shadow the entire API with 404s
from a file server.

The platform publishes the service under `/_service/uds/_global/<instance>/`
and envoy strips that prefix before this process sees it, so everything here
deals in clean paths. The prefix only matters to the browser, which is why it
is baked into the frontend at build time instead (see NFR-21 and
`frontend/next.config.mjs`).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: Where `scripts/platform/package.sh` puts the exported frontend inside the
#: bundle. Overridable so the same app can be run against a local build.
DEFAULT_STATIC_DIR_ENV = "AGA_STATIC_DIR"


def resolve_static_dir(static_dir: Optional[str | Path] = None) -> Optional[Path]:
    """Find the exported frontend, or return None if there isn't one.

    Order: explicit argument, then ``AGA_STATIC_DIR``, then the two layouts
    that actually occur — ``static/`` beside the bundle root (what the packaged
    service gets) and ``frontend/out`` (what a developer has after a build).
    """

    candidates: list[Path] = []
    if static_dir:
        candidates.append(Path(static_dir))
    env_dir = os.environ.get(DEFAULT_STATIC_DIR_ENV, "").strip()
    if env_dir:
        candidates.append(Path(env_dir))
    here = Path(__file__).resolve()
    # Bundle layout: <root>/static, with this module at <root>/graph_analytics_ai/product/.
    bundle_root = here.parent.parent.parent
    candidates.append(bundle_root / "static")
    # Development layout.
    candidates.append(bundle_root / "frontend" / "out")

    for candidate in candidates:
        if candidate.is_dir() and (candidate / "index.html").is_file():
            return candidate.resolve()
    return None


def create_byoc_app(
    static_dir: Optional[str | Path] = None,
    **app_kwargs: Any,
) -> Any:
    """Product API with the exported frontend mounted underneath it.

    Missing static files are a warning, not a failure: the API alone is still
    useful, and failing to boot would turn a packaging mistake into a service
    that never starts and reports nothing about why.
    """

    from fastapi.staticfiles import StaticFiles

    from .fastapi_app import create_product_fastapi_app

    app = create_product_fastapi_app(**app_kwargs)

    resolved = resolve_static_dir(static_dir)
    if resolved is None:
        logger.warning(
            "No exported frontend found (looked for an index.html under "
            "%s, $%s, <bundle>/static and <bundle>/frontend/out). "
            "Serving the API only.",
            static_dir or "<no explicit dir>",
            DEFAULT_STATIC_DIR_ENV,
        )
        return app

    logger.info("Serving the exported frontend from %s", resolved)
    # html=True makes `/` serve index.html and, with Next's trailingSlash
    # export, `/workspace/` serve workspace/index.html.
    app.mount("/", StaticFiles(directory=str(resolved), html=True), name="workspace-ui")
    return app


def build_app() -> Any:
    """Entry point for `uvicorn graph_analytics_ai.product.byoc_app:build_app`."""

    return create_byoc_app()
