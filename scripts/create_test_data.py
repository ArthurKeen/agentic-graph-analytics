"""
Create test data for GAE testing on ArangoDB cluster.

This script creates a realistic e-commerce graph with:
- Users (customers)
- Products
- Categories
- Relationships: purchased, viewed, rated, follows, belongs_to

Perfect for testing:
- PageRank (influential users/products)
- Community Detection (customer segments, product clusters)
- Shortest Path (product recommendations)
- Centrality (key influencers)
"""

import random
from datetime import datetime, timedelta
from graph_analytics_ai.db_connection import get_db_connection


def create_test_data():
    """Create comprehensive test data for GAE testing."""
    
    print("=" * 70)
    print("Creating Test Data for GAE Analytics")
    print("=" * 70)
    print()
    
    # Connect to database
    print("📡 Connecting to ArangoDB...")
    db = get_db_connection()
    print("   ✓ Connected!")
    print()
    
    # Configuration
    NUM_USERS = 500
    NUM_PRODUCTS = 200
    NUM_CATEGORIES = 15
    NUM_PURCHASES = 1500
    NUM_VIEWS = 3000
    NUM_RATINGS = 1000
    NUM_FOLLOWS = 800
    
    print("📊 Data Configuration:")
    print(f"   - Users: {NUM_USERS}")
    print(f"   - Products: {NUM_PRODUCTS}")
    print(f"   - Categories: {NUM_CATEGORIES}")
    print(f"   - Purchases: {NUM_PURCHASES}")
    print(f"   - Views: {NUM_VIEWS}")
    print(f"   - Ratings: {NUM_RATINGS}")
    print(f"   - Follows: {NUM_FOLLOWS}")
    print()
    
    # ========================================================================
    # 1. Clean up existing data
    # ========================================================================
    print("1️⃣  Cleaning up existing data...")
    
    # Delete graph first (if exists)
    graph_name = 'ecommerce_graph'
    if db.has_graph(graph_name):
        db.delete_graph(graph_name, drop_collections=True)
        print(f"   ✓ Deleted existing graph: {graph_name}")
    
    print()
    
    # ========================================================================
    # 2. Create Collections
    # ========================================================================
    print("2️⃣  Creating collections...")
    
    # Vertex collections
    collections_to_create = {
        'users': {'type': 'vertex', 'description': 'Customer accounts'},
        'products': {'type': 'vertex', 'description': 'Product catalog'},
        'categories': {'type': 'vertex', 'description': 'Product categories'},
    }
    
    # Edge collections
    edges_to_create = {
        'purchased': {'type': 'edge', 'from': 'users', 'to': 'products'},
        'viewed': {'type': 'edge', 'from': 'users', 'to': 'products'},
        'rated': {'type': 'edge', 'from': 'users', 'to': 'products'},
        'follows': {'type': 'edge', 'from': 'users', 'to': 'users'},
        'belongs_to': {'type': 'edge', 'from': 'products', 'to': 'categories'},
    }
    
    # Create vertex collections
    for coll_name, info in collections_to_create.items():
        if not db.has_collection(coll_name):
            db.create_collection(coll_name)
            print(f"   ✓ Created {coll_name} ({info['description']})")
        else:
            print(f"   ✓ Using existing {coll_name} ({info['description']})")
    
    # Create edge collections
    for edge_name, info in edges_to_create.items():
        if not db.has_collection(edge_name):
            db.create_collection(edge_name, edge=True)
            print(f"   ✓ Created {edge_name} (edge)")
        else:
            print(f"   ✓ Using existing {edge_name} (edge)")
    
    print()
    
    # ========================================================================
    # 3. Create Graph
    # ========================================================================
    print("3️⃣  Creating named graph...")
    
    graph = db.create_graph(graph_name)
    
    # Add edge definitions
    for edge_name, info in edges_to_create.items():
        from_colls = [info['from']]
        to_colls = [info['to']]
        graph.create_edge_definition(
            edge_collection=edge_name,
            from_vertex_collections=from_colls,
            to_vertex_collections=to_colls
        )
    
    print(f"   ✓ Created graph: {graph_name}")
    print()
    
    # ========================================================================
    # 4. Populate Categories
    # ========================================================================
    print("4️⃣  Creating categories...")
    
    category_names = [
        'Electronics', 'Clothing', 'Books', 'Home & Garden', 'Sports',
        'Toys', 'Beauty', 'Automotive', 'Food', 'Health',
        'Music', 'Movies', 'Games', 'Tools', 'Office'
    ]
    
    categories = db.collection('categories')
    category_keys = []
    
    for i, name in enumerate(category_names):
        doc = {
            '_key': f'cat_{i}',
            'name': name,
            'description': f'{name} products and accessories',
            'created_at': datetime.now().isoformat()
        }
        categories.insert(doc)
        category_keys.append(f'cat_{i}')
    
    print(f"   ✓ Created {len(category_keys)} categories")
    print()
    
    # ========================================================================
    # 5. Populate Products
    # ========================================================================
    print("5️⃣  Creating products...")
    
    product_prefixes = [
        'Premium', 'Deluxe', 'Pro', 'Ultra', 'Super', 'Mega', 'Smart',
        'Classic', 'Modern', 'Vintage', 'Eco', 'Digital', 'Wireless'
    ]
    
    product_suffixes = [
        'Widget', 'Gadget', 'Device', 'Tool', 'Kit', 'Set', 'Bundle',
        'System', 'Solution', 'Package', 'Collection', 'Series'
    ]
    
    products = db.collection('products')
    belongs_to = db.collection('belongs_to')
    product_keys = []
    
    for i in range(NUM_PRODUCTS):
        prefix = random.choice(product_prefixes)
        suffix = random.choice(product_suffixes)
        
        doc = {
            '_key': f'prod_{i}',
            'name': f'{prefix} {suffix} {i}',
            'price': round(random.uniform(9.99, 999.99), 2),
            'stock': random.randint(0, 500),
            'rating': round(random.uniform(3.0, 5.0), 1),
            'created_at': (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat()
        }
        products.insert(doc)
        product_keys.append(f'prod_{i}')
        
        # Link to category
        category_key = random.choice(category_keys)
        belongs_to.insert({
            '_from': f'products/{doc["_key"]}',
            '_to': f'categories/{category_key}',
            'created_at': datetime.now().isoformat()
        })
    
    print(f"   ✓ Created {len(product_keys)} products")
    print("   ✓ Linked products to categories")
    print()
    
    # ========================================================================
    # 6. Populate Users
    # ========================================================================
    print("6️⃣  Creating users...")
    
    first_names = [
        'James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda',
        'William', 'Barbara', 'David', 'Elizabeth', 'Richard', 'Susan', 'Joseph', 'Jessica',
        'Thomas', 'Sarah', 'Charles', 'Karen', 'Daniel', 'Nancy', 'Matthew', 'Lisa'
    ]
    
    last_names = [
        'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
        'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
        'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Thompson', 'White'
    ]
    
    users = db.collection('users')
    user_keys = []
    
    for i in range(NUM_USERS):
        first = random.choice(first_names)
        last = random.choice(last_names)
        
        doc = {
            '_key': f'user_{i}',
            'username': f'{first.lower()}.{last.lower()}{i}',
            'email': f'{first.lower()}.{last.lower()}{i}@example.com',
            'first_name': first,
            'last_name': last,
            'age': random.randint(18, 75),
            'member_since': (datetime.now() - timedelta(days=random.randint(0, 1095))).isoformat(),
            'total_spent': 0.0,
            'purchase_count': 0
        }
        users.insert(doc)
        user_keys.append(f'user_{i}')
    
    print(f"   ✓ Created {len(user_keys)} users")
    print()
    
    # ========================================================================
    # 7. Create User-Product Relationships
    # ========================================================================
    print("7️⃣  Creating user-product relationships...")
    
    # Purchases
    print("   📦 Creating purchases...")
    purchased = db.collection('purchased')
    for _ in range(NUM_PURCHASES):
        user_key = random.choice(user_keys)
        product_key = random.choice(product_keys)
        
        purchased.insert({
            '_from': f'users/{user_key}',
            '_to': f'products/{product_key}',
            'quantity': random.randint(1, 5),
            'price_paid': round(random.uniform(9.99, 999.99), 2),
            'purchased_at': (datetime.now() - timedelta(days=random.randint(0, 180))).isoformat()
        })
    print(f"      ✓ Created {NUM_PURCHASES} purchases")
    
    # Views
    print("   👁️  Creating product views...")
    viewed = db.collection('viewed')
    for _ in range(NUM_VIEWS):
        user_key = random.choice(user_keys)
        product_key = random.choice(product_keys)
        
        viewed.insert({
            '_from': f'users/{user_key}',
            '_to': f'products/{product_key}',
            'viewed_at': (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
            'duration_seconds': random.randint(5, 300)
        })
    print(f"      ✓ Created {NUM_VIEWS} views")
    
    # Ratings
    print("   ⭐ Creating product ratings...")
    rated = db.collection('rated')
    for _ in range(NUM_RATINGS):
        user_key = random.choice(user_keys)
        product_key = random.choice(product_keys)
        
        rated.insert({
            '_from': f'users/{user_key}',
            '_to': f'products/{product_key}',
            'rating': random.randint(1, 5),
            'review': random.choice([
                'Great product!',
                'Excellent quality',
                'Would recommend',
                'Not bad',
                'Could be better',
                'Amazing!',
                'Perfect for my needs'
            ]),
            'rated_at': (datetime.now() - timedelta(days=random.randint(0, 90))).isoformat()
        })
    print(f"      ✓ Created {NUM_RATINGS} ratings")
    
    # Follows (user-to-user)
    print("   👥 Creating user follows...")
    follows = db.collection('follows')
    for _ in range(NUM_FOLLOWS):
        user1_key = random.choice(user_keys)
        user2_key = random.choice(user_keys)
        
        if user1_key != user2_key:  # Can't follow yourself
            follows.insert({
                '_from': f'users/{user1_key}',
                '_to': f'users/{user2_key}',
                'followed_at': (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat()
            })
    print(f"      ✓ Created {NUM_FOLLOWS} follows")
    
    print()
    
    # ========================================================================
    # 8. Summary
    # ========================================================================
    print("=" * 70)
    print("✅ Test Data Creation Complete!")
    print("=" * 70)
    print()
    
    # Get final counts
    print("📊 Final Statistics:")
    print("   Vertices:")
    print(f"      • Users: {db.collection('users').count()}")
    print(f"      • Products: {db.collection('products').count()}")
    print(f"      • Categories: {db.collection('categories').count()}")
    print()
    print("   Edges:")
    print(f"      • Purchased: {db.collection('purchased').count()}")
    print(f"      • Viewed: {db.collection('viewed').count()}")
    print(f"      • Rated: {db.collection('rated').count()}")
    print(f"      • Follows: {db.collection('follows').count()}")
    print(f"      • Belongs To: {db.collection('belongs_to').count()}")
    print()
    
    total_vertices = (db.collection('users').count() + 
                      db.collection('products').count() + 
                      db.collection('categories').count())
    total_edges = (db.collection('purchased').count() + 
                   db.collection('viewed').count() + 
                   db.collection('rated').count() + 
                   db.collection('follows').count() + 
                   db.collection('belongs_to').count())
    
    print(f"   Total Vertices: {total_vertices:,}")
    print(f"   Total Edges: {total_edges:,}")
    print(f"   Graph Density: {total_edges / (total_vertices * (total_vertices - 1)):.4%}")
    print()
    
    print("🎯 Use Cases Enabled:")
    print("   • PageRank - Find influential users and popular products")
    print("   • Community Detection - Discover customer segments")
    print("   • Shortest Path - Product recommendation paths")
    print("   • Centrality - Identify key influencers")
    print("   • Pattern Matching - Discover purchase patterns")
    print()
    
    print("🚀 Ready for GAE Analytics Testing!")
    print()


if __name__ == '__main__':
    create_test_data()

