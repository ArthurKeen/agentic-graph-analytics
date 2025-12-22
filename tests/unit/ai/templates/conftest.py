"""Fixtures for template tests."""

import pytest
from graph_analytics_ai.ai.templates.models import (
    AlgorithmType,
    AlgorithmParameters,
    TemplateConfig,
    AnalysisTemplate,
)
from graph_analytics_ai.ai.generation.use_cases import UseCase, UseCaseType
from graph_analytics_ai.ai.documents.models import Priority
from graph_analytics_ai.ai.schema.models import (
    GraphSchema,
    CollectionSchema,
    CollectionType,
)


@pytest.fixture
def simple_use_case():
    """Create a simple use case for testing."""
    return UseCase(
        id="UC-001",
        title="Find Influencers",
        description="Identify influential users",
        use_case_type=UseCaseType.CENTRALITY,
        priority=Priority.HIGH,
        related_requirements=[],
        graph_algorithms=["pagerank"],
        data_needs=["users"],
    )


@pytest.fixture
def simple_schema():
    """Create a simple graph schema for testing."""
    users_col = CollectionSchema(
        name="users", type=CollectionType.DOCUMENT, document_count=1000
    )
    follows_col = CollectionSchema(
        name="follows", type=CollectionType.EDGE, document_count=5000
    )

    return GraphSchema(
        database_name="test_graph",
        vertex_collections={"users": users_col},
        edge_collections={"follows": follows_col},
    )


@pytest.fixture
def valid_template():
    """Create a valid analysis template for testing."""
    return AnalysisTemplate(
        name="Valid Template",
        description="A valid template for testing",
        algorithm=AlgorithmParameters(
            algorithm=AlgorithmType.PAGERANK, parameters={"damping_factor": 0.85}
        ),
        config=TemplateConfig(
            graph_name="test_graph",
            vertex_collections=["users"],
            edge_collections=["follows"],
        ),
    )
