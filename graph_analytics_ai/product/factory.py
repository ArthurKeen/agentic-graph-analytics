"""Factories for wiring product UI services."""

from typing import Any, Callable, Optional

from graph_analytics_ai.db_connection import get_db_connection

from .repository import ProductRepository
from .secrets import SecretResolver
from .service import ProductService
from .storage import ProductArangoStorage


def create_product_service(
    db: Optional[Any] = None,
    db_connector: Optional[Callable[[], Any]] = None,
    storage: Optional[ProductArangoStorage] = None,
    repository: Optional[ProductRepository] = None,
    secret_resolver: Optional[SecretResolver] = None,
    service_db_connector: Optional[Callable[..., Any]] = None,
    schema_extractor_factory: Optional[Callable[..., Any]] = None,
    auto_initialize: bool = True,
) -> ProductService:
    """Create a product service with the default ArangoDB storage stack."""

    if repository is None:
        if storage is None:
            database = db if db is not None else (db_connector or get_db_connection)()
            storage = ProductArangoStorage(
                database,
                auto_initialize=auto_initialize,
            )
        repository = ProductRepository(storage)

    return ProductService(
        repository=repository,
        secret_resolver=secret_resolver,
        db_connector=service_db_connector,
        schema_extractor_factory=schema_extractor_factory,
    )
