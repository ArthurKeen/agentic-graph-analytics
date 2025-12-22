"""
Unit tests for schema extractor.

Tests schema extraction from ArangoDB databases.
"""

from unittest.mock import Mock, patch

from graph_analytics_ai.ai.schema.extractor import SchemaExtractor, create_extractor
from graph_analytics_ai.ai.schema.models import CollectionType


class TestSchemaExtractor:
    """Test SchemaExtractor class."""

    def test_init(self, mock_arango_db):
        """Test extractor initialization."""
        extractor = SchemaExtractor(mock_arango_db, sample_size=50)

        assert extractor.db == mock_arango_db
        assert extractor.sample_size == 50
        assert extractor.max_samples_per_collection == 3

    def test_determine_collection_type_edge(self):
        """Test determining edge collection type."""
        extractor = SchemaExtractor(Mock())

        col_info = {"name": "follows", "type": 3}
        col_type = extractor._determine_collection_type(col_info)

        assert col_type == CollectionType.EDGE

    def test_determine_collection_type_vertex(self):
        """Test determining vertex collection type."""
        extractor = SchemaExtractor(Mock())

        col_info = {"name": "users", "type": 2}
        col_type = extractor._determine_collection_type(col_info)

        assert col_type == CollectionType.VERTEX

    def test_get_value_type(self):
        """Test getting value types."""
        extractor = SchemaExtractor(Mock())

        assert extractor._get_value_type(None) == "null"
        assert extractor._get_value_type(True) == "boolean"
        assert extractor._get_value_type(42) == "number"
        assert extractor._get_value_type(3.14) == "number"
        assert extractor._get_value_type("hello") == "string"
        assert extractor._get_value_type([1, 2, 3]) == "array"
        assert extractor._get_value_type({"key": "value"}) == "object"

    def test_clean_sample_documents(self):
        """Test cleaning sample documents."""
        extractor = SchemaExtractor(Mock())

        docs = [
            {
                "_key": "user1",
                "_id": "users/user1",
                "_rev": "12345",
                "name": "Alice",
                "description": "A" * 150,  # Long string
                "data": {"nested": "value"},
            }
        ]

        cleaned = extractor._clean_sample_documents(docs)

        assert len(cleaned) == 1
        assert "_key" in cleaned[0]
        assert "_id" not in cleaned[0]  # Filtered out
        assert "_rev" not in cleaned[0]  # Filtered out
        assert "name" in cleaned[0]
        assert len(cleaned[0]["description"]) < 150  # Truncated

    def test_extract_from_collections(self, sample_edge_documents):
        """Test extracting from collections from edges."""
        extractor = SchemaExtractor(Mock())

        from_cols = extractor._extract_from_collections(sample_edge_documents)

        assert "users" in from_cols
        assert len(from_cols) == 1

    def test_extract_to_collections(self, sample_edge_documents):
        """Test extracting to collections from edges."""
        extractor = SchemaExtractor(Mock())

        to_cols = extractor._extract_to_collections(sample_edge_documents)

        assert "users" in to_cols
        assert len(to_cols) == 1

    def test_guess_relationship_type_follows(self):
        """Test guessing relationship type for 'follows'."""
        extractor = SchemaExtractor(Mock())

        rel_type = extractor._guess_relationship_type("user_follows_user")
        assert rel_type == "FOLLOWS"

    def test_guess_relationship_type_single_word(self):
        """Test guessing relationship type for single word."""
        extractor = SchemaExtractor(Mock())

        rel_type = extractor._guess_relationship_type("knows")
        assert rel_type == "KNOWS"

    def test_guess_relationship_type_unknown(self):
        """Test guessing relationship type for unknown pattern."""
        extractor = SchemaExtractor(Mock())

        rel_type = extractor._guess_relationship_type("some_random_edge_name")
        assert rel_type == "RANDOM"  # Middle part of 3-part name

    def test_analyze_attributes(self, sample_user_documents):
        """Test analyzing attributes from documents."""
        extractor = SchemaExtractor(Mock())

        attributes = extractor._analyze_attributes(sample_user_documents)

        # Check key attributes exist
        assert "name" in attributes
        assert "email" in attributes
        assert "age" in attributes

        # Check name attribute
        assert "string" in attributes["name"].data_types
        assert attributes["name"].present_count == 3
        assert attributes["name"].null_count == 0

        # Check email attribute (has null)
        assert "string" in attributes["email"].data_types
        assert "null" in attributes["email"].data_types
        assert attributes["email"].null_count == 1
        assert attributes["email"].present_count == 2

    def test_analyze_nested_attributes(self):
        """Test analyzing nested object attributes."""
        extractor = SchemaExtractor(Mock())

        docs = [{"user": "alice", "address": {"city": "SF", "zip": "94102"}}]

        attributes = extractor._analyze_attributes(docs)

        # Check nested attributes
        assert "address" in attributes
        assert "address.city" in attributes
        assert "address.zip" in attributes

        assert attributes["address"].primary_type == "object"
        assert attributes["address.city"].primary_type == "string"

    @patch("graph_analytics_ai.ai.schema.extractor.ArangoClient")
    def test_create_extractor(self, mock_client_class):
        """Test factory function for creating extractor."""
        mock_client = Mock()
        mock_db = Mock()
        mock_client.db.return_value = mock_db
        mock_client_class.return_value = mock_client

        extractor = create_extractor(
            endpoint="http://localhost:8529",
            database="test_db",
            username="root",
            password="password",
            sample_size=50,
        )

        # Verify client was created with correct params
        mock_client_class.assert_called_once_with(
            hosts="http://localhost:8529", verify_override=True
        )

        # Verify db connection was established
        mock_client.db.assert_called_once_with(
            "test_db", username="root", password="password"
        )

        # Verify extractor was created
        assert isinstance(extractor, SchemaExtractor)
        assert extractor.db == mock_db
        assert extractor.sample_size == 50


