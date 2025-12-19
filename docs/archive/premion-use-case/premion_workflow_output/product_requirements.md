# Product Requirements Document

## 1. Overview

**Product:** Premion Identity Graph Analytics
**Domain:** Digital Advertising / AdTech
**Documents analyzed:** 1

The documents outline five key business use cases for Premion to implement a 'stitched identity' graph using ArangoDB’s Graph Analytics Engine (GAE). The primary focus is on resolving household identities (PHID) from disjointed device and IP data to improve ad targeting, fraud detection, and attribution modeling.

## 2. Objectives

- **OBJ-001 – Household Identity Resolution** (critical)
  - Create a foundational 'stitched' view of households from disjointed device and IP data.
  - Success criteria: Successful creation of PHIDs for grouped devices
  - Related requirements: REQ-001, REQ-002, REQ-007
- **OBJ-002 – Anomaly & Fraud Detection** (high)
  - Automatically flag and filter out non-residential IPs to prevent wasted ad spend and diluted attribution.
  - Success criteria: Reduction in commercial IP inclusion in household clusters; Identification of IPs with Degree > 20
  - Related requirements: REQ-003
- **OBJ-003 – Behavioral Look-alike Segmentation** (medium)
  - Increase inventory value by extending targetable attributes to all devices in a household cluster.
  - Success criteria: Successful propagation of 'segment_interest' attributes across PHIDs
  - Related requirements: REQ-004
- **OBJ-004 – Cross-Device Attribution** (high)
  - Prove campaign ROI by tracing the path of influence from TV impressions to mobile conversions.
  - Success criteria: Confirmation of 'is_attributed' boolean via shortest path analysis
  - Related requirements: REQ-005
- **OBJ-005 – Inventory Influence Scoring** (medium)
  - Understand which apps and channels act as primary gateways for audiences to optimize pricing and delivery.
  - Success criteria: Generation of 'authority_rank' for content nodes
  - Related requirements: REQ-006

## 3. Requirements

- **REQ-001** [critical] (functional)
  - The system must identify distinct connected components (subgraphs) representing a single 'Premion Household' (PHID) using Weakly Connected Components (WCC).
  - Stakeholders: Premion
- **REQ-002** [critical] (functional)
  - The system must be able to find all devices in the same household given a specific device ID.
  - Stakeholders: Premion, Advertisers
- **REQ-007** [critical] (technical)
  - The system must support the creation of a 'stitched identity' graph using ArangoDB's Graph Analytics Engine (GAE).
  - Stakeholders: Premion
- **REQ-003** [high] (functional)
  - The system must flag and filter high-cardinality IP nodes (e.g., airports, universities, bot farms) using Degree Centrality to distinguish commercial from residential networks.
  - Stakeholders: Premion, Advertisers
- **REQ-005** [high] (functional)
  - The system must determine cross-device attribution by calculating the shortest path between an impression event on one device and a conversion event on another device within a household.
  - Stakeholders: Advertisers
- **REQ-004** [medium] (functional)
  - The system must propagate behavioral labels (e.g., audience segments) from specific devices to all other devices within the same household cluster using Label Propagation (LPA).
  - Stakeholders: Premion, Advertisers
- **REQ-006** [medium] (functional)
  - The system must assign importance scores to App and Channel nodes using PageRank to identify primary audience gateways and forecast inventory value.
  - Stakeholders: Premion, Managed service clients

## 4. Stakeholders

- **Premion** (Service Provider) – Premion
  - Interests: Identity resolution, Inventory pricing, Fraud prevention, Managed service delivery
  - Requirements: REQ-001, REQ-002, REQ-003, REQ-004, REQ-006, REQ-007
- **Advertisers** (Customers) – Various
  - Interests: Campaign ROI, Cross-device attribution, Targeting accuracy, Reducing ad spend waste
  - Requirements: REQ-002, REQ-003, REQ-004, REQ-005
- **Managed service clients** (Business Partners) – Various
  - Interests: Inventory forecasting, Delivery prediction
  - Requirements: REQ-006

## 5. Constraints

- Must utilize ArangoDB’s Graph Analytics Engine (GAE) algorithms (WCC, PageRank, etc.)
- Identification of households relies on devices connecting to the same residential IP within specific time windows
- Shortest Path attribution is limited to paths within N hops

## 6. Risks

- High-cardinality IPs (e.g., public Wi-Fi) could lead to incorrect household stitching if not correctly filtered
- Data sparsity in App or Channel usage may affect the accuracy of audience propagation
- Attribution models may be overly simplified if they rely solely on graph hop distance

## 7. Graph Schema (Summary)

- Vertex collections: 10 (SiteUse, Exchange, household_components, AppProduct, InstalledApp, Site, Location, Publisher, IP, Device)
- Edge collections: 7 (OWNED_BY, SERVED_BY, INSTANCE_OF, SEEN_ON_SITE, SEEN_ON_APP, LOCATED_IN, SEEN_ON_IP)
- Total documents: 687,564
- Total edges: 264,836
- Domain: AdTech / Identity Resolution
- Complexity: 7.5/10
- Key entities: Device, IP, AppProduct
- Key relationships: SEEN_ON_IP, SEEN_ON_APP, INSTANCE_OF
- Suggested analyses: Household Clustering, Ad Fraud Detection, Inventory Value Analysis, Cross-Channel Attribution, Supply Chain Transparency
