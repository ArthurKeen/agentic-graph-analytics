"""
Create test data for GAE testing in ArangoDB AMP cluster.

This script creates a realistic e-commerce graph with:
- Users (customers)
- Products
- Categories
- Purchased edges (user bought product)
- Viewed edges (user viewed product)
- BelongsTo edges (product belongs to category)

Perfect for testing GAE analyses like PageRank, Louvain, shortest paths, etc.
"""

import random
from datetime import datetime, timedelta
from graph_analytics_ai.db_connection import get_db_connection


# Sample data for realistic generation
FIRST_NAMES = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia", "Mason",
    "Isabella", "William", "Mia", "James", "Charlotte", "Benjamin", "Amelia",
    "Lucas", "Harper", "Henry", "Evelyn", "Alexander", "Abigail", "Sebastian",
    "Emily", "Jack", "Elizabeth", "Michael", "Sofia", "Daniel", "Avery",
    "Owen", "Ella", "Matthew", "Scarlett", "Samuel", "Grace", "David", "Chloe",
    "Joseph", "Victoria", "Carter", "Riley", "Wyatt", "Aria", "John", "Luna"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White",
    "Harris", "Clark", "Lewis", "Robinson", "Walker", "Young", "Hall"
]

CATEGORIES = [
    {"name": "Electronics", "description": "Computers, phones, and gadgets"},
    {"name": "Clothing", "description": "Fashion and apparel"},
    {"name": "Books", "description": "Books and educational materials"},
    {"name": "Home & Kitchen", "description": "Home goods and kitchenware"},
    {"name": "Sports & Outdoors", "description": "Sports equipment and outdoor gear"},
    {"name": "Toys & Games", "description": "Toys, games, and hobbies"},
    {"name": "Beauty & Personal Care", "description": "Beauty and health products"},
    {"name": "Automotive", "description": "Car parts and accessories"},
]

PRODUCTS_BY_CATEGORY = {
    "Electronics": [
        ("Laptop Pro 15", 1299.99, "High-performance laptop"),
        ("Smartphone X", 899.99, "Latest flagship phone"),
        ("Wireless Earbuds", 149.99, "Premium audio quality"),
        ("4K Smart TV 55\"", 699.99, "Ultra HD television"),
        ("Tablet Air", 449.99, "Lightweight tablet"),
        ("Gaming Console", 499.99, "Next-gen gaming"),
        ("Smart Watch", 299.99, "Fitness and notifications"),
        ("Wireless Mouse", 49.99, "Ergonomic design"),
        ("Mechanical Keyboard", 89.99, "RGB backlit"),
        ("USB-C Hub", 39.99, "Multi-port adapter"),
    ],
    "Clothing": [
        ("Classic Jeans", 59.99, "Comfortable denim"),
        ("Cotton T-Shirt", 19.99, "Soft cotton blend"),
        ("Winter Jacket", 129.99, "Warm and stylish"),
        ("Running Shoes", 89.99, "Lightweight athletic"),
        ("Leather Belt", 34.99, "Genuine leather"),
        ("Casual Dress", 79.99, "Perfect for any occasion"),
        ("Wool Sweater", 69.99, "Cozy and warm"),
        ("Summer Shorts", 39.99, "Breathable fabric"),
        ("Sneakers", 79.99, "Casual footwear"),
        ("Formal Shirt", 49.99, "Professional attire"),
    ],
    "Books": [
        ("Python Programming", 44.99, "Learn Python from scratch"),
        ("Data Science Handbook", 54.99, "Practical data science"),
        ("The Great Novel", 24.99, "Bestselling fiction"),
        ("History of Innovation", 34.99, "Technology timeline"),
        ("Cooking Mastery", 29.99, "Professional recipes"),
        ("Business Strategy", 39.99, "Modern business tactics"),
        ("Self-Help Guide", 19.99, "Personal development"),
        ("Science Fiction Epic", 27.99, "Space adventure"),
        ("Biography Collection", 49.99, "Inspiring life stories"),
        ("Art History", 44.99, "Visual arts through time"),
    ],
    "Home & Kitchen": [
        ("Coffee Maker", 79.99, "Programmable brewing"),
        ("Blender Pro", 99.99, "High-speed blending"),
        ("Non-Stick Pan Set", 69.99, "Complete cookware"),
        ("Vacuum Cleaner", 149.99, "Powerful suction"),
        ("Air Purifier", 129.99, "Clean air technology"),
        ("Bedding Set Queen", 89.99, "Soft and comfortable"),
        ("Kitchen Knife Set", 59.99, "Professional quality"),
        ("Dish Set 16-Piece", 79.99, "Elegant dinnerware"),
        ("Storage Containers", 34.99, "Organize your space"),
        ("Table Lamp", 44.99, "Modern lighting"),
    ],
    "Sports & Outdoors": [
        ("Yoga Mat", 29.99, "Non-slip surface"),
        ("Camping Tent 4-Person", 199.99, "Weather-resistant"),
        ("Bicycle Mountain", 449.99, "All-terrain cycling"),
        ("Dumbbell Set", 89.99, "Home fitness"),
        ("Hiking Backpack", 79.99, "Durable and spacious"),
        ("Fishing Rod", 69.99, "Professional grade"),
        ("Soccer Ball", 24.99, "Official size"),
        ("Golf Club Set", 399.99, "Complete set"),
        ("Running Shorts", 34.99, "Moisture-wicking"),
        ("Water Bottle", 19.99, "Insulated"),
    ],
    "Toys & Games": [
        ("Building Blocks 500pc", 49.99, "Creative construction"),
        ("Board Game Classic", 34.99, "Family fun"),
        ("RC Car Racing", 89.99, "Remote control"),
        ("Puzzle 1000 Pieces", 24.99, "Challenging and fun"),
        ("Action Figure Set", 44.99, "Collectible toys"),
        ("Dollhouse Deluxe", 129.99, "Complete playset"),
        ("Educational Robot", 79.99, "Learn coding"),
        ("Art Supply Kit", 39.99, "Creative materials"),
        ("Card Game Collection", 29.99, "Multiple games"),
        ("Science Experiment Kit", 49.99, "Hands-on learning"),
    ],
    "Beauty & Personal Care": [
        ("Skincare Set", 59.99, "Complete routine"),
        ("Hair Dryer Pro", 89.99, "Salon quality"),
        ("Makeup Palette", 44.99, "Versatile colors"),
        ("Electric Toothbrush", 79.99, "Deep cleaning"),
        ("Perfume Designer", 69.99, "Luxurious scent"),
        ("Shaving Kit", 34.99, "Professional shave"),
        ("Nail Care Set", 24.99, "Complete manicure"),
        ("Body Lotion", 19.99, "Moisturizing"),
        ("Face Masks 10-Pack", 29.99, "Hydrating treatment"),
        ("Hair Styling Tools", 99.99, "Professional results"),
    ],
    "Automotive": [
        ("Car Phone Mount", 24.99, "Secure holder"),
        ("Dash Camera", 79.99, "HD recording"),
        ("Floor Mats Set", 49.99, "All-weather protection"),
        ("Tire Pressure Gauge", 14.99, "Digital display"),
        ("Car Vacuum", 59.99, "Portable cleaning"),
        ("Jump Starter", 89.99, "Emergency power"),
        ("Seat Covers", 69.99, "Custom fit"),
        ("Car Charger", 19.99, "Fast charging"),
        ("Steering Wheel Cover", 24.99, "Comfortable grip"),
        ("Tool Kit", 39.99, "Emergency repairs"),
    ],
}