class TestSchemaExtractorIntegration:
    """Integration tests for schema extractor with mocked database."""

    def test_extract_complete_schema(
        self, mock_arango_db, sample_user_documents, sample_edge_documents
    ):
        """Test extracting complete schema from database."""
        # Setup mock collection
        mock_collection = Mock()
        mock_collection.count.return_value = len(sample_user_documents)

        # Mock AQL execution for sampling
        mock_cursor = Mock()
        mock_cursor.__iter__ = Mock(return_value=iter(sample_user_documents))
        mock_arango_db.aql.execute.return_value = mock_cursor

        # Mock collection() method to return different collections
        def get_collection(name):
            if name == "users" or name == "products":
                mock_col = Mock()
                mock_col.count.return_value = len(sample_user_documents)
                return mock_col
            else:  # follows
                mock_col = Mock()
                mock_col.count.return_value = len(sample_edge_documents)
                return mock_col

        mock_arango_db.collection.side_effect = get_collection

        # Mock AQL to return appropriate documents based on collection
        def execute_aql(query, bind_vars):
            if "users" in query or "products" in query:
                mock_cursor = Mock()
                mock_cursor.__iter__ = Mock(return_value=iter(sample_user_documents))
                return mock_cursor
            else:  # follows
                mock_cursor = Mock()
                mock_cursor.__iter__ = Mock(return_value=iter(sample_edge_documents))
                return mock_cursor

        mock_arango_db.aql.execute.side_effect = execute_aql

        # Create extractor and extract
        extractor = SchemaExtractor(mock_arango_db, sample_size=10)
        schema = extractor.extract()

        # Verify basic schema properties
        assert schema.database_name == "test_db"
        assert len(schema.vertex_collections) == 2  # users, products
        assert len(schema.edge_collections) == 1  # follows

        # Verify collections were processed
        assert "users" in schema.vertex_collections
        assert "products" in schema.vertex_collections
        assert "follows" in schema.edge_collections

        # Verify relationships were extracted
        assert len(schema.relationships) >= 1

        # Verify graph names (no system graphs)
        assert "social_graph" in schema.graph_names
        assert "_system_graph" not in schema.graph_names
