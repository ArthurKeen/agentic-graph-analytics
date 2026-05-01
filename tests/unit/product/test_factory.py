"""Unit tests for product service factories."""

from graph_analytics_ai.product import ProductRepository, ProductService, create_product_service


def test_create_product_service_uses_injected_repository():
    """Factory returns a service around an explicitly supplied repository."""

    repository = object()

    service = create_product_service(repository=repository)

    assert isinstance(service, ProductService)
    assert service.repository is repository


def test_create_product_service_builds_repository_from_database():
    """Factory wires Arango storage and repository from an injected database."""

    database = object()

    service = create_product_service(db=database, auto_initialize=False)

    assert isinstance(service.repository, ProductRepository)
    assert service.repository.storage.db is database


def test_create_product_service_uses_db_connector_when_database_not_supplied():
    """Factory calls the configured connector when no database is injected."""

    database = object()
    calls = []

    def connector():
        calls.append("called")
        return database

    service = create_product_service(
        db_connector=connector,
        auto_initialize=False,
    )

    assert calls == ["called"]
    assert service.repository.storage.db is database
