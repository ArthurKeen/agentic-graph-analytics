"""
Algorithm-specific insight patterns for common graph analytics scenarios.

Provides templates for detecting and explaining common patterns in each algorithm.
"""

from typing import Dict, List, Callable, Any

EDA_SPEC_COLLECTIONS = {"Chunk", "Golden_Entity"}
EDA_RTL_PREFIXES = ("RTL_", "FSM_")


def _collection_from_vertex_id(vertex_id: str) -> str:
    if not vertex_id:
        return ""
    if "/" in vertex_id:
        return vertex_id.split("/", 1)[0]
    # Some datasets store bare _key; return empty so callers handle gracefully
    return ""


def detect_wcc_eda_ic_design_patterns(
    results: List[Dict[str, Any]], total_nodes: int
) -> List[Dict[str, Any]]:
    """
    Detect IC/EDA-specific WCC patterns.

    Primary goals:
    - Orphaned spec islands (Chunk/Golden_Entity components with no RTL membership)
    - Unexpected fragmentation across RTL blocks
    """
    patterns: List[Dict[str, Any]] = []
    if not results:
        return patterns

    # Group by component id
    components: Dict[Any, List[Dict[str, Any]]] = {}
    for r in results:
        comp = r.get("component")
        components.setdefault(comp, []).append(r)

    component_sizes = [(cid, len(nodes)) for cid, nodes in components.items()]
    component_sizes.sort(key=lambda x: x[1], reverse=True)

    # Pattern: orphaned spec islands
    orphan_islands: List[Dict[str, Any]] = []
    for cid, nodes in components.items():
        cols = {_collection_from_vertex_id(n.get("id", "")) for n in nodes}
        cols.discard("")
        has_rtl = any(c.startswith(EDA_RTL_PREFIXES) for c in cols)
        has_spec = bool(cols & EDA_SPEC_COLLECTIONS)
        if has_spec and not has_rtl:
            orphan_islands.append(
                {"component_id": cid, "size": len(nodes), "cols": cols}
            )

    orphan_islands.sort(key=lambda x: x["size"], reverse=True)
    if orphan_islands:
        largest = orphan_islands[0]
        total_orphan_nodes = sum(x["size"] for x in orphan_islands)
        pct = (total_orphan_nodes / total_nodes * 100) if total_nodes else 0
        risk = "HIGH" if pct >= 5 or largest["size"] >= 1000 else "MEDIUM"
        patterns.append(
            {
                "type": "orphaned_spec_islands",
                "risk_level": risk,
                "title": f"Traceability Gap: {total_orphan_nodes:,} Spec Nodes in Orphan Components ({pct:.1f}% of WCC sample)",
                "description": (
                    f"Detected {len(orphan_islands)} spec-only connected components (Chunk/Golden_Entity) with no RTL membership. "
                    f"Largest orphan component {largest['component_id']} has {largest['size']:,} nodes. "
                    "This indicates missing/failed RESOLVED_TO semantic bridges, reducing spec→RTL traceability and increasing retrieval noise."
                ),
                "business_impact": (
                    "SHORT-TERM: Add/repair RESOLVED_TO bridges for top requirements/spec entities. "
                    "LONG-TERM: Improve extraction to emit stable RTL identifiers for linking and measure bridge coverage per release."
                ),
                "confidence": 0.8,
                "supporting_data": {
                    "orphan_component_count": len(orphan_islands),
                    "orphan_node_count": total_orphan_nodes,
                    "largest_orphan_component": largest,
                },
            }
        )

    # Pattern: unexpected integration fragmentation (RTL-only small components)
    rtl_only_components = 0
    isolated_rtl_modules = 0
    for cid, nodes in components.items():
        cols = {_collection_from_vertex_id(n.get("id", "")) for n in nodes}
        cols.discard("")
        if cols and all(c.startswith(EDA_RTL_PREFIXES) for c in cols):
            # Count RTL-only components that are small
            if len(nodes) <= 5:
                rtl_only_components += 1
            # Count isolated RTL_Module nodes specifically
            if len(nodes) == 1:
                only = nodes[0]
                if _collection_from_vertex_id(only.get("id", "")) == "RTL_Module":
                    isolated_rtl_modules += 1

    if rtl_only_components >= 25 or isolated_rtl_modules >= 10:
        patterns.append(
            {
                "type": "unexpected_integration_fragmentation",
                "risk_level": "MEDIUM",
                "title": f"Integration Fragmentation: {rtl_only_components} Small RTL-Only Components (incl. {isolated_rtl_modules} isolated RTL_Modules)",
                "description": (
                    "The RTL subgraph is fragmented into many small connected components. This often indicates missing edges in extraction "
                    "(e.g., instantiation/wiring not captured) or incomplete integration of reused IP blocks."
                ),
                "business_impact": (
                    "IMMEDIATE: Validate extraction on representative RTL modules and ensure CONTAINS/HAS_PORT/HAS_SIGNAL/connection edges are emitted. "
                    "Add missing structural relationships to restore connectivity for analytics."
                ),
                "confidence": 0.7,
                "supporting_data": {
                    "small_rtl_only_components": rtl_only_components,
                    "isolated_rtl_modules": isolated_rtl_modules,
                },
            }
        )

    return patterns


