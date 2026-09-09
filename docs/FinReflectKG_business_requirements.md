# FinReflectKG Graph Analytics

## Domain Description

FinReflectKG is an open-source financial knowledge graph extracted from the annual
10-K filings that every S&P 500 constituent files with the U.S. Securities and
Exchange Commission, covering the eleven fiscal years 2014 through 2024. It is
published by Domyn on Hugging Face (`domyn/FinReflectKG`) and is, to date, one of
the largest openly available corpora of machine-extracted corporate disclosure.

**Business Domain: Corporate Disclosure & Systemic Risk Intelligence**

A 10-K is the most consequential document a public company produces. It is where
management is legally obliged to state what the business earns, what it depends on,
what could go wrong, which regulations bind it, which markets it operates in, and
who its competitors are. That information is authoritative and standardised in
*form*, but it is locked in narrative prose — roughly 500 filings a year, each
tens of thousands of words. No analyst reads the whole corpus, and conventional
tooling reduces it to either full-text search or a handful of tabular XBRL
financials, discarding the relationships that carry the analytical value.

FinReflectKG restores those relationships. Every extracted assertion becomes a
typed, dated, source-attributed edge between two entities — *this company discloses
this metric*, *this company depends on this raw material*, *this risk factor
negatively impacts this segment*, *this business is subject to this regulation*.
The result is a graph of what corporate America has formally said about itself over
a decade.

The analytical questions this unlocks are ones no single filing can answer, because
they are questions about the corpus as a whole:

* **Consensus and salience.** Which financial concepts, risks, and regulations
  dominate disclosure across the entire index — and which are idiosyncratic to a
  few firms? This is the empirical vocabulary of corporate finance, measured
  rather than assumed.
* **Shared exposure.** Which dependencies are *common* across otherwise unrelated
  companies? A raw material, a geography, a regulation, or a counterparty that many
  firms independently disclose a dependency on is a systemic transmission channel,
  visible only by aggregating across filings.
* **Emergent structure.** Do companies cluster by disclosure behaviour into the
  sectors that GICS assigns them, or into different, risk-driven groupings? A
  data-derived taxonomy that disagrees with the official one is itself a finding.
* **Drift over time.** The corpus spans 2014–2024, so the same measurement can be
  taken repeatedly and compared. Concepts that rose (supply-chain disruption,
  climate transition risk, generative AI) and fell can be ranked, not merely
  asserted.

**Strategic Objective: Aggregate Intelligence from Mandatory Disclosure**

The value proposition is that regulated disclosure is a free, high-integrity,
adversarially-audited data source that is nonetheless almost unused in aggregate.
Companies have strong legal incentives to be accurate and complete. The obstacle
was never data quality; it was that the corpus is prose. Analytics over
FinReflectKG aims to:

* **Rank by structural position, not market capitalisation.** Identify the firms,
  materials, geographies, and regulations that occupy load-bearing positions in the
  disclosed economy.
* **Surface concentration risk invisible to portfolio-level analysis.** Two holdings
  in different sectors may share an undisclosed-to-you common dependency that both
  independently disclosed.
* **Derive a risk taxonomy from evidence.** Let communities of co-disclosed
  concepts define the thematic map, instead of imposing one.
* **Measure the extraction itself.** Because the graph is LLM-extracted, graph
  structure doubles as a quality instrument: fragmentation, orphan islands, and
  reciprocal duplicate loops are all measurable defects.

**Technical Environment**

The graph is a **labeled property graph (LPG)** with a deliberately generic
physical schema — a single vertex collection and a single edge collection, with
semantics carried in a `type` property rather than in collection names:

| | |
| :--- | :--- |
| `Node` (vertices) | 3,099,773 documents. Semantic type in `Node.type`; display name in `Node.name`. Indexed on both. |
| `relations` (edges) | 17,513,372 documents, `Node` → `Node`. Relationship type in `relations.type`. |
| Named graph | `FinReflectKG` — one edge definition, `relations` from `[Node]` to `[Node]`. |
| `chunks` | 1,384,513 source-text passages, referenced by `relations.chunkKey`. Deliberately **excluded** from the named graph so analytics does not treat source text as vertices. |

