"""Optional FastAPI adapter for the product UI API."""

import os
from typing import Any, Dict, List, Optional

from .api import PRODUCT_API_ENDPOINTS, ProductAPIDispatcher, ProductAPIEndpoint
from .factory import create_product_service

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
    """

    try:
        from fastapi import FastAPI, Request
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError as exc:
        raise ImportError(
            "FastAPI support requires the optional api extra: "
            "pip install 'graph-analytics-ai[api]'"
        ) from exc

    product_service = service or create_product_service(**service_kwargs)
    app = FastAPI(title=title, version=version)

    allowed_origins = _resolve_cors_origins(cors_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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


def _make_route_handler(
    dispatcher: ProductAPIDispatcher,
    endpoint: ProductAPIEndpoint,
    request_type: Any,
) -> Any:
    async def route_handler(request: request_type) -> Any:
        body = await _request_json(request)
        return dispatcher.dispatch(
            method=endpoint.method,
            path=endpoint.path,
            path_params=dict(request.path_params),
            query=dict(request.query_params),
            body=body,
        )

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
