# Premion WCC Household Identity Resolution - Results & Insights

**Generated**: 2025-12-17 16:51:11

## Executive Summary

Weakly Connected Components (WCC) analysis identified **122,437 distinct households** from Device and IP connections in the Premion graph.

### Key Metrics

- **Total Households**: 122,437
- **Largest Household**: 17 nodes
- **Avg Top-20 Size**: 9.0 nodes
- **Analysis Duration**: 95.6 seconds

## Top 20 Largest Households

| Rank | Component ID | Size (Devices/IPs) |
|------|--------------|--------------------|
| 1 | `Device/000:ba08a816d80b25ceacb6f7e9679e954a` | 17 |
| 2 | `Device/000:c2b0aeaa58934d984551c42a7fc1fadc` | 16 |
| 3 | `Device/900:6edda83af4f30fd9470c61acb6514e06` | 11 |
| 4 | `Device/900:89b41ffa4b89d8bada0b0b56940156a6` | 11 |
| 5 | `Device/201:6b059e00-d2b4-3802-de34-c8ab6cf21569` | 11 |
| 6 | `Device/549:1aae874d12fc60c077b6eb42b2aec3b0` | 11 |
| 7 | `Device/000:50b138d9810277188b1ea2fe2b2d21ae` | 10 |
| 8 | `Device/000:2fb3482e6ed7a1d6bbc4745f91b231a8` | 9 |
| 9 | `Device/554:e66d533f19c3477303f71ef12baceb2d` | 9 |
| 10 | `IP/000:44.203.166.0` | 8 |
| 11 | `Device/981:ef94a3a0c8e9e200866c7536643cdacb` | 8 |
| 12 | `IP/531:207.242.23.14` | 8 |
| 13 | `Device/850:7c03385d4cc82cdb02f7ae3a06dc23ab` | 7 |
| 14 | `IP/951:146.75.154.1` | 7 |
| 15 | `Device/951:e4cb065739b41767f74c7f3eab0c4077` | 7 |
| 16 | `Device/000:7b1ad6297a51beb752f82f535becd668` | 6 |
| 17 | `Device/978:b480b111-bd76-4409-a601-a47bfabf844a` | 6 |
| 18 | `IP/606:140.248.30.1` | 6 |
| 19 | `IP/462:146.75.128.1` | 6 |
| 20 | `Device/201:7381e768fdb5dea6e3306b724c5a92b3` | 6 |

## Business Insights

### 1. Multi-Device Households

**20** of the top 20 households contain multiple devices, enabling cross-device targeting and attribution.

### 2. Commercial IP Detection

### 3. Identity Resolution Success

The algorithm successfully stitched devices sharing residential IPs into household clusters, enabling "Given Device X, find all devices in household" queries.

## Sample Queries

### Query 1: Find All Devices in a Household

```aql
// Given device ID: 26100401
LET deviceComponent = (
    FOR doc IN household_components
        FILTER doc._id == "Device/26100401"
        RETURN doc.component_id
)[0]

FOR doc IN household_components
    FILTER doc.component_id == deviceComponent
    FILTER STARTS_WITH(doc._id, "Device/")
    RETURN doc._key
```

### Query 2: Multi-Device Households

```aql
FOR doc IN household_components
    COLLECT component = doc.component_id WITH COUNT INTO size
    FILTER size >= 2
    SORT size DESC
    LIMIT 100
    RETURN {
        household_id: component,
        device_count: size
    }
```

## Recommendations

1. **Filter Commercial IPs**: Apply degree centrality filter (>20 connections)
2. **Enable Cross-Device Campaigns**: Target all devices in household clusters
3. **Attribution Modeling**: Use household_id for cross-device attribution
4. **Audience Extension**: Propagate segments across household devices

