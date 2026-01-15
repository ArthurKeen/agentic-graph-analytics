"""
Algorithm-specific insight patterns for common graph analytics scenarios.

Provides templates for detecting and explaining common patterns in each algorithm.
"""

from typing import Dict, List, Callable, Any


# WCC Pattern Detection for Ad-Tech
def detect_wcc_adtech_patterns(results: List[Dict[str, Any]], total_nodes: int) -> List[Dict[str, Any]]:
    """Detect common WCC patterns in ad-tech identity resolution."""
    patterns = []
    
    if not results:
        return patterns
    
    # Group by component
    components = {}
    for result in results:
        comp_id = result.get("component")
        if comp_id not in components:
            components[comp_id] = []
        components[comp_id].append(result)
    
    component_sizes = [(comp_id, len(nodes)) for comp_id, nodes in components.items()]
    component_sizes.sort(key=lambda x: x[1], reverse=True)
    
    if not component_sizes:
        return patterns
    
    # Pattern 1: Single dominant cluster (over-aggregation risk)
    largest_comp_id, largest_size = component_sizes[0]
    largest_pct = (largest_size / total_nodes * 100) if total_nodes > 0 else 0
    
    if largest_pct > 40:
        patterns.append({
            "type": "over_aggregation",
            "component_id": largest_comp_id,
            "size": largest_size,
            "percentage": largest_pct,
            "risk_level": "HIGH" if largest_pct > 60 else "MEDIUM",
            "title": f"Over-Aggregation Risk: Single Component Contains {largest_pct:.1f}% of Nodes",
            "description": f"Component {largest_comp_id} dominates with {largest_size} nodes ({largest_pct:.1f}% of graph). "
                          f"In ad-tech identity resolution, this often indicates a shared public IP or publisher site "
                          f"incorrectly bridging multiple households. Expected max cluster size: 15-20 devices per household.",
            "business_impact": f"RISK: False household aggregation affecting attribution accuracy. "
                             f"ACTION: Audit bridge nodes in component {largest_comp_id}. "
                             f"If Site/Publisher node is the bridge, exclude from household clustering.",
            "confidence": 0.85
        })
    
    # Pattern 2: High fragmentation (poor resolution)
    singleton_count = sum(1 for _, size in component_sizes if size == 1)
    fragmentation_pct = (singleton_count / len(component_sizes) * 100) if component_sizes else 0
    
    if fragmentation_pct > 50:
        patterns.append({
            "type": "fragmentation",
            "singleton_count": singleton_count,
            "total_components": len(component_sizes),
            "fragmentation_pct": fragmentation_pct,
            "risk_level": "HIGH" if fragmentation_pct > 70 else "MEDIUM",
            "title": f"Poor Identity Resolution: {fragmentation_pct:.1f}% Fragmentation Rate",
            "description": f"{singleton_count} singleton components out of {len(component_sizes)} total "
                          f"({fragmentation_pct:.1f}% fragmentation). High fragmentation indicates missing identity signals "
                          f"or insufficient temporal window. Only {100 - fragmentation_pct:.1f}% of devices successfully "
                          f"resolved to multi-device households.",
            "business_impact": f"DATA QUALITY: Low cross-device coverage reduces attribution and targeting accuracy. "
                             f"RECOMMENDATION: Extend clustering temporal window from 2 to 4 weeks, validate IP collection, "
                             f"add secondary identity signals (device fingerprints, user IDs).",
            "confidence": 0.88
        })
    
    # Pattern 3: Ideal household distribution
    household_sized = sum(1 for _, size in component_sizes if 3 <= size <= 18)
    household_pct = (household_sized / len(component_sizes) * 100) if component_sizes else 0
    
    if household_pct > 60:
        patterns.append({
            "type": "healthy_distribution",
            "household_count": household_sized,
            "household_pct": household_pct,
            "risk_level": "LOW",
            "title": f"Healthy Household Distribution: {household_pct:.1f}% Within Expected Range",
            "description": f"{household_sized} components ({household_pct:.1f}%) fall within typical household size "
                          f"range (3-18 devices). This indicates good identity resolution quality with balanced clustering.",
            "business_impact": f"POSITIVE: High-quality identity graph enables accurate cross-device targeting and attribution. "
                             f"MAINTAIN: Current clustering parameters are working well.",
            "confidence": 0.90
        })
    
    return patterns