Every edge is source-attributed and dated, which is what makes temporal and
provenance analysis possible: `ticker`, `year`, `sourceFile`, `pageId`, `chunkKey`,
`startDate` / `endDate` (`YYYY-MM`), and the denormalised endpoint types
`_fromType` / `_toType`. Vertex-centric indexes (`_from, type, _toType` and
`_to, type, _fromType`) support typed traversal in either direction, and
`ticker, year` supports filing-scoped slicing.

The deployment is a **OneShard** database (`sharding: "single"`), which co-locates
every collection on one DBServer so that multi-hop traversals and the whole-graph
algorithm loads incur no cross-node network cost.

### Two properties of this graph that drive the analytics configuration

These are not incidental details; the use cases below are shaped by them.

**1. The topology is a star radiating from `ORG`.** Filing companies are only
~0.73% of vertices, but they are the `_from` endpoint of essentially every
high-volume edge class — `ORG → FIN_METRIC` alone accounts for well over a third of
all edges, followed by `ORG → FIN_INST`, `ORG → ACCOUNTING_POLICY`,
`ORG → PRODUCT`, `ORG → REGULATORY_REQUIREMENT`, `ORG → RISK_FACTOR`. Each 10-K
contributes a burst of assertions emanating from one company.

The consequence is counter-intuitive and must be designed around: **`ORG` nodes
have enormous out-degree and almost no in-degree**, so a naive whole-graph PageRank
ranks companies *near the bottom* and concentrates score on the widely-disclosed
metrics they point at. Ranking companies therefore requires an explicit
company-to-company projection (§2), not a whole-graph run. Ranking *concepts*, by
contrast, works correctly on the whole graph (§1).

**2. The type vocabularies have a long tail.** `Node.type` has 9,605 distinct
values and `relations.type` has 30,535, because both were produced by LLM
extraction rather than drawn from a fixed ontology. The distribution is steeply
concentrated — the top ~25 node types cover roughly 95% of vertices — but the tail
is thousands of near-duplicate and single-use labels.

This matters operationally because the platform materialises **one projection
collection per logical type** (FR-74 typed LPG projections). Handed the raw
vocabulary, it would attempt to create thousands of collections. **Every use case
below must therefore be configured against an explicit type whitelist**, given in
the configuration section at the end. This is the single most important
configuration constraint in this document.

## FinReflectKG Graph Analytics Use Cases

The use cases below map the analytical questions above onto the algorithms actually
available in ArangoDB's Graph Analytics Engine as exposed by this platform —
**PageRank, WCC, SCC, Label Propagation, and Betweenness Centrality**. Each names
the algorithm class explicitly, because the failure mode in graph analytics is
answering a clustering question with a ranking algorithm, or vice versa.

### 1. Disclosure Salience Ranking

**Use Case Type:** CENTRALITY (Ranking / Influence Analysis)
**Primary Algorithm:** PageRank
**NOT:** Clustering, community detection, or component analysis

**Business Description & Value:**
Establish, empirically, which financial concepts dominate the disclosure of the
entire S&P 500 over a decade. Because the graph's edges point from companies to
the things they disclose, an entity's in-bound PageRank is a measure of how many
companies — weighted by how structurally significant those companies are —
independently chose to say something about it.

* **Value:** Produces a defensible, evidence-based ranking of what actually matters
  in corporate financial reporting, replacing assumption with measurement. The
  expected result is that universal metrics (revenue, net income, operating cash
  flow) and universally-binding regulations rank at the top, while the ranking's
  *middle* is the interesting part: concepts material to a substantial minority of
  the index. It also serves as the demo's correctness anchor — if net income and
  revenue do not surface near the top, the pipeline is misconfigured.
* **Algorithms Used:**
  * **PageRank:** Assigns each vertex a score from the quantity and quality of
    in-bound links. Run over the **whole graph** — this is the one ranking use case
    where the star topology is an asset rather than an obstacle, because
    concept-nodes are precisely the sinks that accumulate score.