def detect_pagerank_eda_ic_design_patterns(
    results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Detect IC/EDA-specific PageRank patterns from ranked nodes.

    Notes:
    - Ownership/bus-factor checks require joining to Author/GitCommit subgraph and are handled elsewhere.
    """
    patterns: List[Dict[str, Any]] = []
    if not results or len(results) < 10:
        return patterns

    sorted_results = sorted(results, key=lambda x: x.get("rank", 0), reverse=True)
    ranks = [
        r.get("rank", 0)
        for r in sorted_results
        if isinstance(r.get("rank"), (int, float))
    ]
    if not ranks or max(ranks) == 0:
        return patterns

    top_20 = sorted_results[:20]
    top_cols = [_collection_from_vertex_id(r.get("id", "")) for r in top_20]
    top_cols = [c for c in top_cols if c]
    port_signal_count = sum(1 for c in top_cols if c in ("RTL_Port", "RTL_Signal"))

    # Pattern: interface chokepoints (ports/signals dominate top ranks)
    if port_signal_count >= 10:
        patterns.append(
            {
                "type": "interface_chokepoint_ports_signals",
                "risk_level": "HIGH",
                "title": f"Interface Chokepoints: {port_signal_count}/20 of Top PageRank Nodes are Ports/Signals",
                "description": (
                    "A large fraction of the highest-ranked nodes are RTL_Port/RTL_Signal types, indicating interface hubs and global wires. "
                    "These are common blast-radius amplifiers and debug bottlenecks."
                ),
                "business_impact": (
                    "SHORT-TERM: Add assertions/coverage at the top-ranked interfaces. "
                    "LONG-TERM: Refactor to reduce fan-out or introduce isolation wrappers/protocol boundaries."
                ),
                "confidence": 0.75,
                "supporting_data": {
                    "top_collections": top_cols,
                    "port_signal_top20": port_signal_count,
                },
            }
        )

    # Pattern: high concentration (few nodes dominate influence)
    total_rank = sum(ranks)
    top_10_rank = sum(r.get("rank", 0) for r in sorted_results[:10])
    top_10_pct = (top_10_rank / total_rank * 100) if total_rank else 0
    if top_10_pct > 50:
        patterns.append(
            {
                "type": "high_concentration",
                "risk_level": "MEDIUM",
                "title": f"Blast Radius Concentration: Top 10 Nodes Account for {top_10_pct:.1f}% of Total PageRank",
                "description": (
                    "Influence is highly concentrated in a small set of nodes. In IC/EDA graphs, this often indicates a few core IP blocks or global nets "
                    "that dominate dependency and traceability flow."
                ),
                "business_impact": (
                    "PRIORITIZE: Treat these nodes as critical IP. Ensure secondary maintainers, documentation bridges, and targeted regression coverage."
                ),
                "confidence": 0.7,
                "supporting_data": {
                    "top_10_pct": top_10_pct,
                    "top_10": sorted_results[:10],
                },
            }
        )

    return patterns


def detect_scc_eda_ic_design_patterns(
    results: List[Dict[str, Any]], total_nodes: int
) -> List[Dict[str, Any]]:
    """
    Detect IC/EDA-specific SCC patterns as a proxy for cyclic dependency risk.
    """
    patterns: List[Dict[str, Any]] = []
    if not results:
        return patterns

    # Group by SCC component
    components: Dict[Any, List[Dict[str, Any]]] = {}
    for r in results:
        comp = r.get("component")
        components.setdefault(comp, []).append(r)
    sizes = sorted((len(nodes) for nodes in components.values()), reverse=True)
    if not sizes:
        return patterns

    largest = sizes[0]
    largest_pct = (largest / total_nodes * 100) if total_nodes else 0
    if largest_pct >= 10 and largest >= 50:
        patterns.append(
            {
                "type": "cross_ip_dependency_cycle",
                "risk_level": "HIGH" if largest_pct >= 25 else "MEDIUM",
                "title": f"Cyclic Core Risk: Largest SCC has {largest:,} nodes ({largest_pct:.1f}% of SCC sample)",
                "description": (
                    "A large strongly-connected core indicates cyclic dependencies and tightly coupled subgraphs. "
                    "This is an architectural risk amplifier and often correlates with expensive verification/debug loops."
                ),
                "business_impact": (
                    "SHORT-TERM: Identify the boundary nodes/interfaces of the dominant SCC and add targeted regression tests. "
                    "LONG-TERM: Break cycles with clearer ownership boundaries or staged control/backpressure redesign."
                ),
                "confidence": 0.7,
                "supporting_data": {
                    "largest_scc_size": largest,
                    "largest_scc_pct": largest_pct,
                },
            }
        )

    return patterns


# WCC Pattern Detection for Ad-Tech
def detect_wcc_adtech_patterns(
    results: List[Dict[str, Any]], total_nodes: int
) -> List[Dict[str, Any]]:
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
        patterns.append(
            {
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
                "confidence": 0.85,
            }
        )

    # Pattern 2: High fragmentation (poor resolution)
    singleton_count = sum(1 for _, size in component_sizes if size == 1)
    fragmentation_pct = (
        (singleton_count / len(component_sizes) * 100) if component_sizes else 0
    )

    if fragmentation_pct > 50:
        patterns.append(
            {
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
                "confidence": 0.88,
            }
        )

    # Pattern 3: Ideal household distribution
    household_sized = sum(1 for _, size in component_sizes if 3 <= size <= 18)
    household_pct = (
        (household_sized / len(component_sizes) * 100) if component_sizes else 0
    )

    if household_pct > 60:
        patterns.append(
            {
                "type": "healthy_distribution",
                "household_count": household_sized,
                "household_pct": household_pct,
                "risk_level": "LOW",
                "title": f"Healthy Household Distribution: {household_pct:.1f}% Within Expected Range",
                "description": f"{household_sized} components ({household_pct:.1f}%) fall within typical household size "
                f"range (3-18 devices). This indicates good identity resolution quality with balanced clustering.",
                "business_impact": f"POSITIVE: High-quality identity graph enables accurate cross-device targeting and attribution. "
                f"MAINTAIN: Current clustering parameters are working well.",
                "confidence": 0.90,
            }
        )

    return patterns


# PageRank Pattern Detection for Ad-Tech
def detect_pagerank_adtech_patterns(
    results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
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
        patterns.append(
            {
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
                "confidence": 0.92,
            }
        )

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
            patterns.append(
                {
                    "type": "node_type_skew",
                    "dominant_type": dominant_type,
                    "count": dominant_count,
                    "risk_level": "MEDIUM" if dominant_type == "IP" else "LOW",
                    "title": f"Top-10 Dominated by {dominant_type} Nodes ({dominant_count}/10)",
                    "description": f"{dominant_count} out of top 10 nodes are {dominant_type} type. "
                    f"For attribution and inventory analysis, expect {dominant_type}s to be central hubs.",
                    "business_impact": (
                        f"INSIGHT: {dominant_type} nodes are primary attribution bridges. "
                        f"{'WARNING: If IPs dominate, validate data quality (IPs should not outrank content/apps).' if dominant_type == 'IP' else 'EXPECTED: Site/App nodes as top influencers indicates healthy network structure.'}"
                    ),
                    "confidence": 0.80,
                }
            )

    return patterns


# WCC Pattern Detection for Fraud Intelligence (Indian Banking)
def detect_wcc_fraud_patterns(
    results: List[Dict[str, Any]], total_nodes: int
) -> List[Dict[str, Any]]:
    """Detect common WCC patterns in fraud/AML networks."""
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

    # Pattern 1: Money mule network (large connected component)
    largest_comp_id, largest_size = component_sizes[0]
    largest_pct = (largest_size / total_nodes * 100) if total_nodes > 0 else 0

    if largest_size > 20 and largest_pct > 15:
        patterns.append(
            {
                "type": "mule_network",
                "component_id": largest_comp_id,
                "size": largest_size,
                "percentage": largest_pct,
                "risk_level": "CRITICAL" if largest_size > 50 else "HIGH",
                "title": f"Suspected Money Mule Network: {largest_size} Connected Accounts",
                "description": f"Component {largest_comp_id} contains {largest_size} interconnected accounts ({largest_pct:.1f}% of network). "
                f"This topology is consistent with money mule or smurfing operations where multiple accounts are "
                f"coordinated to move funds. In Indian banking fraud, mule networks typically involve 20-100 accounts "
                f"controlled by the same entity to structure transactions below CTR thresholds (₹10 Lakhs).",
                "business_impact": f"RISK: Structured transaction / CTR evasion. REGULATORY: File STR with FIU-IND immediately. "
                f"INVESTIGATION: Map account relationships, identify hub accounts, trace fund flows. "
                f"IMMEDIATE ACTION: Enhanced monitoring on all {largest_size} accounts, freeze high-risk nodes.",
                "confidence": 0.82,
            }
        )

    # Pattern 2: Benami identity clusters (post-entity resolution)
    medium_clusters = [size for _, size in component_sizes if 3 <= size <= 8]
    if len(medium_clusters) >= 5:
        avg_cluster = sum(medium_clusters) / len(medium_clusters)
        patterns.append(
            {
                "type": "benami_clusters",
                "cluster_count": len(medium_clusters),
                "avg_size": avg_cluster,
                "risk_level": "HIGH",
                "title": f"Benami Identity Clusters Detected: {len(medium_clusters)} Proxy Networks",
                "description": f"Found {len(medium_clusters)} identity clusters with 3-8 entities each (avg: {avg_cluster:.1f}). "
                f"This pattern suggests Benami transactions where the same individual operates multiple accounts "
                f"through proxies, relatives, or shell companies. After entity resolution, these clusters reveal "
                f"hidden beneficial ownership and control structures typical of Indian banking fraud.",
                "business_impact": f"COMPLIANCE: Benami Transactions (Prohibition) Act violation. Update KYC to reflect beneficial "
                f"ownership. RISK: Layering schemes, tax evasion, circular trading. RECOMMENDATION: Consolidate "
                f"risk scores across resolved identities, file Enhanced Due Diligence reports.",
                "confidence": 0.78,
            }
        )

    # Pattern 3: Isolated high-risk individuals
    singleton_count = sum(1 for _, size in component_sizes if size == 1)
    if singleton_count > 0:
        singleton_pct = (
            (singleton_count / len(component_sizes) * 100) if component_sizes else 0
        )
        patterns.append(
            {
                "type": "isolated_actors",
                "singleton_count": singleton_count,
                "singleton_pct": singleton_pct,
                "risk_level": "MEDIUM",
                "title": f"{singleton_count} Isolated High-Risk Entities Identified",
                "description": f"{singleton_count} entities operate independently without detected connections ({singleton_pct:.1f}% of components). "
                f"These may be: (1) Early-stage fraud not yet connected to networks, (2) Sophisticated actors "
                f"maintaining operational security, or (3) False positives from static rules. Requires individual assessment.",
                "business_impact": f"MONITORING: Flag for enhanced surveillance. INVESTIGATION: Review transaction patterns for each isolated "
                f"entity. May represent early-stage fraud or sophisticated actors. PRIORITY: Focus on watchlist matches first.",
                "confidence": 0.65,
            }
        )

    return patterns


# PageRank Pattern Detection for Fraud Intelligence
def detect_pagerank_fraud_patterns(
    results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Detect common PageRank patterns in fraud/transaction networks."""
    patterns = []

    if not results or len(results) < 3:
        return patterns

    # Sort by rank
    sorted_results = sorted(results, key=lambda x: x.get("rank", 0), reverse=True)
    ranks = [r.get("rank", 0) for r in sorted_results]

    if not ranks or max(ranks) == 0:
        return patterns

    # Pattern 1: Transaction hub (money aggregator)
    top_rank = ranks[0]
    median_rank = ranks[len(ranks) // 2] if len(ranks) > 0 else 0

    if top_rank > median_rank * 10 and top_rank > 0.05:
        top_entity = sorted_results[0]
        patterns.append(
            {
                "type": "transaction_hub",
                "entity_id": top_entity.get("id", "unknown"),
                "rank": top_rank,
                "multiplier": top_rank / median_rank if median_rank > 0 else 0,
                "risk_level": "CRITICAL",
                "title": f"Transaction Hub Detected: Entity {top_entity.get('id', 'unknown')[:20]} - PageRank {top_rank:.4f}",
                "description": f"Entity {top_entity.get('id', 'unknown')} has exceptional network centrality with PageRank {top_rank:.4f}, "
                f"which is {(top_rank / median_rank):.1f}x the median ({median_rank:.4f}). In fraud networks, this pattern "
                f"indicates a hub account that aggregates funds from multiple sources (money mule hub) or distributes funds "
                f"(layering operation). High PageRank in transaction networks reveals accounts that are critical nodes in "
                f"money flow operations.",
                "business_impact": f"IMMEDIATE: Freeze account and review all inbound/outbound transactions. INVESTIGATION: Map complete "
                f"transaction history, identify all counterparties, calculate total volume. REGULATORY: File STR if total "
                f"volume suggests structuring. HIGH PRIORITY: This is likely the control account in a mule network or "
                f"layering scheme.",
                "confidence": 0.88,
            }
        )

    # Pattern 2: Concentration risk (top 5 accounts)
    if len(sorted_results) >= 5:
        top_5_sum = sum(ranks[:5])
        total_sum = sum(ranks)
        concentration = (top_5_sum / total_sum * 100) if total_sum > 0 else 0

        if concentration > 50:
            patterns.append(
                {
                    "type": "concentration",
                    "top_5_ids": [
                        r.get("id", "unknown")[:20] for r in sorted_results[:5]
                    ],
                    "concentration_pct": concentration,
                    "risk_level": "HIGH",
                    "title": f"Transaction Concentration: Top 5 Accounts Control {concentration:.1f}% of Network Activity",
                    "description": f"The top 5 accounts by PageRank control {concentration:.1f}% of total network influence. "
                    f"Combined PageRank: {top_5_sum:.4f} out of {total_sum:.4f}. This extreme concentration indicates "
                    f"that a small number of accounts dominate money flows. In fraud scenarios, this suggests a "
                    f"coordinated operation with central control points.",
                    "business_impact": f"INVESTIGATION: These 5 accounts are critical to the operation. Investigate relationships between them. "
                    f"RISK: If these accounts are compromised or involved in fraud, exposure is significant. "
                    f"MONITORING: Flag all 5 accounts for real-time transaction monitoring.",
                    "confidence": 0.85,
                }
            )

    # Pattern 3: Flat distribution (normal behavior indicator)
    if len(ranks) >= 10:
        top_10_pct = sum(ranks[:10]) / sum(ranks) * 100 if sum(ranks) > 0 else 0
        if top_10_pct < 25:
            patterns.append(
                {
                    "type": "normal_distribution",
                    "top_10_pct": top_10_pct,
                    "risk_level": "LOW",
                    "title": f"Normal Transaction Distribution: Top 10 Accounts Represent {top_10_pct:.1f}% of Activity",
                    "description": f"PageRank distribution is relatively flat with top 10 accounts accounting for only {top_10_pct:.1f}% "
                    f"of network activity. This indicates decentralized transaction patterns consistent with normal "
                    f"business operations rather than coordinated fraud.",
                    "business_impact": f"POSITIVE: Low fraud risk from network topology perspective. MAINTAIN: Continue standard monitoring "
                    f"protocols. FOCUS: Shift investigative resources to components with concentration patterns.",
                    "confidence": 0.90,
                }
            )

    return patterns


# Pattern Registry
ALGORITHM_PATTERNS: Dict[str, Dict[str, Callable]] = {
    "wcc": {
        "adtech": detect_wcc_adtech_patterns,
        "fraud_intelligence": detect_wcc_fraud_patterns,
        "fraud": detect_wcc_fraud_patterns,
        "aml": detect_wcc_fraud_patterns,
        "indian_banking": detect_wcc_fraud_patterns,
        "eda_ic_design": detect_wcc_eda_ic_design_patterns,
        "eda": detect_wcc_eda_ic_design_patterns,
    },
    "pagerank": {
        "adtech": detect_pagerank_adtech_patterns,
        "fraud_intelligence": detect_pagerank_fraud_patterns,
        "fraud": detect_pagerank_fraud_patterns,
        "aml": detect_pagerank_fraud_patterns,
        "indian_banking": detect_pagerank_fraud_patterns,
        "eda_ic_design": detect_pagerank_eda_ic_design_patterns,
        "eda": detect_pagerank_eda_ic_design_patterns,
    },
    "scc": {
        "eda_ic_design": detect_scc_eda_ic_design_patterns,
        "eda": detect_scc_eda_ic_design_patterns,
    },
}


def detect_patterns(
    algorithm: str, industry: str, results: List[Dict[str, Any]], **kwargs
) -> List[Dict[str, Any]]:
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

    # Provide common context automatically when not explicitly passed.
    # This keeps ReportGenerator integration simple while supporting detectors
    # that rely on global metrics like total node count.
    try:
        import inspect

        params = inspect.signature(detector).parameters
        if "total_nodes" in params and "total_nodes" not in kwargs:
            kwargs["total_nodes"] = len(results or [])
    except Exception:
        pass

    return detector(results, **kwargs)