def create_test_data(num_users=100, num_interactions=500):
    """
    Create test data in the ArangoDB cluster.
    
    Args:
        num_users: Number of user vertices to create (default: 100)
        num_interactions: Number of purchase/view edges (default: 500)
    
    Returns:
        dict: Statistics about created data
    """
    print("=" * 60)
    print("Creating Test Data for GAE Testing")
    print("=" * 60)
    print()
    
    db = get_db_connection()
    stats = {
        "users": 0,
        "products": 0,
        "categories": 0,
        "purchased": 0,
        "viewed": 0,
        "belongs_to": 0,
    }
    
    # Create collections
    print("1. Creating collections...")
    
    # Vertex collections
    if not db.has_collection("users"):
        db.create_collection("users")
    users_coll = db.collection("users")
    
    if not db.has_collection("products"):
        db.create_collection("products")
    products_coll = db.collection("products")
    
    if not db.has_collection("categories"):
        db.create_collection("categories")
    categories_coll = db.collection("categories")
    
    # Edge collections
    if not db.has_collection("purchased"):
        db.create_collection("purchased", edge=True)
    purchased_coll = db.collection("purchased")
    
    if not db.has_collection("viewed"):
        db.create_collection("viewed", edge=True)
    viewed_coll = db.collection("viewed")
    
    if not db.has_collection("belongs_to"):
        db.create_collection("belongs_to", edge=True)
    belongs_to_coll = db.collection("belongs_to")
    
    print("   ✓ Collections created")
    print()
    
    # Create categories
    print("2. Creating categories...")
    category_keys = {}
    for cat in CATEGORIES:
        doc = categories_coll.insert({
            "name": cat["name"],
            "description": cat["description"],
            "created_at": datetime.utcnow().isoformat()
        })
        category_keys[cat["name"]] = doc["_key"]
        stats["categories"] += 1
    
    print(f"   ✓ Created {stats['categories']} categories")
    print()
    
    # Create products
    print("3. Creating products...")
    product_keys = []
    for category_name, products in PRODUCTS_BY_CATEGORY.items():
        for product_name, price, description in products:
            # Create product
            product_doc = products_coll.insert({
                "name": product_name,
                "price": price,
                "description": description,
                "category": category_name,
                "stock": random.randint(10, 100),
                "rating": round(random.uniform(3.5, 5.0), 1),
                "created_at": datetime.utcnow().isoformat()
            })
            product_keys.append(product_doc["_key"])
            stats["products"] += 1
            
            # Create belongs_to edge
            belongs_to_coll.insert({
                "_from": f"products/{product_doc['_key']}",
                "_to": f"categories/{category_keys[category_name]}",
                "created_at": datetime.utcnow().isoformat()
            })
            stats["belongs_to"] += 1
    
    print(f"   ✓ Created {stats['products']} products")
    print(f"   ✓ Created {stats['belongs_to']} belongs_to edges")
    print()
    
    # Create users
    print("4. Creating users...")
    user_keys = []
    for i in range(num_users):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        
        doc = users_coll.insert({
            "username": f"{first_name.lower()}{last_name.lower()}{i}",
            "email": f"{first_name.lower()}.{last_name.lower()}{i}@example.com",
            "first_name": first_name,
            "last_name": last_name,
            "age": random.randint(18, 70),
            "location": random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]),
            "member_since": (datetime.utcnow() - timedelta(days=random.randint(30, 730))).isoformat(),
            "total_spent": 0,  # Will be updated
        })
        user_keys.append(doc["_key"])
        stats["users"] += 1
    
    print(f"   ✓ Created {stats['users']} users")
    print()
    
    # Create interactions (purchases and views)
    print("5. Creating user interactions...")
    
    # Purchases (realistic shopping patterns)
    for _ in range(num_interactions):
        user_key = random.choice(user_keys)
        product_key = random.choice(product_keys)
        
        # Get product to know the price
        product = products_coll.get(product_key)
        
        # Create purchase
        purchase_date = datetime.utcnow() - timedelta(days=random.randint(0, 180))
        purchased_coll.insert({
            "_from": f"users/{user_key}",
            "_to": f"products/{product_key}",
            "quantity": random.randint(1, 3),
            "price_paid": product["price"],
            "purchased_at": purchase_date.isoformat(),
        })
        stats["purchased"] += 1
        
        # Update user's total spent
        user = users_coll.get(user_key)
        user["total_spent"] = user.get("total_spent", 0) + product["price"]
        users_coll.update({"_key": user_key, "total_spent": user["total_spent"]})
    
    # Views (more views than purchases - realistic)
    for _ in range(num_interactions * 3):
        user_key = random.choice(user_keys)
        product_key = random.choice(product_keys)
        
        viewed_coll.insert({
            "_from": f"users/{user_key}",
            "_to": f"products/{product_key}",
            "duration_seconds": random.randint(5, 300),
            "viewed_at": (datetime.utcnow() - timedelta(days=random.randint(0, 90))).isoformat(),
        })
        stats["viewed"] += 1
    
    print(f"   ✓ Created {stats['purchased']} purchase edges")
    print(f"   ✓ Created {stats['viewed']} view edges")
    print()
    
    # Create a named graph
    print("6. Creating named graph...")
    try:
        if db.has_graph("ecommerce_graph"):
            db.delete_graph("ecommerce_graph")
        
        db.create_graph(
            name="ecommerce_graph",
            edge_definitions=[
                {
                    "edge_collection": "purchased",
                    "from_vertex_collections": ["users"],
                    "to_vertex_collections": ["products"]
                },
                {
                    "edge_collection": "viewed",
                    "from_vertex_collections": ["users"],
                    "to_vertex_collections": ["products"]
                },
                {
                    "edge_collection": "belongs_to",
                    "from_vertex_collections": ["products"],
                    "to_vertex_collections": ["categories"]
                }
            ]
        )
        print("   ✓ Created 'ecommerce_graph' named graph")
    except Exception as e:
        print(f"   ⚠ Graph creation: {e}")
    
    print()
    print("=" * 60)
    print("✅ Test Data Creation Complete!")
    print("=" * 60)
    print()
    print("📊 Statistics:")
    print(f"   Users:       {stats['users']:>5}")
    print(f"   Products:    {stats['products']:>5}")
    print(f"   Categories:  {stats['categories']:>5}")
    print(f"   Purchased:   {stats['purchased']:>5} edges")
    print(f"   Viewed:      {stats['viewed']:>5} edges")
    print(f"   Belongs_to:  {stats['belongs_to']:>5} edges")
    print(f"   Total edges: {stats['purchased'] + stats['viewed'] + stats['belongs_to']:>5}")
    print()
    print("🎯 Perfect for GAE Analyses:")
    print("   • PageRank - Find influential products")
    print("   • Louvain - Discover customer communities")
    print("   • Shortest Path - Product recommendation paths")
    print("   • Betweenness - Key connector products")
    print("   • k-Core - Dense purchasing patterns")
    print()
    
    return stats


if __name__ == "__main__":
    # Create test data
    stats = create_test_data(
        num_users=100,      # 100 customers
        num_interactions=500  # 500 purchases, 1500 views
    )
    
    print("Next steps:")
    print("1. Review the data in ArangoDB UI")
    print("2. Test schema extraction with AI")
    print("3. Continue with Phase 7 - Template Generation")

