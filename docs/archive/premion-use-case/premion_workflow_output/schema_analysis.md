================================================================================
GRAPH SCHEMA ANALYSIS REPORT
================================================================================

## Overview

**Database:** sharded_premion_graph
**Domain:** AdTech / Identity Resolution
**Complexity:** 7.5/10
  _(Complex graph structure)_

**Description:** This graph tracks digital advertising telemetry and identity resolution, mapping the relationships between user devices, network infrastructure, and content consumption. It connects devices to specific IP addresses, geographical locations, and the various mobile apps or websites they interact with, including the publishers and exchanges serving those ads.

## Statistics

- **Total Collections:** 17
- **Vertex Collections:** 10
- **Edge Collections:** 7
- **Total Documents:** 687,564
- **Total Edges:** 264,836
- **Relationships:** 11

## Key Entity Collections

- **Device**: 63,457 documents
  - Key attributes: _key, _id, _rev, device_id, device_type, user_agent
- **IP**: 58,980 documents
  - Key attributes: _key, _id, _rev, ip_address, zip3, is_high_cardinality
- **AppProduct**: 3,843 documents
  - Key attributes: _key, _id, _rev, bundle, name, store_url

## Key Relationships

- **SEEN_ON_IP**: 59,772 edges
  - Device → IP
- **SEEN_ON_APP**: 63,380 edges
  - Device → InstalledApp
- **INSTANCE_OF**: 68,636 edges
  - SiteUse → Site
  - SiteUse → AppProduct
  - InstalledApp → Site
  - InstalledApp → AppProduct

## Recommended Graph Analytics

1. **Household Clustering** (`community_detection`)
   - By analyzing devices that share common IP addresses and locations over time, the graph can group individual devices into household units for targeted advertising.

2. **Ad Fraud Detection** (`anomaly_detection`)
   - Identifying IP addresses with an unnaturally high frequency of unique devices or identifying devices seen across disparate geographical locations (zip3) in short timeframes to flag botnets or spoofing.

3. **Inventory Value Analysis** (`pagerank`)
   - Ranking AppProducts and Sites based on their centrality and device reach to determine which platforms are the most influential 'hubs' in the advertising ecosystem.

4. **Cross-Channel Attribution** (`pathfinding`)
   - Tracing paths from a Device through IPs to different SiteUse and InstalledApp instances to understand the multi-touch journey of a user across web and mobile platforms.

5. **Supply Chain Transparency** (`pattern_detection`)
   - Mapping the relationships between Publishers, AppProducts, and Exchanges to ensure ads are being served through authorized paths (similar to ads.txt validation).

## All Relationships

- AppProduct --[OWNED_BY]--> Publisher (4,135 edges)
- Site --[SERVED_BY]--> Exchange (5,496 edges)
- AppProduct --[SERVED_BY]--> Exchange (5,496 edges)
- SiteUse --[INSTANCE_OF]--> Site (68,636 edges)
- SiteUse --[INSTANCE_OF]--> AppProduct (68,636 edges)
- InstalledApp --[INSTANCE_OF]--> Site (68,636 edges)
- InstalledApp --[INSTANCE_OF]--> AppProduct (68,636 edges)
- Device --[SEEN_ON_SITE (ON)]--> SiteUse (5,256 edges)
- Device --[SEEN_ON_APP (ON)]--> InstalledApp (63,380 edges)
- IP --[LOCATED_IN]--> Location (58,161 edges)
- Device --[SEEN_ON_IP (ON)]--> IP (59,772 edges)

================================================================================