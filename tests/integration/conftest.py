"""
Pytest configuration and fixtures for integration tests.

These tests require real external services and are skipped by default.
Run with: pytest --run-integration
"""

import pytest
import os
from pathlib import Path


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires external services)",
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires --run-integration flag)",
    )
    config.addinivalue_line(
        "markers", "requires_llm: mark test as requiring LLM provider"
    )
    config.addinivalue_line(
        "markers", "requires_db: mark test as requiring database connection"
    )
    config.addinivalue_line(
        "markers", "requires_gae: mark test as requiring GAE access"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --run-integration is specified."""
    if config.getoption("--run-integration"):
        # Running integration tests - don't skip
        return

    skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


# Fixtures


@pytest.fixture(scope="session")
def test_env_vars():
    """Load test environment variables."""
    from dotenv import load_dotenv

    # Try to load .env.test if it exists
    test_env = Path(__file__).parent.parent.parent / ".env.test"
    if test_env.exists():
        load_dotenv(test_env)
    else:
        load_dotenv()  # Fall back to regular .env

    return {
        "llm_api_key": os.getenv("OPENROUTER_API_KEY"),
        "llm_model": os.getenv("LLM_MODEL", "google/gemini-flash-1.5"),
        "db_endpoint": os.getenv("ARANGO_ENDPOINT", "http://localhost:8529"),
        "db_name": os.getenv("ARANGO_DATABASE", "graph-analytics-ai-test"),
        "db_user": os.getenv("ARANGO_USER", "root"),
        "db_password": os.getenv("ARANGO_PASSWORD"),
        "gae_token": os.getenv("ARANGO_GRAPH_TOKEN"),
    }


@pytest.fixture(scope="session")
def check_env_vars(test_env_vars):
    """Verify required environment variables are set."""
    missing = []

    if not test_env_vars["llm_api_key"]:
        missing.append("OPENROUTER_API_KEY")

    if not test_env_vars["db_password"]:
        missing.append("ARANGO_PASSWORD")

    if missing:
        pytest.skip(f"Missing required environment variables: {', '.join(missing)}")

    return test_env_vars


@pytest.fixture(scope="function")
def temp_output_dir(tmp_path):
    """Create temporary output directory for test runs."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture(scope="session")
def test_use_case_file():
    """Path to test use case file."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    use_case_file = fixtures_dir / "test_use_case.md"

    if not use_case_file.exists():
        pytest.skip(f"Test use case file not found: {use_case_file}")

    return str(use_case_file)


@pytest.fixture(scope="function")
def mock_llm_provider():
    """Create a mock LLM provider for testing without API calls."""
    from unittest.mock import Mock

    mock = Mock()
    mock.generate.return_value = "Mock LLM response"
    mock.generate_with_schema.return_value = {"mock": "data"}

    return mock


@pytest.fixture(scope="session")
def test_graph_schema():
    """Sample graph schema for testing."""
    from graph_analytics_ai.ai.schema.models import GraphSchema, CollectionInfo

    return GraphSchema(
        database="test_db",
        vertex_collections=[
            CollectionInfo(name="users", count=100, sample_doc={"name": "Alice"}),
            CollectionInfo(name="products", count=50, sample_doc={"title": "Widget"}),
        ],
        edge_collections=[
            CollectionInfo(name="purchased", count=200, sample_doc={"quantity": 1}),
            CollectionInfo(
                name="viewed", count=500, sample_doc={"timestamp": "2024-01-01"}
            ),
        ],
        named_graphs=[],
    )
