"""Optional FastAPI adapter for the product UI API."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from .api import PRODUCT_API_ENDPOINTS, ProductAPIDispatcher, ProductAPIEndpoint
from .factory import create_product_service

logger = logging.getLogger(__name__)

# Default origins permitted by the API when no override is supplied. Covers the
# common Next.js dev ports for the workspace UI.
_DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def _resolve_cors_origins(cors_origins: Optional[List[str]]) -> List[str]:
    """Resolve allowed CORS origins from arg or `AGA_PRODUCT_CORS_ORIGINS`."""

    if cors_origins is not None:
        return list(cors_origins)

    raw = os.getenv("AGA_PRODUCT_CORS_ORIGINS")
    if not raw:
        return list(_DEFAULT_CORS_ORIGINS)

    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_product_fastapi_app(
    service: Optional[Any] = None,
    title: str = "Agentic Graph Analytics Product API",
    version: str = "0.1.0",
    cors_origins: Optional[List[str]] = None,
    enable_agentic_supervisor: Optional[bool] = None,
    **service_kwargs: Any,
) -> Any:
    """Create a FastAPI app wired to the product service.

    FastAPI is an optional dependency. Install `graph-analytics-ai[api]` before
    calling this factory.

    Args:
        service: Optional pre-built ProductService.
        title / version: OpenAPI metadata.
        cors_origins: Allowed browser origins. Defaults to localhost:3000 (the
            Next.js dev server). Override programmatically or via the
            `AGA_PRODUCT_CORS_ORIGINS` env var (comma-separated). Pass `["*"]`
            to disable CORS scoping.
        enable_agentic_supervisor: FR-31a Phase 1 toggle. When ``True``, the
            app constructs an :class:`AgenticRunSupervisor`, wires it into the
            service, sweeps any orphan ``RUNNING`` rows on startup (Phase 1's
            executor is in-process so an API restart loses in-flight runs),
            and drains the pool on shutdown. Defaults to the env var
            ``AGA_ENABLE_AGENTIC_SUPERVISOR`` (``"1"``/``"true"`` enables
            it) and falls back to ``False`` for backward compatibility.
    """

    try:
        from fastapi import FastAPI, Request
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
    except ImportError as exc:
        raise ImportError(
            "FastAPI support requires the optional api extra: "
            "pip install 'graph-analytics-ai[api]'"
        ) from exc

    from .exceptions import (
        ConflictError,
        DuplicateError,
        NotFoundError,
        ValidationError,
    )

    product_service = service or create_product_service(**service_kwargs)

    enable_supervisor = _resolve_enable_supervisor(enable_agentic_supervisor)
    supervisor = None
    if enable_supervisor:
        # Lazy import so the FastAPI module is importable in
        # environments that have the AI extras but don't want to pay
        # the AgenticWorkflowRunner import cost at app startup.
        from .agentic_run_supervisor import AgenticRunSupervisor

        supervisor = AgenticRunSupervisor(product_service)
        # Make the service aware so start_workflow_run / cancel_workflow_run
        # / get_workflow_run_status route through the supervisor.
        product_service._agentic_run_supervisor = supervisor

    @asynccontextmanager
    async def lifespan(_app: Any):
        if supervisor is not None:
            try:
                # Phase 1: sweep orphan RUNNING rows on startup. The
                # in-process executor can't survive a restart, so a
                # row stuck in RUNNING is by definition stale.
                swept = supervisor.sweep_orphan_runs()
                if swept:
                    logger.info(
                        "AgenticRunSupervisor swept %d orphan run(s) on startup",
                        len(swept),
                    )
            except Exception:  # noqa: BLE001
                logger.exception("AgenticRunSupervisor orphan sweep failed")
        try:
            yield
        finally:
            if supervisor is not None:
                # Best-effort drain. Wait briefly so in-flight runs
                # have a chance to observe the cancel signal and
                # write a clean ``cancelled`` status; if they don't
                # finish in time, the next startup sweep will mark
                # them ``failed`` with stale_run_detected.
                supervisor.shutdown(wait=False)

    app = FastAPI(title=title, version=version, lifespan=lifespan)

    allowed_origins = _resolve_cors_origins(cors_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # FR-31a AC#8 + general API hygiene: map domain exceptions to
    # appropriate HTTP status codes so callers don't see opaque
    # 500s for conditions the service layer is signalling
    # explicitly. ConflictError → 409 is the FR-31a-driven case
    # (manual PATCH on agentic run); the others are baseline
    # contract responses that previously fell through to 500.
    def _make_handler(status_code: int):
        async def handler(_request: Any, exc: Exception):
            return JSONResponse(
                status_code=status_code,
                content={"error": exc.__class__.__name__, "detail": str(exc)},
            )

        return handler

    app.add_exception_handler(ValidationError, _make_handler(400))
    app.add_exception_handler(NotFoundError, _make_handler(404))
    app.add_exception_handler(ConflictError, _make_handler(409))
    app.add_exception_handler(DuplicateError, _make_handler(409))

    dispatcher = ProductAPIDispatcher(product_service)

    for endpoint in PRODUCT_API_ENDPOINTS:
        app.add_api_route(
            endpoint.path,
            _make_route_handler(dispatcher, endpoint, Request),
            methods=[endpoint.method],
            summary=endpoint.summary,
            tags=endpoint.tags,
        )

    return app


def _resolve_enable_supervisor(explicit: Optional[bool]) -> bool:
    if explicit is not None:
        return bool(explicit)
    raw = os.getenv("AGA_ENABLE_AGENTIC_SUPERVISOR", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _make_route_handler(
    dispatcher: ProductAPIDispatcher,
    endpoint: ProductAPIEndpoint,
    request_type: Any,
) -> Any:
    # Imported here so the FastAPI adapter remains the only place that knows
    # which service-layer result types need raw (non-JSON) HTTP responses.
    # Adding a new raw-response type later is a one-line addition below
    # rather than a new field on every endpoint contract.
    from fastapi import Response

    from .service import ReportExportResult

    async def route_handler(request: request_type) -> Any:
        body = await _request_json(request)
        result = dispatcher.dispatch(
            method=endpoint.method,
            path=endpoint.path,
            path_params=dict(request.path_params),
            query=dict(request.query_params),
            body=body,
        )

        if isinstance(result, ReportExportResult):
            # FR-42: stream the rendered document back as a download. The
            # service decides media_type + filename so the route handler
            # stays agnostic of HTML vs Markdown specifics.
            return Response(
                content=result.content,
                media_type=result.media_type,
                headers={
                    "Content-Disposition": (f'attachment; filename="{result.filename}"')
                },
            )

        return result

    route_handler.__name__ = _route_handler_name(endpoint)
    return route_handler


async def _request_json(request: Any) -> Dict[str, Any]:
    if request.method in {"GET", "DELETE", "HEAD", "OPTIONS"}:
        return {}

    try:
        body = await request.json()
    except Exception:
        return {}

    if body is None:
        return {}
    if not isinstance(body, dict):
        return {"body": body}
    return body


def _route_handler_name(endpoint: ProductAPIEndpoint) -> str:
    normalized_path = (
        endpoint.path.strip("/")
        .replace("/", "_")
        .replace("{", "")
        .replace("}", "")
        .replace("-", "_")
    )
    return f"{endpoint.method.lower()}_{normalized_path}"