### 2. Corporate Ecosystem Influence

**Use Case Type:** CENTRALITY (Ranking / Influence Analysis)
**Primary Algorithm:** PageRank over an `ORG → ORG` projection
**NOT:** A whole-graph run — see the warning below

**Business Description & Value:**
Rank companies by their structural position in the network of relationships that
companies disclose *about each other* — ownership stakes, competitive rivalry,
partnerships, investments, and dependencies. This is a measure of ecosystem
centrality, deliberately independent of market capitalisation, revenue, or index
weight: a mid-cap firm that many large firms name as a dependency is central here
and invisible in a cap-weighted view.

* **Value:** Identifies the companies whose distress would propagate furthest
  through disclosed commercial relationships — a counterparty-risk lens built from
  the filings themselves rather than from market co-movement.
* **CRITICAL CONFIGURATION NOTE:** This use case **must** run over a projection
  restricted to company-to-company edges (`has_stake_in`, `competes_with`,
  `partners_with`, `invests_in`, `depends_on`, `acquires`, `supplies_to`) with both
  endpoints of an organisation type. Running PageRank on the whole graph to rank
  companies produces a systematically wrong answer, because `ORG` nodes are
  near-pure sources: their in-degree is close to zero and their score collapses to
  the damping floor. The projection inverts a star into an actual network.
* **Algorithms Used:**
  * **PageRank:** Over the projected subgraph, where edge direction now carries
    genuine "A defers to / depends on B" semantics.

### 3. Thematic Community Detection

**Use Case Type:** COMMUNITY DETECTION (Clustering / Grouping)
**Primary Algorithm:** Label Propagation
**NOT:** Centrality or ranking — this groups concepts, it does not rank them

**Business Description & Value:**
Discover which financial concepts, risks, and macro conditions are habitually
disclosed *together*, and let those co-disclosure patterns define thematic
clusters. Companies exposed to the same underlying forces write similar filings;
the concepts they co-mention therefore form measurable communities.

* **Value:** Yields a risk-and-theme taxonomy derived from evidence rather than
  imposed by a classification standard. The commercially interesting output is
  **disagreement with GICS**: a community that spans several official sectors has
  identified a cross-sector exposure that sector-based portfolio construction
  cannot see. Conversely, communities that cleanly reproduce known sectors
  validate the extraction.
* **Algorithms Used:**
  * **Label Propagation (LPA):** Each vertex iteratively adopts the most frequent
    label among its neighbours, converging on densely-interconnected groups without
    requiring the number of communities to be specified in advance — essential
    here, since the natural number of disclosure themes is unknown. Run over a
    projection of concept-bearing types (`FIN_METRIC`, `RISK_FACTOR`,
    `MACRO_CONDITION`, `REGULATORY_REQUIREMENT`, `ESG_TOPIC`, `RAW_MATERIAL`,
    `SECTOR`) so that companies do not dominate the propagation.

### 4. Corpus Coherence & Extraction Coverage

**Use Case Type:** COMPONENT ANALYSIS (Connectivity / Data Quality)
**Primary Algorithm:** Weakly Connected Components (WCC)
**NOT:** A ranking exercise — the output is a coverage and quality verdict

**Business Description & Value:**
Determine whether the extracted graph is one coherent structure or a collection of
disconnected islands, and quantify the split. Because FinReflectKG is
LLM-extracted from independently-filed documents, connectivity is not guaranteed:
it is an *achievement* of the extraction, and therefore a measurement of its
quality.

* **Value:** This is the trustworthiness gate for every other use case in this
  document. A dominant component holding the overwhelming majority of vertices
  means companies genuinely share disclosed concepts and cross-company comparison
  is valid. Heavy fragmentation would mean the extraction produced per-filing silos
  with too little entity conflation, and cross-company findings would be artefacts.
  The small components are directly actionable: they localise filings whose
  extracted entities failed to merge with the corpus vocabulary, pointing at
  specific conflation defects.
