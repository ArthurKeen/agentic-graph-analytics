"""
Test fixtures for schema module tests.

Provides mock data and objects for testing schema extraction and analysis.
"""

import pytest
from unittest.mock import Mock

from graph_analytics_ai.ai.schema.models import (
    GraphSchema,
    CollectionSchema,
    CollectionType,
    AttributeInfo,
    Relationship,
)


@pytest.fixture
def sample_user_documents():
    """Sample user documents for testing."""
    return [
        {
            "_key": "user1",
            "_id": "users/user1",
            "_rev": "12345",
            "name": "Alice Smith",
            "email": "alice@example.com",
            "age": 30,
            "active": True,
            "address": {"city": "San Francisco", "country": "USA"},
            "tags": ["premium", "verified"],
        },
        {
            "_key": "user2",
            "_id": "users/user2",
            "_rev": "67890",
            "name": "Bob Jones",
            "email": "bob@example.com",
            "age": 25,
            "active": True,
            "address": {"city": "New York", "country": "USA"},
            "tags": ["new"],
        },
        {
            "_key": "user3",
            "_id": "users/user3",
            "_rev": "11111",
            "name": "Charlie Brown",
            "email": None,
            "age": 35,
            "active": False,
        },
    ]


@pytest.fixture
def sample_edge_documents():
    """Sample edge documents for testing."""
    return [
        {
            "_key": "edge1",
            "_id": "follows/edge1",
            "_rev": "22222",
            "_from": "users/user1",
            "_to": "users/user2",
            "since": "2023-01-15",
            "weight": 1.0,
        },
        {
            "_key": "edge2",
            "_id": "follows/edge2",
            "_rev": "33333",
            "_from": "users/user2",
            "_to": "users/user3",
            "since": "2023-02-20",
            "weight": 0.8,
        },
        {
            "_key": "edge3",
            "_id": "follows/edge3",
            "_rev": "44444",
            "_from": "users/user1",
            "_to": "users/user3",
            "since": "2023-03-10",
            "weight": 1.0,
        },
    ]


@pytest.fixture
def sample_collection_schema():
    """Sample collection schema for testing."""
    schema = CollectionSchema(
        name="users", type=CollectionType.VERTEX, document_count=100
    )

    # Add attributes
    schema.attributes = {
        "_key": AttributeInfo(
            name="_key", data_types={"string"}, present_count=100, null_count=0
        ),
        "name": AttributeInfo(
            name="name",
            data_types={"string"},
            present_count=100,
            null_count=0,
            sample_values=["Alice", "Bob", "Charlie"],
        ),
        "email": AttributeInfo(
            name="email",
            data_types={"string", "null"},
            present_count=90,
            null_count=10,
            sample_values=["alice@example.com", "bob@example.com"],
        ),
        "age": AttributeInfo(
            name="age",
            data_types={"number"},
            present_count=100,
            null_count=0,
            sample_values=[30, 25, 35, 28, 42],
        ),
    }

    return schema


@pytest.fixture
def sample_graph_schema():
    """Sample complete graph schema for testing."""
    schema = GraphSchema(database_name="test_db")

    # Add vertex collections
    schema.vertex_collections["users"] = CollectionSchema(
        name="users", type=CollectionType.VERTEX, document_count=100
    )

    schema.vertex_collections["products"] = CollectionSchema(
        name="products", type=CollectionType.VERTEX, document_count=50
    )

    # Add edge collections
    follows_col = CollectionSchema(
        name="follows", type=CollectionType.EDGE, document_count=200
    )
    follows_col.from_collections = {"users"}
    follows_col.to_collections = {"users"}
    schema.edge_collections["follows"] = follows_col

    purchased_col = CollectionSchema(
        name="purchased", type=CollectionType.EDGE, document_count=500
    )
    purchased_col.from_collections = {"users"}
    purchased_col.to_collections = {"products"}
    schema.edge_collections["purchased"] = purchased_col

    # Add relationships
    schema.relationships = [
        Relationship(
            edge_collection="follows",
            from_collection="users",
            to_collection="users",
            edge_count=200,
            relationship_type="FOLLOWS",
        ),
        Relationship(
            edge_collection="purchased",
            from_collection="users",
            to_collection="products",
            edge_count=500,
            relationship_type="PURCHASED",
        ),
    ]

    return schema


@pytest.fixture
def mock_arango_db():
    """Mock ArangoDB database connection."""
    db = Mock()
    db.name = "test_db"

    # Mock collections() method
    db.collections.return_value = [
        {"name": "users", "type": 2},  # document/vertex
        {"name": "products", "type": 2},
        {"name": "follows", "type": 3},  # edge
        {"name": "_system", "type": 2},  # system collection (should be filtered)
    ]

    # Mock graphs() method
    db.graphs.return_value = [{"name": "social_graph"}, {"name": "_system_graph"}]

    return db


@pytest.fixture
def mock_arango_collection(sample_user_documents):
    """Mock ArangoDB collection."""
    collection = Mock()
    collection.name = "users"
    collection.count.return_value = len(sample_user_documents)
    collection.all.return_value = iter(sample_user_documents)

    return collection


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing."""
    provider = Mock()

    # Mock generate_structured to return valid schema analysis
    provider.generate_structured.return_value = {
        "description": "A social network graph with users and their relationships.",
        "domain": "social network",
        "key_entities": ["users", "products"],
        "key_relationships": ["follows", "purchased"],
        "suggested_analyses": [
            {
                "type": "pagerank",
                "title": "PageRank Centrality",
                "reason": "Identify influential users in the network",
            },
            {
                "type": "community_detection",
                "title": "Community Detection",
                "reason": "Find clusters of closely connected users",
            },
        ],
        "complexity_score": 4.5,
    }

    return provider
