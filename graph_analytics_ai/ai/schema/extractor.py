"""
Schema extractor for ArangoDB databases.

This module extracts schema information from an ArangoDB database,
including collections, attributes, relationships, and sample data.
"""

from typing import Dict, List, Optional, Set, Any
from arango import ArangoClient
from arango.database import StandardDatabase
from arango.collection import StandardCollection

from .models import (
    GraphSchema,
    CollectionSchema,
    CollectionType,
    AttributeInfo,
    Relationship,
)


class SchemaExtractor:
    """
    Extract schema information from an ArangoDB database.

    This class connects to ArangoDB and analyzes the database structure,
    including collections, attributes, relationships, and sample documents.

    Example:
        >>> from arango import ArangoClient
        >>> client = ArangoClient(hosts='http://localhost:8529')
        >>> db = client.db('my_database', username='root', password='password')
        >>>
        >>> extractor = SchemaExtractor(db)
        >>> schema = extractor.extract()
        >>>
        >>> print(f"Found {len(schema.vertex_collections)} vertex collections")
        >>> print(f"Total documents: {schema.total_documents}")
    """

    def __init__(
        self,
        db: StandardDatabase,
        sample_size: int = 100,
        max_samples_per_collection: int = 3,
    ):
        """
        Initialize schema extractor.

        Args:
            db: ArangoDB database connection.
            sample_size: Number of documents to sample for attribute analysis.
            max_samples_per_collection: Maximum sample documents to store per collection.
        """
        self.db = db
        self.sample_size = sample_size
        self.max_samples_per_collection = max_samples_per_collection

    def extract(self) -> GraphSchema:
        """
        Extract complete schema from the database.

        Returns:
            GraphSchema containing all schema information.
        """
        schema = GraphSchema(database_name=self.db.name)

        # Get all collections
        collections = self.db.collections()

        # Separate system collections from user collections
        user_collections = [
            col for col in collections if not col["name"].startswith("_")
        ]

        # Process each collection
        for col_info in user_collections:
            col_name = col_info["name"]
            col_type = self._determine_collection_type(col_info)

            # Extract collection schema
            col_schema = self._extract_collection_schema(col_name, col_type)

            # Add to appropriate category
            if col_type == CollectionType.VERTEX:
                schema.vertex_collections[col_name] = col_schema
            elif col_type == CollectionType.EDGE:
                schema.edge_collections[col_name] = col_schema
            else:
                schema.document_collections[col_name] = col_schema

        # Extract relationships
        schema.relationships = self._extract_relationships(schema)

        # Get named graphs
        try:
            graphs = self.db.graphs()
            schema.graph_names = [
                g["name"] for g in graphs if not g["name"].startswith("_")
            ]
        except:
            # Ignore if graphs() fails
            schema.graph_names = []

        return schema

    def _determine_collection_type(self, col_info: Dict[str, Any]) -> CollectionType:
        """Determine if collection is vertex, edge, or document."""
        col_type = col_info.get("type")

        # python-arango returns 'edge' or 'document' as strings
        # or legacy integer values: Type 2 = document collection, Type 3 = edge collection
        if col_type == 3 or col_type == "edge":
            return CollectionType.EDGE

        # For document collections, check if they're used as vertices
        # We'll default to VERTEX for now, can refine later
        # (Document collections not in any graph are marked as DOCUMENT)
        return CollectionType.VERTEX

    def _extract_collection_schema(
        self, col_name: str, col_type: CollectionType
    ) -> CollectionSchema:
        """Extract schema for a single collection."""
        collection = self.db.collection(col_name)

        # Create collection schema
        col_schema = CollectionSchema(
            name=col_name, type=col_type, document_count=collection.count()
        )

        # Sample documents for attribute analysis
        if col_schema.document_count > 0:
            sample_docs = self._sample_documents(collection, self.sample_size)

            # Analyze attributes
            col_schema.attributes = self._analyze_attributes(sample_docs)

            # Store sample documents (limited number)
            col_schema.sample_documents = self._clean_sample_documents(
                sample_docs[: self.max_samples_per_collection]
            )

            # For edge collections, extract from/to information
            if col_type == CollectionType.EDGE:
                col_schema.from_collections = self._extract_from_collections(
                    sample_docs
                )
                col_schema.to_collections = self._extract_to_collections(sample_docs)

        return col_schema

    def _sample_documents(
        self, collection: StandardCollection, sample_size: int
    ) -> List[Dict[str, Any]]:
        """Sample documents from a collection."""
        try:
            # Use AQL to get random sample
            aql = f"""
                FOR doc IN {collection.name}
                LIMIT @sample_size
                RETURN doc
            """

            cursor = self.db.aql.execute(aql, bind_vars={"sample_size": sample_size})

            return list(cursor)

        except Exception:
            # If sampling fails, try to get any documents
            try:
                return list(collection.all(limit=sample_size))
            except:
                return []

    def _analyze_attributes(
        self, documents: List[Dict[str, Any]]
    ) -> Dict[str, AttributeInfo]:
        """Analyze attributes across sampled documents."""
        attributes: Dict[str, AttributeInfo] = {}

        for doc in documents:
            self._process_document_attributes(doc, attributes)

        return attributes

    def _process_document_attributes(
        self,
        doc: Dict[str, Any],
        attributes: Dict[str, AttributeInfo],
        prefix: str = "",
    ):
        """
        Process attributes in a document (recursive for nested objects).

        Args:
            doc: Document to process.
            attributes: Dictionary to accumulate attribute information.
            prefix: Prefix for nested attributes (e.g., 'address.').
        """
        for key, value in doc.items():
            attr_name = f"{prefix}{key}" if prefix else key

            # Get or create attribute info
            if attr_name not in attributes:
                attributes[attr_name] = AttributeInfo(name=attr_name)

            attr_info = attributes[attr_name]

            # Update statistics
            if value is None:
                attr_info.null_count += 1
                attr_info.data_types.add("null")
            else:
                attr_info.present_count += 1

                # Determine type
                value_type = self._get_value_type(value)
                attr_info.data_types.add(value_type)

                # Store sample values (max 5)
                if len(attr_info.sample_values) < 5:
                    # Don't store large objects
                    if value_type in ["string", "number", "boolean"]:
                        attr_info.sample_values.append(value)
                    elif value_type == "array" and len(str(value)) < 100:
                        attr_info.sample_values.append(value)

                # Recursively process nested objects (one level only)
                if value_type == "object" and not prefix:
                    self._process_document_attributes(
                        value, attributes, f"{attr_name}."
                    )

    def _get_value_type(self, value: Any) -> str:
        """Get type string for a value."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int) or isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "unknown"

    def _clean_sample_documents(
        self, documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Clean sample documents by removing system fields and large values."""
        cleaned = []

        for doc in documents:
            cleaned_doc = {}
            for key, value in doc.items():
                # Keep _key, _from, _to but not _id, _rev
                if key in ["_key", "_from", "_to"]:
                    cleaned_doc[key] = value
                elif not key.startswith("_"):
                    # Limit string length
                    if isinstance(value, str) and len(value) > 100:
                        cleaned_doc[key] = value[:100] + "..."
                    # Limit array/object size
                    elif isinstance(value, (list, dict)) and len(str(value)) > 200:
                        cleaned_doc[key] = (
                            f"<{type(value).__name__} - {len(value)} items>"
                        )
                    else:
                        cleaned_doc[key] = value

            cleaned.append(cleaned_doc)

        return cleaned

    def _extract_from_collections(self, edge_docs: List[Dict[str, Any]]) -> Set[str]:
        """Extract source collections from edge documents."""
        from_collections = set()

        for doc in edge_docs:
            if "_from" in doc:
                # _from format: "collection/key"
                collection_name = doc["_from"].split("/")[0]
                from_collections.add(collection_name)

        return from_collections

    def _extract_to_collections(self, edge_docs: List[Dict[str, Any]]) -> Set[str]:
        """Extract target collections from edge documents."""
        to_collections = set()

        for doc in edge_docs:
            if "_to" in doc:
                # _to format: "collection/key"
                collection_name = doc["_to"].split("/")[0]
                to_collections.add(collection_name)

        return to_collections

    def _extract_relationships(self, schema: GraphSchema) -> List[Relationship]:
        """Extract relationships between collections."""
        relationships = []

        for edge_col_name, edge_col in schema.edge_collections.items():
            # Create relationship for each from/to combination
            for from_col in edge_col.from_collections:
                for to_col in edge_col.to_collections:
                    # Try to determine relationship type from edge collection name
                    rel_type = self._guess_relationship_type(edge_col_name)

                    relationship = Relationship(
                        edge_collection=edge_col_name,
                        from_collection=from_col,
                        to_collection=to_col,
                        edge_count=edge_col.document_count,
                        relationship_type=rel_type,
                    )

                    relationships.append(relationship)

        return relationships

    def _guess_relationship_type(self, edge_col_name: str) -> Optional[str]:
        """
        Try to guess relationship type from edge collection name.

        Common patterns:
        - "user_follows_user" -> "FOLLOWS"
        - "product_categories" -> "IN_CATEGORY"
        - "knows" -> "KNOWS"
        """
        # Remove common prefixes/suffixes
        name = edge_col_name.lower()

        # Split on underscore
        parts = name.split("_")

        # Look for verb-like words in the middle
        verbs = ["follows", "knows", "likes", "purchased", "created", "owns", "belongs"]
        for verb in verbs:
            if verb in parts:
                return verb.upper()

        # If single word, use as-is
        if len(parts) == 1:
            return name.upper()

        # Otherwise, use middle part if 3 or more parts (fallback heuristic)
        if len(parts) >= 3:
            return parts[1].upper()

        return None


def create_extractor(
    endpoint: str,
    database: str,
    username: str = "root",
    password: str = "",
    verify_ssl: bool = True,
    sample_size: int = 100,
) -> SchemaExtractor:
    """
    Create a schema extractor with ArangoDB connection.

    Args:
        endpoint: ArangoDB endpoint (e.g., 'http://localhost:8529').
        database: Database name.
        username: Username (default: 'root').
        password: Password.
        verify_ssl: Whether to verify SSL certificates.
        sample_size: Number of documents to sample per collection.

    Returns:
        Configured SchemaExtractor instance.

    Example:
        >>> extractor = create_extractor(
        ...     endpoint='http://localhost:8529',
        ...     database='my_graph',
        ...     password='my_password'
        ... )
        >>> schema = extractor.extract()
    """
    client = ArangoClient(hosts=endpoint, verify_override=verify_ssl)
    db = client.db(database, username=username, password=password)

    return SchemaExtractor(db, sample_size=sample_size)
