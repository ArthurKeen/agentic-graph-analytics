================================================================================
GRAPH SCHEMA ANALYSIS REPORT
================================================================================

## Overview

**Database:** sharded_premion_graph
**Domain:** Unknown (LLM analysis unavailable)
**Complexity:** 7.5/10
  _(Complex graph structure)_

**Description:** Graph database with 9 vertex collections, 7 edge collections, and 476,200 total documents. Top entities: Device (63,457 docs), InstalledApp (63,380 docs), IP (58,980 docs). (Note: LLM analysis failed: API error 404: {'message': 'No endpoints found for google/gemini-2.0-flash-001:free.', 'code': 404})

## Statistics

- **Total Collections:** 16
- **Vertex Collections:** 9
- **Edge Collections:** 7
- **Total Documents:** 476,200
- **Total Edges:** 264,836
- **Relationships:** 11

## Key Entity Collections

- **Device**: 63,457 documents
  - Key attributes: _key, _id, _rev, device_id, device_type, user_agent
- **InstalledApp**: 63,380 documents
  - Key attributes: _key, _id, _rev, app_id, zip3, bundle
- **IP**: 58,980 documents
  - Key attributes: _key, _id, _rev, ip_address, zip3, is_high_cardinality

## Key Relationships

- **INSTANCE_OF**: 68,636 edges
  - InstalledApp → AppProduct
  - InstalledApp → Site
  - SiteUse → AppProduct
  - SiteUse → Site
- **SEEN_ON_APP**: 63,380 edges
  - Device → InstalledApp
- **SEEN_ON_IP**: 59,772 edges
  - Device → IP

## All Relationships

- AppProduct --[OWNED_BY]--> Publisher (4,135 edges)
- AppProduct --[SERVED_BY]--> Exchange (5,496 edges)
- Site --[SERVED_BY]--> Exchange (5,496 edges)
- InstalledApp --[INSTANCE_OF]--> AppProduct (68,636 edges)
- InstalledApp --[INSTANCE_OF]--> Site (68,636 edges)
- SiteUse --[INSTANCE_OF]--> AppProduct (68,636 edges)
- SiteUse --[INSTANCE_OF]--> Site (68,636 edges)
- IP --[LOCATED_IN]--> Location (58,161 edges)
- Device --[SEEN_ON_APP (ON)]--> InstalledApp (63,380 edges)
- Device --[SEEN_ON_SITE (ON)]--> SiteUse (5,256 edges)
- Device --[SEEN_ON_IP (ON)]--> IP (59,772 edges)

================================================================================