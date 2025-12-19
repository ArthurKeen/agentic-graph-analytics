# Graph Analytics Use Cases

Generated 10 use cases for graph analytics.


## UC-001: Household Identity Resolution

**Type:** centrality  
**Priority:** critical


### Description
Create a foundational 'stitched' view of households from disjointed device and IP data.


### Related Requirements

- REQ-001
- REQ-002
- REQ-007


### Data Requirements

- Domain: Digital Advertising / AdTech


### Expected Outputs

- Successful creation of PHIDs for grouped devices


## UC-002: Anomaly & Fraud Detection

**Type:** anomaly  
**Priority:** high


### Description
Automatically flag and filter out non-residential IPs to prevent wasted ad spend and diluted attribution.


### Related Requirements

- REQ-003


### Data Requirements

- Domain: Digital Advertising / AdTech


### Expected Outputs

- Reduction in commercial IP inclusion in household clusters
- Identification of IPs with Degree > 20


## UC-003: Behavioral Look-alike Segmentation

**Type:** community  
**Priority:** medium


### Description
Increase inventory value by extending targetable attributes to all devices in a household cluster.


### Related Requirements

- REQ-004


### Data Requirements

- Domain: Digital Advertising / AdTech


### Expected Outputs

- Successful propagation of 'segment_interest' attributes across PHIDs


## UC-004: Cross-Device Attribution

**Type:** pathfinding  
**Priority:** high


### Description
Prove campaign ROI by tracing the path of influence from TV impressions to mobile conversions.


### Related Requirements

- REQ-005


### Data Requirements

- Domain: Digital Advertising / AdTech


### Expected Outputs

- Confirmation of 'is_attributed' boolean via shortest path analysis


## UC-005: Inventory Influence Scoring

**Type:** centrality  
**Priority:** medium


### Description
Understand which apps and channels act as primary gateways for audiences to optimize pricing and delivery.


### Related Requirements

- REQ-006


### Data Requirements

- Domain: Digital Advertising / AdTech


### Expected Outputs

- Generation of 'authority_rank' for content nodes


## UC-S01: Household Clustering

**Type:** community  
**Priority:** medium


### Description
By analyzing devices that share common IP addresses and locations over time, the graph can group individual devices into household units for targeted advertising.


### Suggested Algorithms

- community_detection


### Data Requirements

- Vertex collections: Device, IP, AppProduct
- Edge collections: SEEN_ON_IP, SEEN_ON_APP, INSTANCE_OF


### Expected Outputs

- Household Clustering results


## UC-S02: Ad Fraud Detection

**Type:** anomaly  
**Priority:** medium


### Description
Identifying IP addresses with an unnaturally high frequency of unique devices or identifying devices seen across disparate geographical locations (zip3) in short timeframes to flag botnets or spoofing.


### Suggested Algorithms

- anomaly_detection


### Data Requirements

- Vertex collections: Device, IP, AppProduct
- Edge collections: SEEN_ON_IP, SEEN_ON_APP, INSTANCE_OF


### Expected Outputs

- Ad Fraud Detection results


## UC-S03: Inventory Value Analysis

**Type:** centrality  
**Priority:** medium


### Description
Ranking AppProducts and Sites based on their centrality and device reach to determine which platforms are the most influential 'hubs' in the advertising ecosystem.


### Suggested Algorithms

- pagerank


### Data Requirements

- Vertex collections: Device, IP, AppProduct
- Edge collections: SEEN_ON_IP, SEEN_ON_APP, INSTANCE_OF


### Expected Outputs

- Inventory Value Analysis results


## UC-S04: Cross-Channel Attribution

**Type:** pathfinding  
**Priority:** medium


### Description
Tracing paths from a Device through IPs to different SiteUse and InstalledApp instances to understand the multi-touch journey of a user across web and mobile platforms.


### Suggested Algorithms

- pathfinding


### Data Requirements

- Vertex collections: Device, IP, AppProduct
- Edge collections: SEEN_ON_IP, SEEN_ON_APP, INSTANCE_OF


### Expected Outputs

- Cross-Channel Attribution results


## UC-S05: Supply Chain Transparency

**Type:** pattern  
**Priority:** medium


### Description
Mapping the relationships between Publishers, AppProducts, and Exchanges to ensure ads are being served through authorized paths (similar to ads.txt validation).


### Suggested Algorithms

- pattern_detection


### Data Requirements

- Vertex collections: Device, IP, AppProduct
- Edge collections: SEEN_ON_IP, SEEN_ON_APP, INSTANCE_OF


### Expected Outputs

- Supply Chain Transparency results
