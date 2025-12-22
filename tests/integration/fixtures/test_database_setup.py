"""
Database setup utilities for integration tests.

Creates and manages test databases with sample data.
"""

import os
from arango import ArangoClient
from typing import Dict, Any


def create_test_database(
    endpoint: str = None,
    username: str = "root",
    password: str = None,
    database_name: str = "graph-analytics-ai-test",
) -> Dict[str, Any]:
    """
    Create test database with sample graph data.

    Args:
        endpoint: ArangoDB endpoint (defaults to env var)
        username: Database username
        password: Database password (defaults to env var)
        database_name: Name for test database

    Returns:
        Dictionary with connection info and statistics
    """
    endpoint = endpoint or os.getenv("ARANGO_ENDPOINT", "http://localhost:8529")
    password = password or os.getenv("ARANGO_PASSWORD")

    if not password:
        raise ValueError("Database password required")

    # Connect to ArangoDB
    client = ArangoClient(hosts=endpoint)
    sys_db = client.db("_system", username=username, password=password)

    # Delete test database if it exists
    if sys_db.has_database(database_name):
        sys_db.delete_database(database_name)
        print(f"Deleted existing test database: {database_name}")

    # Create test database
    sys_db.create_database(database_name)
    print(f"Created test database: {database_name}")

    db = client.db(database_name, username=username, password=password)

    # Create collections
    stats = {}

    # Vertex collections
    customers = db.create_collection("customers")
    products = db.create_collection("products")
    categories = db.create_collection("categories")

    # Edge collections
    purchased = db.create_collection("purchased", edge=True)
    viewed = db.create_collection("viewed", edge=True)
    belongs_to = db.create_collection("belongs_to", edge=True)
    similar_to = db.create_collection("similar_to", edge=True)

    # Insert sample data

    # Categories
    cat_data = [
        {"_key": "electronics", "name": "Electronics"},
        {"_key": "books", "name": "Books"},
        {"_key": "clothing", "name": "Clothing"},
    ]
    categories.insert_many(cat_data)
    stats["categories"] = len(cat_data)

    # Products
    product_data = [
        {"_key": f"prod_{i}", "name": f"Product {i}", "price": 10 + i * 5}
        for i in range(1, 51)
    ]
    products.insert_many(product_data)
    stats["products"] = len(product_data)

    # Customers
    customer_data = [
        {
            "_key": f"cust_{i}",
            "name": f"Customer {i}",
            "email": f"customer{i}@example.com",
        }
        for i in range(1, 101)
    ]
    customers.insert_many(customer_data)
    stats["customers"] = len(customer_data)

    # Product categories
    belongs_data = (
        [
            {"_from": f"products/prod_{i}", "_to": "categories/electronics"}
            for i in range(1, 17)
        ]
        + [
            {"_from": f"products/prod_{i}", "_to": "categories/books"}
            for i in range(17, 34)
        ]
        + [
            {"_from": f"products/prod_{i}", "_to": "categories/clothing"}
            for i in range(34, 51)
        ]
    )
    belongs_to.insert_many(belongs_data)
    stats["product_categories"] = len(belongs_data)

    # Customer purchases (create graph structure)
    purchase_data = []
    for cust_id in range(1, 101):
        # Each customer purchases 2-5 products
        num_purchases = (cust_id % 4) + 2
        for prod_offset in range(num_purchases):
            prod_id = ((cust_id + prod_offset) % 50) + 1
            purchase_data.append(
                {
                    "_from": f"customers/cust_{cust_id}",
                    "_to": f"products/prod_{prod_id}",
                    "quantity": (prod_offset % 3) + 1,
                    "timestamp": f"2024-01-{(cust_id % 28) + 1:02d}",
                }
            )
    purchased.insert_many(purchase_data)
    stats["purchases"] = len(purchase_data)

    # Customer views (more than purchases)
    view_data = []
    for cust_id in range(1, 101):
        # Each customer views 5-10 products
        num_views = (cust_id % 6) + 5
        for view_offset in range(num_views):
            prod_id = ((cust_id + view_offset) % 50) + 1
            view_data.append(
                {
                    "_from": f"customers/cust_{cust_id}",
                    "_to": f"products/prod_{prod_id}",
                    "timestamp": f"2024-01-{(cust_id % 28) + 1:02d}",
                }
            )
    viewed.insert_many(view_data)
    stats["views"] = len(view_data)

    # Product similarities
    similar_data = []
    for i in range(1, 50):
        # Connect each product to next 2 products
        for offset in [1, 2]:
            j = ((i + offset - 1) % 50) + 1
            similar_data.append(
                {
                    "_from": f"products/prod_{i}",
                    "_to": f"products/prod_{j}",
                    "similarity_score": 0.7 + (offset * 0.1),
                }
            )
    similar_to.insert_many(similar_data)
    stats["product_similarities"] = len(similar_data)

    # Create named graph
    graph_def = {
        "name": "ecommerce_graph",
        "edgeDefinitions": [
            {"collection": "purchased", "from": ["customers"], "to": ["products"]},
            {"collection": "viewed", "from": ["customers"], "to": ["products"]},
            {"collection": "belongs_to", "from": ["products"], "to": ["categories"]},
            {"collection": "similar_to", "from": ["products"], "to": ["products"]},
        ],
    }

    if not db.has_graph("ecommerce_graph"):
        db.create_graph(**graph_def)
        print("Created named graph: ecommerce_graph")

    print("\nTest database setup complete!")
    print(f"Statistics: {stats}")

    return {
        "endpoint": endpoint,
        "database": database_name,
        "username": username,
        "stats": stats,
    }


def cleanup_test_database(
    endpoint: str = None,
    username: str = "root",
    password: str = None,
    database_name: str = "graph-analytics-ai-test",
):
    """
    Delete test database.

    Args:
        endpoint: ArangoDB endpoint
        username: Database username
        password: Database password
        database_name: Name of database to delete
    """
    endpoint = endpoint or os.getenv("ARANGO_ENDPOINT", "http://localhost:8529")
    password = password or os.getenv("ARANGO_PASSWORD")

    if not password:
        raise ValueError("Database password required")

    client = ArangoClient(hosts=endpoint)
    sys_db = client.db("_system", username=username, password=password)

    if sys_db.has_database(database_name):
        sys_db.delete_database(database_name)
        print(f"Deleted test database: {database_name}")
    else:
        print(f"Test database does not exist: {database_name}")


if __name__ == "__main__":
    # Run as script to setup test database
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        cleanup_test_database()
    else:
        create_test_database()
