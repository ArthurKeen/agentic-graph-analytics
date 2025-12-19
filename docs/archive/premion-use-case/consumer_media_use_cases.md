Based on the Premion requirements, data structure, and the capabilities of ArangoDB’s Graph Analytics Engine (GAE), here is a set of developed business use cases. These use cases map Premion’s goal of creating a "stitched identity" graph to specific algorithms available in the GAE (like WCC, Label Propagation, and Centrality) to demonstrate value during the PoC.

### 1. Household Identity Resolution (The "Stitched" View)
**Business Description & Value:**
This is the foundational use case for Premion. The raw data consists of disjointed `Device` and `IP` nodes. The goal is to identify distinct connected components that represent a single "Premion Household" (PHID).
*   **Value:** Enables the creation of the `phid` (Premion Household ID). By grouping all devices (TVs, mobiles, tablets) that connect to the same residential IP within a specific time window, Premion can target ads to a whole household rather than disjointed devices. This supports the core requirement of "Given a device, find all devices in the same household".
*   **Algorithms Used:**
    *   **Weakly Connected Components (WCC):** This algorithm traverses the graph to find all subgraphs where every node is reachable from every other node (ignoring edge direction). In the Premion context, if `Device A` connected to `IP 1`, and `Device B` connected to `IP 1`, WCC labels them all with the same Component ID, which becomes the candidate Household ID.

### 2. Anomaly & Fraud Detection (Commercial vs. Residential Filtering)
**Business Description & Value:**
Premion needs to distinguish between true residential households and "high-cardinality IPs" such as airports, coffee shops, universities, or bot farms. Targeting a commercial IP as a household wastes ad spend and dilutes attribution models.
*   **Value:** automatically flags and filters out non-residential IPs. If an IP node connects to thousands of unique devices in a 24-hour window, it is likely a public network or fraud bot, not a household.
*   **Algorithms Used:**
    *   **Degree Centrality:** Calculates the number of edges (connections) incident to a node. By running this on `IP` nodes, you can set a threshold (e.g., Degree > 20). Any IP exceeding this threshold is flagged as `is_commercial` or `is_fraud`, preventing it from forming a valid "Household" in the WCC step.

### 3. Behavioral Look-alike Segmentation
**Business Description & Value:**
Premion wants to build "look-alike segments" and niche audiences based on viewing habits (e.g., "Households that watch Discovery and use the Roku Channel"). Since `App` and `Channel` data can be sparse or distributed across devices, the graph needs to infer interests for the whole household based on the behavior of individual devices.
*   **Value:** Extends targetable attributes to all devices in a cluster. If one device in the household watches "Home & Garden" content, the entire household can be tagged as "Home Improvement Intenders," increasing the inventory value.
*   **Algorithms Used:**
    *   **Label Propagation (LPA):** This algorithm spreads labels from labeled nodes to unlabeled nodes based on the strength of their connections. If `Device A` is labeled "Sports Fan" (based on App usage), LPA propagates this label to other devices in the same WCC (Household), allowing Premion to target the "Sports Fan" segment across all screens in that home.

### 4. Cross-Device Influence & Attribution
**Business Description & Value:**
Premion aims to provide "cross-device attribution". This involves determining if an ad displayed on a Connected TV (Device A) led to a conversion or specific action on a mobile device (Device B) or a visit to a specific Site.
*   **Value:** Proves campaign ROI to advertisers by tracing the path of influence. It validates that a mobile click was influenced by a CTV impression within the same household context.
*   **Algorithms Used:**
    *   **Shortest Path:** Calculates the path between an Impression event (on a TV) and a Conversion event (on a Mobile/Laptop). If a path exists within the Household cluster (e.g., TV -> IP -> Mobile), attribution is credited.

### 5. Content Popularity & Inventory Scoring
**Business Description & Value:**
To assist with "forecasting" and "inventory definition", Premion needs to understand which Apps and Channels act as the primary gateways for their audience in specific geographies (e.g., "What is the most influential app in the New York DMA?").
*   **Value:** Identifies "Power Nodes"—the specific apps or publishers that bridge the most households. This helps in pricing inventory and predicting delivery for managed service clients.
*   **Algorithms Used:**
    *   **PageRank:** Assigns a score of importance to nodes based on the quantity and quality of links to them. Running PageRank on `App` or `Channel` nodes (weighted by `frequency_count` from the edges) identifies which content sources are the strongest drivers of household engagement, beyond simple impression counting.

### Summary Table for GAE Configuration

| Use Case Name | Target Nodes | Algorithm | Output / Result |
| :--- | :--- | :--- | :--- |
| **Household Stitching** | Device, IP | **WCC** | New property `phid` (Component ID) added to all Device/IP nodes. |
| **Commercial IP Filtering** | IP | **Degree Centrality** | New property `ip_type` ("Residential" vs "Commercial") based on connection count. |
| **Audience Propagation** | Device, Household | **Label Propagation** | Attribute `segment_interest` (e.g., "Auto Intender") spread to all devices in a `phid`. |
| **Attribution Path** | Device (TV), Device (Mobile) | **Shortest Path** | Boolean `is_attributed` confirmed if path exists < N hops. |
| **Inventory Influence** | App, Channel | **PageRank** | Score `authority_rank` added to Content nodes to forecast high-value inventory. |