* **Algorithms Used:**
  * **Weakly Connected Components (WCC):** Ignores edge direction to find every
    maximal set of mutually reachable vertices. Run over the whole graph — this is
    a question about the corpus in its entirety, so restricting it would defeat
    the purpose.

### 5. Systemic Contagion Chokepoints

**Use Case Type:** CENTRALITY (Bridge / Bottleneck Identification)
**Primary Algorithm:** Betweenness Centrality
**NOT:** PageRank — these measure different things, see below

**Business Description & Value:**
Find the entities that lie on the largest share of shortest paths between other
entities: the raw materials, geographies, regulations, financial institutions, and
macro conditions that act as bridges between otherwise unrelated parts of the
disclosed economy. These are the channels through which a localised shock becomes
a correlated one.

* **Value:** This is the systemic-risk use case, and it answers a question
  portfolio diversification analysis routinely gets wrong. Two holdings in
  different sectors with uncorrelated historical returns may both independently
  disclose dependence on the same strait, semiconductor, currency, or regulator.
  Betweenness surfaces exactly those shared chokepoints. A high-betweenness node is
  materially different from a high-PageRank node: PageRank finds what is *widely
  discussed*, betweenness finds what is *structurally load-bearing*. A commodity
  disclosed by only a few dozen firms can be a critical bridge while ranking
  nowhere on salience.
* **Algorithms Used:**
  * **Betweenness Centrality:** Counts shortest paths through each vertex. It is
    the most computationally expensive algorithm in the set, so it must run over a
    curated projection (`ORG`, `GPE`, `RAW_MATERIAL`, `REGULATORY_REQUIREMENT`,
    `MACRO_CONDITION`, `FIN_INST`, `LOGISTICS`) rather than all 3.1M vertices, and
    should be scheduled after the cheaper algorithms.

### 6. Reflexive Dependency Loops

**Use Case Type:** COMPONENT ANALYSIS (Directed Cycle Detection)
**Primary Algorithm:** Strongly Connected Components (SCC)
**NOT:** WCC — direction is the entire point here

**Business Description & Value:**
Find groups of entities that are mutually reachable *following edge direction*:
closed loops in which A's disclosed dependence on B coexists with B's dependence
on A, directly or through intermediaries. In a purely hierarchical dependency
structure, every strongly connected component is a single vertex; any component
larger than one is a feedback loop.

* **Value:** Dual-purpose, and both halves are worth reporting. Economically,
  genuine loops are self-reinforcing relationships — vertically entangled
  suppliers, mutual-dependency partnerships, reflexive market conditions — where
  shocks amplify rather than dissipate, and they are prime candidates for the
  betweenness analysis in §5. Diagnostically, loops are also the signature of
  extraction artefacts: if the same assertion was extracted once in each direction
  from a single passage, that reciprocal pair is a defect, and its `chunkKey`
  provenance identifies the exact source passage to inspect.
* **Algorithms Used:**
  * **Strongly Connected Components (SCC):** Respects edge direction. Run over a
    projection of directional dependency and impact edges (`depends_on`,
    `impacted_by`, `negatively_impacts`, `positively_impacts`, `supplies_to`,
    `subject_to`), where direction is semantically meaningful. Excluding
    `discloses` is essential — it is 42% of all edges and is structurally
    unidirectional, so including it adds cost and no cycles.

### 7. Disclosure Influence Drift, 2014 → 2024

**Use Case Type:** CENTRALITY (Comparative / Longitudinal Ranking)
**Primary Algorithm:** PageRank over year-sliced projections
**NOT:** A single run — the finding is the *difference* between runs

**Business Description & Value:**
Run the §1 salience ranking independently over each fiscal year's edges and compare
the results across the decade. Every edge carries a `year`, so the corpus supports
eleven independent annual measurements of the same quantity.

* **Value:** Turns a static ranking into a trend, which is where the narrative
  value sits. Concepts that climbed the ranking (supply-chain disruption, pandemic
  response, climate transition risk, generative AI) and those that faded can be
  ranked by *magnitude of movement*, with each movement traceable to the specific
  filings that caused it. It also demonstrates that a decade-scale corpus is being
  used as such, rather than being collapsed into one undifferentiated blob.
