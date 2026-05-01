"""Optional FastAPI adapter for the product UI API."""

from typing import Any, Dict, Optional

from .api import PRODUCT_API_ENDPOINTS, ProductAPIDispatcher, ProductAPIEndpoint
from .factory import create_product_service


def create_product_fastapi_app(
    service: Optional[Any] = None,
    title: str = "Agentic Graph Analytics Product API",
    version: str = "0.1.0",
    **service_kwargs: Any,
) -> Any:
    """Create a FastAPI app wired to the product service.

    FastAPI is an optional dependency. Install `graph-analytics-ai[api]` before
    calling this factory.
    """

    try:
        from fastapi import FastAPI, Request
    except ImportError as exc:
        raise ImportError(
            "FastAPI support requires the optional api extra: "
            "pip install 'graph-analytics-ai[api]'"
        ) from exc

    product_service = service or create_product_service(**service_kwargs)
    app = FastAPI(title=title, version=version)
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