# PageRank Pattern Detection for Ad-Tech
def detect_pagerank_adtech_patterns(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect common PageRank patterns in ad-tech networks."""
    patterns = []
    
    if not results or len(results) < 10:
        return patterns
    
    # Sort by rank
    sorted_results = sorted(results, key=lambda x: x.get("rank", 0), reverse=True)
    top_10 = sorted_results[:10]
    
    # Calculate total PageRank
    total_rank = sum(r.get("rank", 0) for r in results)
    top_10_rank = sum(r.get("rank", 0) for r in top_10)
    top_10_pct = (top_10_rank / total_rank * 100) if total_rank > 0 else 0
    
    # Pattern 1: High concentration (good for targeting)
    if top_10_pct > 60:
        top_node = top_10[0]
        patterns.append({
            "type": "high_concentration",
            "top_10_percentage": top_10_pct,
            "top_node_id": top_node.get("_key"),
            "top_node_rank": top_node.get("rank"),
            "risk_level": "LOW",
            "title": f"Premium Inventory Concentration: Top 10 Nodes Control {top_10_pct:.1f}% of Influence",
            "description": f"Top 10 nodes account for {top_10_pct:.1f}% of total PageRank. "
                          f"Leader: {top_node.get('_key')} with rank {top_node.get('rank', 0):.4f}. "
                          f"High concentration indicates clear premium inventory opportunities.",
            "business_impact": f"TARGETING: Focus campaigns on top 10 nodes for maximum reach. "
                             f"FORECAST: {top_10_pct:.0f}% delivery confidence within these environments. "
                             f"PRICING: Premium CPM justified for top-ranked inventory.",
            "confidence": 0.92
        })
    
    # Pattern 2: Node type analysis
    node_types = {}
    for node in top_10:
        node_key = node.get("_key", "")
        if "/" in node_key:
            node_type = node_key.split("/")[0]
            node_types[node_type] = node_types.get(node_type, 0) + 1
    
    if node_types:
        dominant_type = max(node_types, key=node_types.get)
        dominant_count = node_types[dominant_type]
        
        if dominant_type in ["IP", "Site"] and dominant_count >= 7:
            patterns.append({
                "type": "node_type_skew",
                "dominant_type": dominant_type,
                "count": dominant_count,
                "risk_level": "MEDIUM" if dominant_type == "IP" else "LOW",
                "title": f"Top-10 Dominated by {dominant_type} Nodes ({dominant_count}/10)",
                "description": f"{dominant_count} out of top 10 nodes are {dominant_type} type. "
                              f"For attribution and inventory analysis, expect {dominant_type}s to be central hubs.",
                "business_impact": f"INSIGHT: {dominant_type} nodes are primary attribution bridges. "
                                 f"{'WARNING: If IPs dominate, validate data quality (IPs should not outrank content/apps).'
                                    if dominant_type == 'IP' else 
                                    'EXPECTED: Site/App nodes as top influencers indicates healthy network structure.'}",
                "confidence": 0.80
            })
    
    return patterns


# Pattern Registry
ALGORITHM_PATTERNS: Dict[str, Dict[str, Callable]] = {
    "wcc": {
        "adtech": detect_wcc_adtech_patterns,
    },
    "pagerank": {
        "adtech": detect_pagerank_adtech_patterns,
    },
}


def detect_patterns(algorithm: str, industry: str, results: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
    """
    Detect algorithm and industry-specific patterns in results.
    
    Args:
        algorithm: Algorithm name (e.g., "wcc", "pagerank")
        industry: Industry identifier (e.g., "adtech", "fintech")
        results: Analysis results
        **kwargs: Additional context (e.g., total_nodes for WCC)
    
    Returns:
        List of detected patterns with titles, descriptions, and business impacts
    """
    if algorithm not in ALGORITHM_PATTERNS:
        return []
    
    if industry not in ALGORITHM_PATTERNS[algorithm]:
        return []
    
    detector = ALGORITHM_PATTERNS[algorithm][industry]
    return detector(results, **kwargs)