* **Algorithms Used:**
  * **PageRank**, executed once per year-slice, discriminating on the
    `relations.year` property. Ranks are then joined across slices and ordered by
    change. Note that the sibling `FinReflectKgTemporal` database already contains
    pre-computed PageRank results for 2014, 2019, 2020, and 2024
    (`gae_pr_<year>`) together with time-travel snapshots (`tt_snap_<year>`), so
    this use case can be demonstrated against pre-computed results or recomputed
    live.

### GAE Configuration

#### Mandatory type whitelist

`Node.type` has 9,605 distinct values and `relations.type` has 30,535, so typed
projections **must** be constrained to the lists below. Without this, projection
materialisation attempts thousands of collections.

**Node types in scope** (~95% of all vertices): `FIN_METRIC`, `FIN_INST`,
`ACCOUNTING_POLICY`, `PRODUCT`, `RISK_FACTOR`, `REGULATORY_REQUIREMENT`, `SEGMENT`,
`COMP`, `COMMENTARY`, `CONCEPT`, `EVENT`, `MACRO_CONDITION`, `LOGISTICS`,
`LITIGATION`, `PERSON`, `GPE`, `SECTOR`, `ECON_IND`, `ORG`, `RAW_MATERIAL`,
`ESG_TOPIC`, `FIN_MARKET`, `ORG_REG`, `PROPERTY`, `SERVICE`.

**Relation types in scope**: `discloses`, `negatively_impacts`, `depends_on`,
`subject_to`, `operates_in`, `impacted_by`, `has_stake_in`, `introduces`,
`positively_impacts`, `invests_in`, `complies_with`, `guides_on`, `partners_with`,
`competes_with`, `produce`, `announces`.

#### Summary table

| Use Case Name | Target Nodes | Scope / Projection | Algorithm | Output / Result |
| :--- | :--- | :--- | :--- | :--- |
| **Disclosure Salience** | all concept types | whole graph | **PageRank** | `disclosure_rank` on `Node`; ranked concept list. |
| **Ecosystem Influence** | `ORG`, `COMP` | `ORG→ORG` edges only | **PageRank** | `ecosystem_rank` on organisation nodes. |
| **Thematic Communities** | `FIN_METRIC`, `RISK_FACTOR`, `MACRO_CONDITION`, `REGULATORY_REQUIREMENT`, `ESG_TOPIC`, `RAW_MATERIAL`, `SECTOR` | concept projection | **Label Propagation** | `theme_community` label per concept; themes vs GICS. |
| **Corpus Coherence** | all | whole graph | **WCC** | `component`; dominant-component share + island inventory. |
| **Contagion Chokepoints** | `ORG`, `GPE`, `RAW_MATERIAL`, `REGULATORY_REQUIREMENT`, `MACRO_CONDITION`, `FIN_INST`, `LOGISTICS` | curated projection | **Betweenness** | `bridge_centrality`; ranked shared-exposure chokepoints. |
| **Reflexive Loops** | `ORG`, `FIN_METRIC`, `MACRO_CONDITION` | directional dependency edges | **SCC** | `feedback_component`; loops sized > 1, with provenance. |
| **Influence Drift** | all concept types | per-year edge slices | **PageRank** ×N | `rank_<year>`; concepts ordered by rank movement. |

#### Execution constraints

* **Read-only.** Write algorithm results to separate result collections; never
  mutate `Node` or `relations`.
* **Ordering.** Run WCC (§4) first — it validates the corpus and its dominant
  component bounds the others. Then the PageRank cases (§1, §2), then Label
  Propagation (§3) and SCC (§6). Betweenness (§5) is the most expensive and runs
  last.
* **Exclude `chunks`.** It holds 1.4M source-text passages and is not part of the
  named graph. It must never be loaded as a vertex collection; it is for
  provenance drill-down only, joined via `relations.chunkKey`.
