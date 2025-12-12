# Test Data Summary

**Created:** December 12, 2025  
**Cluster:** AMP with GAE enabled  
**Database:** graph-analytics-ai

## Overview

E-commerce graph with realistic data for testing GAE analytics.

## Data Model

### Vertex Collections (715 vertices)
- **users** (500) - Customer accounts with demographics
- **products** (200) - Product catalog with pricing and ratings
- **categories** (15) - Product categories

### Edge Collections (6,499 edges)
- **purchased** (1,500) - User purchases with quantity and price
- **viewed** (3,000) - Product views with duration
- **rated** (1,000) - Product ratings and reviews
- **follows** (799) - User-to-user social connections
- **belongs_to** (200) - Product-to-category associations

### Graph Structure
- **Named Graph:** `ecommerce_graph`
- **Average Degree:** 18.18 (well-connected)
- **Graph Density:** 1.27%

## Use Cases Enabled

### 1. PageRank
- Find influential users (heavy purchasers, many followers)
- Identify popular products (many views/purchases)

### 2. Community Detection (Louvain)
- Customer segmentation
- Product clusters
- Market basket analysis

### 3. Shortest Path
- Product recommendation paths
- User influence chains
- Category navigation

### 4. Centrality Analysis
- Key influencers
- Hub products
- Bridge users

### 5. Pattern Matching
- Purchase patterns
- User behavior flows
- Cross-sell opportunities

## Sample Queries

### Find Top Users by Connections
```aql
FOR user IN users
  LET purchases = LENGTH(
    FOR v, e IN 1..1 OUTBOUND user purchased
    RETURN 1
  )
  LET views = LENGTH(
    FOR v, e IN 1..1 OUTBOUND user viewed
    RETURN 1
  )
  SORT purchases + views DESC
  LIMIT 10
  RETURN {
    user: user.username,
    purchases: purchases,
    views: views,
    total_activity: purchases + views
  }
```

### Find Popular Products
```aql
FOR product IN products
  LET purchase_count = LENGTH(
    FOR v, e IN 1..1 INBOUND product purchased
    RETURN 1
  )
  LET view_count = LENGTH(
    FOR v, e IN 1..1 INBOUND product viewed
    RETURN 1
  )
  SORT purchase_count DESC
  LIMIT 10
  RETURN {
    product: product.name,
    purchases: purchase_count,
    views: view_count,
    price: product.price,
    rating: product.rating
  }
```

### Find User Communities
```aql
FOR user IN users
  LET followers = (
    FOR v IN 1..1 INBOUND user follows
    RETURN v.username
  )
  LET following = (
    FOR v IN 1..1 OUTBOUND user follows
    RETURN v.username
  )
  FILTER LENGTH(followers) > 2 OR LENGTH(following) > 2
  RETURN {
    user: user.username,
    followers: LENGTH(followers),
    following: LENGTH(following)
  }
```

## GAE Analysis Templates

Ready to test with:
- PageRank on users/products
- Louvain community detection
- Betweenness centrality
- K-shortest paths

## Regenerating Data

To recreate the data:
```bash
python scripts/create_test_data.py
```

The script will:
1. Delete existing graph and collections
2. Create fresh collections
3. Populate with randomized realistic data
4. Link relationships

## Notes

- All data is synthetic but realistic
- User ages: 18-75
- Product prices: $9.99-$999.99
- Product ratings: 3.0-5.0 stars
- Purchase history: 0-180 days
- View history: 0-30 days

