# Product Requirements Document: Agentic Graph Analytics UI

**Version:** 0.6  
**Date:** 2026-05-12  
**Status:** Draft  
**Target Release:** Product UI MVP  
**Related Document:** [Agentic Graph Analytics UI Vision](UI_PRODUCT_VISION.md)

**Changelog:**

- **0.6 (2026-05-12)** — Added FR-56..FR-72 (§ "Schema Kind Detection and
  Multi-Graph Support") and the corresponding data-model, agent, and UI
  requirements. Motivated by the HR-documents engagement where the source
  database is an ArangoDB GraphRAG output: a corpus graph
  (`*_Documents` + `*_Chunks`) and a knowledge graph (`*_Entities` +
  `*_Relationships` + `*_Communities`) live side by side in the same
  database, the entity and relationship collections are LPG (one
  collection holds many logical types, discriminated by a `type` /
  `relType` field), and a third structured-data graph (HRIS:
  `Employee`, `Department`, `Position`) may also be present. The current
  `SchemaExtractor` is collection-centric and would surface a single
  `Entities` entity and a single `Relationships` relationship, which
  breaks downstream use-case generation, template generation, and GAE
  projection. v0.6 introduces (a) algorithmic-then-LLM schema analysis
  via `arangodb-schema-analyzer` with a heuristic fallback (matching
  `arango-cypher-py` / `arango-sparql-py`); (b) a per-(workspace, named
  graph) `GraphProfile` model with `graph_purpose` classification; (c) a
  workspace-level `GraphSet` that records cross-graph linkage; (d) a
  conceptual-vs-physical `SchemaSnapshot` carrying `entityStyle ∈
  {COLLECTION, LABEL}` and `relationshipStyle ∈ {DEDICATED_COLLECTION,
  GENERIC_WITH_TYPE}` plus `typeField`/`typeValue`; (e) GAE projection
  view materialization so PageRank/WCC/etc. can run on a typed
  conceptual subgraph; (f) corpus/KG-aware Requirements Copilot,
  use-case generation, and reporting. See "Implementation Phases — Phase
  6: Multi-Graph and LPG-Aware Schema" for the rollout plan.
- **0.5 (2026-05-06)** — FR-31a Phase 1 acceptance closure. Closed the
  remaining gaps from v0.4: (AC#5) cancelled runs flip in-flight and
  pending steps to a new `WorkflowStepStatus.CANCELLED` so the DAG no
  longer shows a permanent `running` stripe; (AC#8) manual `PATCH
  /api/runs/{id}/steps/{id}` against an agentic run now raises
  `ConflictError → 409` with an internal-only `_internal=True` bypass
  for the `StepStatusReporter`; (general) the FastAPI app factory now
  maps `ValidationError → 400`, `NotFoundError → 404`, and
  `ConflictError`/`DuplicateError → 409` so callers no longer see
  opaque 500s for explicit domain errors. The supervisor was also
  fixed to pass `db_connection` (matching `AgenticWorkflowRunner`'s
  real ctor) and to surface `core_collections` /
  `satellite_collections` from the graph profile's role tags. Live
  status polling + an `AgenticRunStatusPanel` were added to the
  workspace canvas (3s poll while the run is `running`, 10s
  otherwise), and `start_workflow_run` / `execute_workflow` audit
  events now bracket every agentic run.
- **0.4 (2026-05-06)** — FR-31a Phase 1 design decisions locked and
  implementation begun. Confirmed: (1) agentic runs use a fixed
  six-step canonical layout instead of free-form labels; (2) execution
  uses an in-process `ThreadPoolExecutor` with a hard pre-commit to
  FR-31b before public availability; (3) LLM provider is env-only in
  Phase 1 with an `LLMProviderFactory.for_workspace` seam for future
  per-workspace `LLMProfile` records; (4) the new components are named
  `AgenticRunSupervisor` and `StepStatusReporter` to avoid colliding
  with the existing `OrchestratorAgent` / `AgenticWorkflowRunner`
  vocabulary.
- **0.3 (2026-05-05)** — Documented the deterministic-orchestration gap
  in the workflow runs section (workflow runs are persisted state, not
  executed agents) and added FR-31a "Planned: Live Agentic Execution"
  with full architecture, step-layout, API, cancellation, audit, and
  phasing plan for wiring `AgenticWorkflowRunner` into
  `start_workflow_run`.
- **0.2 (2026-05-05)** — Added Requirements iteration via versioning (UC-4B), the
  consolidated Requirements asset IA with canvas-side version dropdown,
  domain inheritance across reopen sessions, URL deep-linking for individual
  versions, and clarified copilot session UX (per-question save state,
  auto-refresh after approve).
- **0.1 (2026-04-30)** — Initial draft.

---

## Executive Summary

The Agentic Graph Analytics UI will turn `agentic-graph-analytics` from a Python library used through per-customer wrapper repositories into a product experience for configuring, executing, and sharing graph analytics workflows.

The MVP will provide a browser UI and backend API that let users create customer workspaces, connect to ArangoDB databases, inspect graph schemas, manage requirements documents, approve generated use cases and templates, run workflows, and view dynamic interactive reports. Product state should be stored in the customer's ArangoDB database using platform-owned metadata collections, while credentials and secrets remain outside the graph database.

The first release should focus on replacing the most common wrapper-repo functions:

- Customer configuration
- Requirements documents
- Graph profiles and collection roles
- Analysis templates
- Workflow run state
- Report browsing and publishing
- Catalog and lineage visibility

---

## Problem Statement

### Current State

Customer graph analytics work is currently delivered by creating separate projects that depend on `agentic-graph-analytics` or related orchestration libraries. Those projects contain:

- Business requirements and use-case documents
- `.env` files or environment conventions for customer cluster access
- YAML or Python configuration
- Customer-specific workflow scripts
- Analysis templates
- Output folders for Markdown, JSON, and HTML reports
- Workflow state files

This makes each customer engagement reproducible for engineers, but it has product limitations:

- Customer context is scattered across files and code.
- Analysts need engineering help to run or modify workflows.
- Reports are exported to local folders instead of rendered from durable product state.
- Requirements, templates, executions, and reports are not always linked by visible lineage.
- New customer onboarding requires repo creation and custom glue.
- Existing Analysis Catalog capabilities are not surfaced as a product UI.

### Desired State

Users should be able to use Agentic Graph Analytics as a product:

- Create a workspace for a customer graph.
- Connect to a customer ArangoDB database.
- Store customer-specific metadata in that database.
- Upload and version requirements documents.
- Generate, review, and approve use cases and templates.
- Execute workflows through a UI.
- View progress and recover from failures.
- Browse dynamic interactive reports.
- Trace every report back to requirements, templates, executions, and result collections.
- Export artifacts when needed without relying on wrapper repos.

---

## Goals and Non-Goals

### Goals

1. **Eliminate per-customer wrapper repos for standard usage.** Users should not need a new repository to onboard a customer graph.
2. **Provide a guided UI for the existing pipeline.** Requirements, schema analysis, use cases, templates, execution, catalog, and reports should be visible and actionable.
3. **Persist product state in ArangoDB.** Store non-secret workspace metadata, requirements, templates, runs, and reports in the customer database.
4. **Render reports dynamically.** Reports should be database-backed product views with export options, not only static HTML files.
5. **Make lineage auditable.** Every report should link back to source requirements, generated use cases, templates, executions, and result collections.
6. **Support migration from existing customer repos.** AdTech, clinical trials/CRO, and open source intelligence project patterns should be importable.
7. **Preserve power-user APIs.** Existing Python, CLI, and MCP surfaces should remain useful.

### Non-Goals

1. **No full SaaS tenant platform in MVP.** The first release does not need centralized tenant billing, usage metering, or global customer administration.
2. **No direct browser-to-database connection.** The frontend must use a backend API.
3. **No storage of secret values in ArangoDB metadata collections.** Store secret references only.
4. **No replacement of ArangoDB Graph Visualizer.** The UI may show graph inventory and lineage, but it is not a full graph visualization product in MVP.
5. **No generic BI dashboard builder.** Reports are structured around graph analytics workflows and catalog lineage.
6. **No arbitrary Python execution from imported templates.** Importers should parse supported formats safely.

---

## Personas

### Solutions Architect

Configures customer workspaces, imports existing customer artifacts, verifies graph access, and prepares demos or proofs of concept.

Needs:

- Fast workspace setup
- Connection testing
- Graph inventory
- Importers from existing repos
- Clear error messages
- Exportable deliverables

### Analytics Engineer

Reviews schemas, collection roles, templates, algorithms, result fields, and execution settings.

Needs:

- Template workbench
- Validation warnings
- Cost/time estimates
- Run history
- Result collection links
- Rerun and compare controls

### Business Analyst

Works with requirements, use cases, reports, insights, and recommendations.

Needs:

- Requirements upload and review
- Business-readable use cases
- Report browser
- Published report links
- Evidence and explanation
- Export to Markdown/PDF/HTML

### Platform Administrator

Controls deployment, authentication, authorization, secrets, and retention.

Needs:

- Workspace permissions
- Secret reference configuration
- Audit logs
- Metadata collection health
- Retention settings
- Backup/export options

---

## Primary Use Cases

### UC-1: Create Customer Workspace

**Actor:** Solutions Architect  
**Goal:** Create a reusable product workspace for a customer graph.

**Scenario:**

1. User opens the UI and selects "New Workspace."
2. User enters customer, project name, environment, and description.
3. User selects deployment mode.
4. System creates workspace metadata in the target database after connection setup.
5. Workspace appears on the home page.

**Success Criteria:**

- Workspace has a stable ID.
- Workspace stores customer/project/environment metadata.
- Workspace can be exported and re-imported.
- Workspace does not contain secret values.

### UC-2: Configure and Test Connection

**Actor:** Solutions Architect  
**Goal:** Connect the product to a customer ArangoDB database and GAE environment.

**Scenario:**

1. User enters endpoint, database, user, SSL setting, and deployment mode.
2. User selects or creates secret references for password/API keys/tokens.
3. System tests database connectivity.
4. System tests collection and named graph access.
5. System tests GAE capability if enabled.
6. System saves a connection profile.

**Success Criteria:**

- Connection profile is saved with non-secret descriptors.
- Secret values are never written to product collections.
- UI shows last successful verification time.
- Failures include actionable remediation.

### UC-3: Discover and Profile Graph

**Actor:** Analytics Engineer  
**Goal:** Understand the customer graph before generating analyses.

**Scenario:**

1. User opens the graph explorer.
2. System lists named graphs, vertex collections, edge collections, and counts.
3. User selects a graph.
4. System creates a graph profile and schema snapshot.
5. User assigns collection roles such as core, satellite, reference, result, or excluded.
6. System validates algorithm compatibility.

**Success Criteria:**

- Graph profile is versioned.
- Collection roles are editable and auditable.
- Schema snapshots can be compared.
- Warnings appear for risky roles, such as result collections included in WCC.

### UC-4: Upload and Version Requirements

**Actor:** Business Analyst  
**Goal:** Store business requirements in the product instead of a customer repo.

**Scenario:**

1. User uploads Markdown/PDF/DOCX/TXT requirements.
2. System stores document metadata, hash, extracted text, and storage URI or inline content.
3. System extracts structured objectives, requirements, constraints, and domain context.
4. User reviews and edits extracted requirements.
5. User approves a requirement version.

**Success Criteria:**

- Requirement versions are immutable after approval.
- Source document lineage is preserved.
- Duplicate uploads are detected by hash.
- Requirements can be linked to use cases and reports.

### UC-4A: Create Requirements with Requirements Copilot

**Actor:** Business Analyst  
**Goal:** Create a business requirements document through a guided, schema-aware interview.

**Scenario:**

1. User selects a graph profile and opens Requirements Copilot.
2. System summarizes observed schema context: named graph, collections, edge definitions, counts, sample fields, and collection roles.
3. System asks guided questions about vertical, domain, business objectives, decisions to support, target report audience, desired use cases, constraints, and success criteria.
4. User answers questions, edits assumptions, and confirms or rejects inferred context.
5. System generates an editable BRD draft and structured requirement version.
6. User reviews provenance labels and approves the requirement version.

**Success Criteria:**

- Copilot output distinguishes observed schema facts, inferred context, user-provided facts, and assumptions requiring confirmation.
- Generated BRDs are editable before approval.
- Approved copilot-generated requirements follow the same immutable versioning rules as uploaded requirements.
- Downstream use-case generation can only use an approved requirement version.

### UC-4B: Iterate Requirements with Versioning

**Actor:** Business Analyst  
**Goal:** Refine an approved requirements document into a new immutable
version without losing prior context, audit trail, or domain.

**Scenario:**

1. User opens the consolidated **Requirements** asset for the workspace.
2. UI displays the active version in a canvas with a version dropdown listing
   all prior versions (active + superseded + archived).
3. User selects "Reopen Copilot to Produce v(N+1)" from the canvas (or from
   the asset's right-click menu).
4. System opens a new Requirements Copilot session pre-populated with:
   - The prior version's domain.
   - The prior version's answers, mapped to the same questions where they
     still exist.
   - Provenance metadata recording the basis version (`based_on_version` /
     `based_on_version_id`).
5. User edits answers, regenerates the BRD draft, and approves the new
   version.
6. System auto-assigns the next sequential version number (`max(existing) + 1`),
   marks the basis version as superseded, and records a supersede edge in the
   audit trail.
7. The Assets panel's consolidated **Requirements** row updates to display the
   new active version and prior version count without a page reload.

**Success Criteria:**

- Version numbers are auto-assigned and monotonically increasing per workspace.
- Prior versions are preserved as immutable, read-only history; their status
  flips from `approved` to `superseded` exactly when the new version is
  approved.
- The Reopen flow inherits the domain from the prior version so the user is
  not asked to retype it.
- Pre-filled answers from the prior version are clearly marked as
  carried-over; editing them creates new state without altering history.
- The Assets panel surfaces ONE consolidated **Requirements** row per
  workspace regardless of version count; per-version inspection happens via
  the canvas dropdown.
- Each version is individually deep-linkable via URL (e.g.
  `?requirementVersion=<id>`) so audit links survive sharing across users.
- Historical versions remain viewable read-only; "Reopen Copilot" is only
  available when the active version is selected.

### UC-5: Generate and Approve Use Cases

**Actor:** Business Analyst  
**Goal:** Convert requirements and schema into graph analytics use cases.

**Scenario:**

1. User selects an approved requirement version and graph profile.
2. System generates candidate use cases.
3. UI shows business value, recommended algorithm, confidence, assumptions, and required graph shape.
4. User approves, edits, rejects, or prioritizes use cases.

**Success Criteria:**

- Approved use cases have stable IDs.
- Use cases link to source requirements.
- Rejected use cases retain rationale.
- Use cases can be manually created or imported.

### UC-6: Review and Approve Templates

**Actor:** Analytics Engineer  
**Goal:** Review executable GAE templates before running them.

**Scenario:**

1. System generates templates from approved use cases.
2. UI displays algorithm, parameters, graph config, result collection, result fields, engine settings, cost estimate, and runtime estimate.
3. System validates template compatibility.
4. User approves templates for execution.

**Success Criteria:**

- Invalid templates cannot be launched.
- Approved templates are versioned.
- Template changes preserve lineage.
- Imported clinical trials/CRO and open source intelligence templates map into this model.

### UC-7: Run Workflow

**Actor:** Analytics Engineer  
**Goal:** Execute graph analytics workflows without custom scripts.

**Scenario:**

1. User selects workflow mode: traditional, agentic, or parallel agentic.
2. User selects requirement version, graph profile, and approved templates.
3. User reviews estimated cost/time.
4. User launches run.
5. UI displays a visual workflow DAG with live step progress, GAE job status, agent decisions, warnings, and checkpoints.
6. User can cancel, retry failed steps, or resume from checkpoint.

**Success Criteria:**

- Run state is persisted incrementally.
- UI can recover after refresh.
- User can understand workflow progress and dependencies through a visual run DAG.
- Executions are recorded in the Analysis Catalog.
- Result collections are linked to execution records.
- Failures have retry/resume actions where supported.

### UC-8: View Dynamic Report

**Actor:** Business Analyst  
**Goal:** Review graph analytics outputs as an interactive product report.

**Scenario:**

1. User opens a completed run.
2. System displays generated reports from structured report records.
3. User reviews summary, insights, recommendations, charts, evidence, and lineage.
4. User filters or drills into result samples.
5. User exports report to HTML, Markdown, JSON, or PDF.
6. User publishes report snapshot.

**Success Criteria:**

- Report can be rendered without local output files.
- Charts render from stored chart specifications.
- Published reports are immutable.
- Report links to source requirements, use cases, templates, executions, and result collections.

### UC-9: Import Existing Customer Project

**Actor:** Solutions Architect  
**Goal:** Migrate existing repo-based customer work into the product.

**Scenario:**

1. User selects an import type: AdTech YAML/docs, clinical trials/CRO templates, open source intelligence templates, or generic folder.
2. System scans supported files.
3. UI previews mapped workspace, requirements, use cases, templates, reporting profile, and historical reports.
4. User approves import.
5. Product stores imported artifacts as versioned records.

**Success Criteria:**

- Import does not execute arbitrary Python.
- User can inspect mappings before save.
- Import preserves source file references and hashes.
- Unsupported files are reported clearly.

---

## Functional Requirements

### Workspace Management

- **FR-1:** Users can create, view, update, archive, and export workspaces. *(Implemented: `PATCH /api/workspaces/{id}` for editable metadata + `POST /api/workspaces/{id}/archive` for soft-delete; canvas right-click menu surfaces both. Edit emits an audit diff per changed field; archive is idempotent and emits a typed lifecycle event.)*
- **FR-2:** A workspace includes customer name, project name, environment, description, tags, and status.
- **FR-3:** A workspace can have multiple connection profiles.
- **FR-4:** A workspace can have multiple graph profiles.

### Connection Profiles

- **FR-5:** Users can create connection profiles for ArangoDB databases.
- **FR-6:** Connection profiles store non-secret descriptors and secret references.
- **FR-7:** The backend can test database, graph inventory, and GAE access.
- **FR-8:** The UI displays connection status, last verification time, and diagnostic errors.

### Graph Profiles

- **FR-9:** The system can discover named graphs, collections, edge definitions, counts, and sample schema.
- **FR-10:** Users can assign collection roles.
- **FR-11:** Graph profiles are versioned.
- **FR-12:** Graph profile snapshots can be linked to workflow runs.

### Requirements Documents

- **FR-13:** Users can upload Markdown, PDF, DOCX, and TXT documents.
- **FR-14:** The system stores document metadata, hash, extracted text, and source location.
- **FR-15:** The system extracts structured requirements using existing document extraction logic.
- **FR-16:** Users can approve requirement versions.
- **FR-17:** Approved requirement versions are immutable.
- **FR-17a:** Version numbers are auto-assigned per workspace as
  `max(existing.version) + 1`. The system rejects any explicit version that
  would collide with an existing version in the same workspace.
- **FR-17b:** When a new version is approved, all prior `approved` versions
  in the same workspace transition to `superseded`. The transition is atomic
  with the new version's approval and recorded in the audit log
  (`superseded_by` / `superseded_at` metadata on the prior version).
- **FR-17c:** All historical versions (any status) remain queryable and
  individually addressable. The Assets panel surfaces ONE consolidated
  "Requirements" entry per workspace; per-version inspection happens through
  the canvas-side selector and via deep-link
  (`?requirementVersion=<requirement_version_id>`).
- **FR-17d:** A new requirement version may be created from a prior approved
  version (the "Reopen Copilot to produce v(N+1)" flow). The new version's
  metadata records `based_on_version` and `based_on_version_id` for lineage.
- **FR-17e:** After a successful approval the workspace overview projection
  must refresh so the consolidated "Requirements" row reflects the new active
  version and history depth without a manual reload.

### Requirements Copilot

- **RC-1:** Users can launch a guided Requirements Copilot session from a graph profile or Requirements Studio.
- **RC-2:** The copilot uses graph schema context, including named graphs, collections, edge definitions, counts, sample fields, and collection roles.
- **RC-3:** The copilot asks domain and use-case discovery questions before drafting requirements.
- **RC-4:** The copilot captures constraints including runtime, cost, refresh cadence, data sensitivity, reporting audience, and required evidence.
- **RC-5:** The copilot generates an editable BRD draft with domain description, business objectives, analytics questions, success criteria, assumptions, constraints, and candidate GAE use cases.
- **RC-6:** Each generated statement is labeled as observed from schema, inferred from schema, user-provided, or assumption requiring confirmation.
- **RC-7:** Copilot-generated requirements must be reviewed and approved before use-case or template generation.
- **RC-8:** Users can reopen the Copilot from a prior approved RequirementVersion to produce the next version. The new session pre-fills:
  - The prior version's domain, so the user is not asked to retype it.
  - The prior version's answers, mapped to the same questions where they
    still apply, so iteration starts from the existing context.
- **RC-9:** Each Copilot session records its basis (`based_on_version_id`,
  `based_on_version`) on the resulting RequirementVersion's metadata. The
  domain is also persisted on the RequirementVersion's metadata so it
  propagates forward through future reopen sessions (`v1 → v2 → vN`) without
  user intervention.
- **RC-10:** The Copilot panel exposes per-question save state visibility so
  that users can tell which answers have been persisted versus typed but not
  yet saved. Specifically:
  - Each question shows a status indicator: untouched, unsaved (dirty),
    saving, or saved.
  - Saving one answer must not block editing of other answers.
  - The Approve action is disabled while any answer is unsaved.
- **RC-11:** After a Copilot draft is generated the UI must visibly surface
  the Draft BRD (e.g. by scrolling it into view). After approval the panel
  must clearly acknowledge success (showing the assigned version number) and
  lock all interactive controls so further typing cannot silently affect a
  sealed version.

### Use Cases

- **FR-18:** The system can generate use cases from requirement versions and graph profiles.
- **FR-19:** Users can manually create and edit draft use cases.
- **FR-20:** Users can approve, reject, prioritize, and archive use cases.
- **FR-21:** Use cases link back to requirements and forward to templates.

### Templates

- **FR-22:** The system can generate analysis templates from use cases.
- **FR-23:** Users can view and edit algorithm parameters before approval.
- **FR-24:** The system validates graph, algorithm, parameter, and result storage compatibility.
- **FR-25:** Approved templates are versioned and immutable for completed runs.
- **FR-26:** The system can import supported template dictionaries from existing projects without executing arbitrary code.

### Workflow Runs

- **FR-27:** Users can launch traditional, agentic, and parallel agentic workflows.
- **FR-28:** The backend persists run state, step status, checkpoints, warnings, errors, and timestamps.
- **FR-29:** Users can view run progress and GAE job IDs.
- **FR-30:** Users can cancel, retry, or resume runs where supported.
- **FR-31:** Completed executions are recorded in the Analysis Catalog.

#### Known limitation: workflow runs are currently deterministic state, not executed agents

**Status as of v0.2:** `WorkflowMode.AGENTIC` is descriptive metadata only.
The product workflow API (`POST /api/runs`, `POST /api/runs/{id}/start`,
`PATCH /api/runs/{id}/steps/{step_id}`) is a **persisted DAG plus state
machine**, not an executor:

- Step labels and the linear DAG are built client-side in
  `frontend/src/lib/product-api/client.ts:createWorkflowRunPayload` from
  whatever text the user types in the Create Workflow Run overlay.
- `ProductService.start_workflow_run` only flips run status to `RUNNING`
  and stamps `started_at`; it does **not** invoke
  `AgenticWorkflowRunner` or any agent.
- Step transitions to `succeeded`/`failed` are driven by the UI calling
  `PATCH .../steps/{id}`. There is no execution callback that produces
  these transitions today, so the visualizer reflects user actions
  rather than real agent progress.
- `RequirementsCopilot` questions are a hardcoded list and the draft is
  template-rendered (`graph_analytics_ai/product/service.py:_requirements_copilot_questions`,
  `_build_requirements_draft`). It is intentionally deterministic for
  MVP; LLM-backed question generation and draft synthesis are not wired.
- Real LLM-backed reasoning **does** exist in
  `graph_analytics_ai/ai/agents/runner.AgenticWorkflowRunner` and the
  specialized agents (`SchemaAnalysisAgent`, `RequirementsAgent` doc
  extraction path, `ReportingAgent` insights). It is reachable today
  only via MCP (`graph_analytics_ai/mcp/tools/workflow.start_workflow`)
  and CLI/example entry points — not from the product workflow API.

**FR-31a (planned, see "Planned: Live Agentic Execution" below):** Wire
`POST /api/runs/{id}/start` (when `workflow_mode == AGENTIC`) to
`AgenticWorkflowRunner.run_async`, derive step transitions from the
runner's `TraceEventType.STEP_START` / `STEP_END` events, and persist
them via the existing `update_workflow_step` path so the visualizer
reflects real agent progress without UI involvement. Until FR-31a
ships, the visualizer accurately reflects **persisted state**, not
**live execution**, and `WorkflowMode.AGENTIC` should be read as
"intended to run agentically" rather than "currently runs agents."

### Agentic Workflow Visualizer

- **FR-32:** The UI displays a run-level workflow DAG for every workflow run.
- **FR-33:** The DAG shows workflow stages as nodes, including schema analysis, requirements extraction, use-case generation, template generation, GAE execution, catalog persistence, and report generation.
- **FR-34:** The DAG supports parallel branches for parallel agentic workflows.
- **FR-35:** Each node displays status: pending, running, completed, failed, skipped, or paused.
- **FR-36:** Selecting a node opens step details, including agent name, inputs, outputs, warnings, errors, timing, retry count, checkpoint ID, and cost metadata when available.
- **FR-37:** Step details link to produced artifacts, including requirement versions, use cases, templates, executions, result collections, and reports.
- **FR-38:** Failed or paused nodes expose supported recovery actions such as retry, resume, cancel, or open logs.
- **FR-39:** The visualizer can be implemented with polling for MVP and must not require WebSocket/SSE delivery.

### Reports

- **FR-40:** The system stores report manifests, sections, insights, recommendations, evidence, and chart specs as structured records.
- **FR-41:** The UI renders reports dynamically from stored records.
- **FR-42:** Users can export reports to HTML, Markdown, JSON, and PDF. *(MVP scope: HTML and Markdown shipped; JSON and PDF deferred until use-case generation produces enough content to make them meaningfully different from the HTML/Markdown exports.)*
- **FR-43:** Users can publish immutable report snapshots.
- **FR-44:** Reports link to requirements, use cases, templates, executions, result collections, and graph profile versions.

### Catalog and Lineage

- **FR-45:** Users can browse epochs, executions, templates, use cases, and requirements.
- **FR-46:** Users can search executions by algorithm, status, epoch, date, graph, and workspace.
- **FR-47:** Users can view lineage from report to execution to template to use case to requirement.
- **FR-48:** Users can compare executions across epochs.

### Import and Export

- **FR-49:** The product supports import from AdTech-style YAML/docs projects.
- **FR-50:** The product supports import from clinical trials/CRO and open source intelligence analysis template files.
- **FR-51:** The product can export a workspace bundle with metadata, documents, templates, and report snapshots.
- **FR-52:** Exported bundles exclude secret values.

### Administration and Audit

- **FR-53:** The system records audit events for create, update, approve, launch, publish, import, export, and delete/archive actions.
- **FR-54:** Admins can configure retention for drafts, runs, documents, report snapshots, and audit logs.
- **FR-55:** Admins can validate product metadata collection health.

### Schema Kind Detection and Multi-Graph Support

This section adds the requirements introduced in v0.6 to cover ArangoDB
databases whose graphs are encoded as Labelled Property Graphs (LPG —
one document collection holds many logical entity types, discriminated
by a `type`-style field; one edge collection holds many relationship
types, discriminated by a `relType`/`relation`/`type` field) and
databases that contain multiple coexisting named graphs that serve
different purposes (e.g., a GraphRAG corpus graph alongside an extracted
knowledge graph alongside a structured HRIS graph).

These requirements are dependencies of existing FR-9..FR-12 (graph
profiles), FR-18..FR-21 (use cases), FR-22..FR-26 (templates), and
FR-27..FR-31a (workflow runs). Where this section conflicts with an
older requirement, this section wins.

#### Schema Analysis Library Adoption

- **FR-56 (Schema analyzer dependency):** The product depends on
  `arangodb-schema-analyzer` (the `schema_analyzer` package) as the
  primary schema analysis library, matching the convention established
  by `arango-cypher-py` and `arango-sparql-py`. The analyzer is a
  required runtime dependency for production deployments; a heuristic
  fallback (functionally equivalent to the
  `schema_acquire._build_heuristic_mapping` path in `arango-cypher-py`)
  is supported for dev environments and for graceful degradation when
  the analyzer is unreachable, but degraded bundles must carry an
  `ANALYZER_NOT_INSTALLED` warning surfaced in the UI.
- **FR-57 (Three-tier acquisition):** Schema acquisition follows a
  fixed strategy chain — `analyzer` (full algorithmic baseline +
  optional LLM repair) → `heuristic` (per-collection sampling and tier
  classification) → `cached`. The default strategy is `auto`
  (analyzer-then-heuristic). Operators can pin a strategy per workspace
  (`workspace.metadata.schema_strategy ∈ {auto, analyzer, heuristic}`)
  for cost or reproducibility.
- **FR-58 (Algorithmic-first / LLM-on-difficulty escalation):** The
  analyzer must always produce a deterministic baseline mapping
  (`schema_analyzer.baseline.infer_baseline_from_snapshot`) before any
  LLM call. The LLM repair pass runs only when at least one of the
  following triggers fires:
  - the baseline confidence is below the configured threshold
    (`schema_strategy.review_threshold`, default 0.7),
  - a collection has `>= 1` rejected tier-2 type candidate (per the
    `_detect_type_field` notes_sink in the heuristic detector),
  - a `GENERIC_WITH_TYPE` edge has unresolved `fromEntity`/`toEntity`
    (`UNRESOLVED_ENDPOINT == "Any"`),
  - a collection has competing tier-1 candidates (more than one of
    `type`, `_type`, `entityType` qualifies on the 80% rule),
  - the user explicitly opts in via `?force_llm=true` on the discovery
    API.

  When LLM repair fires, the resulting mapping is reconciled with the
  baseline (`schema_analyzer.reconcile.reconcile_physical_mapping`) so
  no collection is dropped silently; reconciliation deltas are surfaced
  in the UI.
- **FR-59 (Two-tier caching with shape/full fingerprints):** The
  product caches schema acquisition results keyed by
  `(workspace_id, connection_profile_id, database, graph_name)`. Two
  fingerprints drive cache decisions, mirroring `arango-cypher-py`:
  - `shape_fingerprint` — collections + types + index digests; when it
    matches, the cached conceptual + physical mapping is reused.
  - `full_fingerprint` — shape plus per-collection row counts; when it
    matches, cached cardinality statistics are reused; when only it
    differs, statistics are recomputed on top of the cached mapping
    (the "stats-only refresh" fast path).

  The persistent cache lives in a new `aga_schema_snapshots` collection
  (see Data Model below). The in-memory cache is process-local. Both
  caches are bypassed when `force_refresh=true` is passed to the
  discovery API.
- **FR-60 (Schema-change probe API):** A new
  `GET /api/graph-profiles/{graph_profile_id}/schema-change` endpoint
  reports `unchanged | stats_changed | shape_changed | no_cache` in
  under 200ms without doing a full reintrospection. The UI uses this on
  workspace open to decide whether to badge the Graph Explorer with
  "Schema may have changed."

#### Conceptual vs Physical Schema Model

- **FR-61 (Schema kind classification):** Every `GraphProfile` carries a
  `schema_kind` enum drawn from the analyzer's classification:
  - `pg` — every doc collection one entity, every edge collection one
    relationship (the legacy assumption).
  - `lpg` — every doc collection holds many entity types via a type
    discriminator field; every edge collection holds many relationship
    types via a discriminator.
  - `hybrid` — mix of `pg` and `lpg` collections in the same graph.
  - `rpt` — Resource Property Table (RDF triples shape: `subject_uri /
    predicate / object_uri / object_value`); reserved for SPARQL-style
    graphs.
  - `unknown` — analyzer ran but could not classify.

  `schema_kind` is what unblocks LPG-aware downstream behavior; every
  template/use-case generator MUST branch on it.
- **FR-62 (Conceptual schema persistence):** The `GraphProfile` carries
  a `conceptual_schema` block (the `schema_analyzer.ConceptualSchema`
  shape) listing logical `entities[]` (with `name`, `labels`,
  `properties`) and `relationships[]` (with `type`, `fromEntity`,
  `toEntity`, `properties`). For LPG graphs the entity list contains
  one entry per discriminator value (e.g., `Person`, `Org`, `Skill`,
  `Policy`), not one entry per collection.
- **FR-63 (Physical mapping persistence):** The `GraphProfile` also
  carries a `physical_mapping` block recording, for each conceptual
  entity:
  - `style ∈ {COLLECTION, LABEL}`
  - `collectionName: str`
  - `typeField: str | null` (only for `LABEL`)
  - `typeValue: str | null` (only for `LABEL`)
  - `properties: {name → {field, indexed, unique}}`
  - `indexes: [{type, fields, unique, sparse, name, vci?, deduplicate?, storedValues?}]`

  And, for each conceptual relationship:
  - `style ∈ {DEDICATED_COLLECTION, GENERIC_WITH_TYPE}`
  - `edgeCollectionName: str`
  - `typeField: str | null` / `typeValue: str | null` (only for
    `GENERIC_WITH_TYPE`)
  - `properties` and `indexes` as above
- **FR-64 (Provenance and confidence):** Every `GraphProfile`
  `metadata` block records `analyzer_source ∈ {analyzer_baseline,
  analyzer_llm, heuristic}`, `confidence ∈ [0, 1]`, `warnings[]`,
  `assumptions[]`, `detected_patterns[]` (closed tag set:
  `PG_ENTITY_COLLECTION`, `LPG_LABEL`, `RPT_TRIPLES`,
  `PG_DEDICATED_EDGE`, `LPG_GENERIC_EDGE`, `RPT_OBJECT_PROPERTY`),
  `analyzer_version`, `prompt_version` (when LLM ran),
  `shape_fingerprint`, `full_fingerprint`. `confidence < 0.7` flips the
  profile's `review_required` flag and the UI prompts the user to
  inspect.
- **FR-65 (Multitenancy and sharding profile surfacing):** When the
  upstream analyzer reports `metadata.multitenancy` and
  `metadata.shardingProfile`, the product surfaces them on the graph
  profile and uses them to (a) choose appropriate GAE projection
  parameters (e.g., respect `OneShard`), (b) warn before running
  cross-tenant analyses, and (c) expose the inferred `tenantKey` field
  to the Requirements Copilot so questions can be tenant-scoped
  automatically.

#### Multi-Graph Workspaces

- **FR-66 (Per-named-graph profiles):** A connection profile may have
  zero or more `GraphProfile` rows per database — one per named graph
  the user activates. The `(workspace_id, connection_profile_id,
  database, graph_name)` tuple is unique per `version`. Workspaces
  without any named graphs ("loose collections" mode) get a synthetic
  `__db__` profile representing the entire database.
- **FR-67 (Graph purpose classification):** Every `GraphProfile`
  carries a `graph_purpose` enum:
  - `corpus` — chunked-text container (heuristic: vertex collection
    names match `*Document(s)?` and `*Chunk(s)?`; edges include
    `PART_OF`).
  - `knowledge_graph` — extracted entity/relationship store (heuristic:
    `schema_kind == lpg` AND vertex collection names match
    `*Entit(y|ies)?` AND `MENTIONED_IN` and/or `in_community` edges
    present).
  - `structured` — collection-typed PG (heuristic: `schema_kind == pg`
    AND no GraphRAG-style collection names).
  - `analytics` — purpose-built result graph (heuristic: vertex
    collections begin with one of the configured GAE result prefixes,
    e.g., `pagerank_`, `wcc_`, `community_`).
  - `hybrid` — mixed signals.
  - `unknown` — auto-classifier could not decide.

  The classifier is deterministic, runs in the analyzer, and is
  user-overridable; an audit event records every override.
- **FR-68 (Workspace GraphSet):** A new workspace-level entity
  `GraphSet` records which `GraphProfile`s belong together and how they
  link. Required fields: `graph_set_id`, `workspace_id`,
  `graph_profile_ids[]`, `cross_graph_links[]` (each with `source_graph
  / target_graph / source_collection / target_collection /
  edge_collection? / link_kind ∈ {extracted_from, foreign_key,
  embedding_match, mention_chain, manual}` plus a confidence). The
  GraphSet is the unit a workflow run binds to (a run can span multiple
  graphs if the GraphSet records the cross-graph links the
  workflow needs).
- **FR-69 (Cross-graph link discovery):** During discovery the analyzer
  inspects every edge collection's `_from`/`_to` for cross-graph hops
  (i.e., `_from` lives in collection C1 that is in graph G1 only, and
  `_to` lives in collection C2 that is in graph G2 only) and records
  them as candidate `cross_graph_links` on the GraphSet for review. The
  user must confirm or reject each link before it can be used by the
  workflow runner.

#### LPG-Aware Agentic Workflow

- **FR-70 (Conceptual-typed AQL generation):** The
  `TemplateGenerator` and `AnalysisExecutor` MUST emit AQL/GAE
  templates that reference *conceptual* entity and relationship types,
  not collection names. The generators consult the `physical_mapping`
  to materialize the right scan or filter:
  - `style == COLLECTION` → `FOR x IN @@<collection>`
  - `style == LABEL` → `FOR x IN @@<collection> FILTER
    x[@typeField] == @typeValue`
  - `style == DEDICATED_COLLECTION` → `FOR e IN @@<edgeCollection>`
  - `style == GENERIC_WITH_TYPE` → `FOR e IN @@<edgeCollection>
    FILTER e[@typeField] == @typeValue`

  This is exactly the `aql_entity_match` /
  `aql_relationship_traversal` contract already implemented in
  `schema_analyzer.PhysicalMapping`; the product reuses it.
- **FR-71 (Typed GAE projection):** GAE algorithms (PageRank, WCC,
  SCC, Label Propagation, Betweenness, Community Detection, etc.)
  cannot directly operate on a `LABEL` entity or a `GENERIC_WITH_TYPE`
  relationship because GAE projects from collections. Before running
  any GAE algorithm against an LPG conceptual entity/relationship pair,
  the executor MUST materialize a *typed projection*:
  - Default strategy: server-side AQL view collection or named-graph
    materialization that selects only the matching `typeField ==
    typeValue` rows; the projection's lifetime is the run.
  - Alternative strategy (when permitted by deployment + dataset
    size): a lightweight GAE filter via per-projection vertex/edge
    collection clones; the cost surfaces in the run cost estimate.

  Typed projections are recorded as `analysis_executions[].metadata.
  projection` and cleaned up via the run finalizer or retained on
  request. The user can inspect, name, and reuse a projection across
  runs.
- **FR-72 (Schema-aware Requirements Copilot):** The Requirements
  Copilot MUST consume the conceptual schema and graph_purpose, not
  raw collection lists. Concretely, RC observations now include:
  - Per-named-graph kind/purpose summary (e.g. "This workspace has 2
    graphs: `acme_corpus` (purpose: corpus, 12k chunks across 350
    documents) and `acme_kg` (purpose: knowledge_graph, lpg, 8
    entity types: Person, Org, Skill, Policy, Position, Project,
    Location, Event)").
  - Per-entity-type counts (LPG: from the
    `metadata.statistics.entities` block) instead of just per-
    collection counts.
  - Per-relationship-type counts and from→to entity types.
  - Cross-graph link hints (e.g. "MENTIONED_IN connects entities to
    chunks; PART_OF connects chunks to documents — a use case can
    trace influence back to source documents").
  - Suggested algorithms scoped per-entity-type (e.g. "PageRank on
    Person via WORKS_FOR" rather than "PageRank on Entities via
    Relationships").

  Copilot questions and the BRD draft are templated against the
  conceptual schema; the prompt provenance labels each fact as
  `observed_from_schema`, `inferred_from_schema`,
  `analyzer_assumption`, `user_provided`, or `assumption_requires_
  confirmation`.

---

## Non-Functional Requirements

### Security

- **NFR-1:** Secret values must never be stored in product metadata collections.
- **NFR-2:** Backend APIs must enforce authentication and authorization.
- **NFR-3:** Sensitive fields must be redacted in logs and UI diagnostics.
- **NFR-4:** Published reports must respect workspace permissions.

### Reliability

- **NFR-5:** Workflow run state must survive browser refresh and backend restart.
- **NFR-6:** Long-running executions must not depend on a single HTTP request.
- **NFR-7:** Import operations must be idempotent when source hashes have not changed.

### Performance

- **NFR-8:** Workspace home should load in under 2 seconds for typical workspaces.
- **NFR-9:** Report views should render in under 3 seconds when using stored report records and samples.
- **NFR-10:** Large result collections should be sampled or paginated rather than fully loaded into the UI.

### Scalability

- **NFR-11:** Product collections should support multiple workspaces per database.
- **NFR-12:** Queries should use indexed workspace, run, timestamp, status, and lineage fields.
- **NFR-13:** The design should not preclude a future centralized control-plane database.

### Usability

- **NFR-14:** Users should be able to create a workspace and verify a connection without editing files.
- **NFR-15:** Generated recommendations must include explanations and assumptions.
- **NFR-16:** Validation errors should identify the exact graph, collection, algorithm, or parameter issue.

---

## Data Model

### Existing Catalog Collections

The UI should reuse the Analysis Catalog collections:

- `analysis_epochs`
- `analysis_requirements`
- `analysis_use_cases`
- `analysis_templates`
- `analysis_executions`
- `analysis_lineage_edges`
- `analysis_epoch_edges`

These collections already support core lineage from requirements through execution.

### New Product Collections

#### `aga_workspaces`

Stores customer project metadata.

Required fields:

- `_key`
- `workspace_id`
- `customer_name`
- `project_name`
- `environment`
- `description`
- `status`
- `tags`
- `created_at`
- `updated_at`
- `metadata`

#### `aga_connection_profiles`

Stores non-secret connection metadata.

Required fields:

- `_key`
- `connection_profile_id`
- `workspace_id`
- `name`
- `deployment_mode`
- `endpoint`
- `database`
- `username`
- `verify_ssl`
- `secret_refs`
- `last_verified_at`
- `last_verification_status`
- `metadata`

#### `aga_graph_profiles`

Stores graph inventory snapshots and role metadata.

Required fields:

- `_key`
- `graph_profile_id`
- `workspace_id`
- `connection_profile_id`
- `graph_name`
- `version`
- `schema_hash`
- `vertex_collections`
- `edge_collections`
- `edge_definitions`
- `collection_roles`
- `counts`
- `created_at`
- `created_by`

#### `aga_documents`

Stores source document metadata.

Required fields:

- `_key`
- `document_id`
- `workspace_id`
- `filename`
- `mime_type`
- `sha256`
- `storage_mode`
- `storage_uri`
- `extracted_text`
- `uploaded_at`
- `metadata`

#### `aga_requirement_interviews`

Stores Requirements Copilot sessions and generated BRD drafts.

Required fields:

- `_key`
- `requirement_interview_id`
- `workspace_id`
- `graph_profile_id`
- `status`
- `domain`
- `questions`
- `answers`
- `schema_observations`
- `inferences`
- `assumptions`
- `draft_brd`
- `provenance_labels`
- `created_at`
- `updated_at`
- `metadata`

#### `aga_requirement_versions`

Stores reviewed, versioned requirement sets.

Required fields:

- `_key`
- `requirement_version_id`
- `workspace_id`
- `document_ids`
- `analysis_requirements_id`
- `version`
- `status`
- `summary`
- `objectives`
- `requirements`
- `constraints`
- `approved_at`
- `metadata`

#### `aga_workflow_runs`

Stores UI-level workflow run state.

Required fields:

- `_key`
- `run_id`
- `workspace_id`
- `workflow_mode`
- `requirement_version_id`
- `graph_profile_id`
- `template_ids`
- `status`
- `steps`
- `checkpoints`
- `warnings`
- `errors`
- `started_at`
- `completed_at`
- `analysis_execution_ids`
- `metadata`

#### `aga_report_manifests`

Stores report-level metadata.

Required fields:

- `_key`
- `report_id`
- `workspace_id`
- `run_id`
- `status`
- `title`
- `summary`
- `version`
- `section_ids`
- `chart_ids`
- `published_snapshot_id`
- `created_at`
- `updated_at`
- `metadata`

#### `aga_report_sections`

Stores report content blocks.

Required fields:

- `_key`
- `section_id`
- `report_id`
- `order`
- `type`
- `title`
- `content`
- `evidence_refs`
- `metadata`

#### `aga_chart_specs`

Stores renderable chart specifications.

Required fields:

- `_key`
- `chart_id`
- `report_id`
- `title`
- `chart_type`
- `data_source`
- `data`
- `encoding`
- `metadata`

#### `aga_published_snapshots`

Stores immutable report publication records.

Required fields:

- `_key`
- `published_snapshot_id`
- `report_id`
- `workspace_id`
- `title`
- `published_at`
- `published_by`
- `content_hash`
- `rendered_snapshot`
- `export_uris`
- `metadata`

#### `aga_audit_events`

Stores product audit trail.

Required fields:

- `_key`
- `audit_event_id`
- `workspace_id`
- `actor`
- `action`
- `target_type`
- `target_id`
- `timestamp`
- `details`
- `metadata`

#### `aga_schema_snapshots` (new in v0.6)

Stores cached schema-acquisition results so subsequent reads do not
re-run the analyzer or LLM unless the underlying database changes. One
row per `(connection_profile_id, database, graph_name)`; the row is
upserted on every successful acquisition. Fingerprints are keyed lookups
for cache freshness.

Required fields:

- `_key` — `sha256("{connection_profile_id}|{database}|{graph_name}")`
- `schema_snapshot_id`
- `workspace_id`
- `connection_profile_id`
- `database`
- `graph_name` — may be `__db__` for "all collections in database"
- `schema_kind` — `pg | lpg | hybrid | rpt | unknown`
- `graph_purpose` — `corpus | knowledge_graph | structured | analytics | hybrid | unknown`
- `conceptual_schema` — `ConceptualSchema.to_json()` shape
- `physical_mapping` — `PhysicalMapping.to_json()` shape
- `analyzer_metadata` — `{source, confidence, warnings, assumptions, detected_patterns, analyzer_version, prompt_version, multitenancy?, sharding_profile?, statistics?}`
- `shape_fingerprint`
- `full_fingerprint`
- `acquired_at`
- `metadata`

#### `aga_graph_sets` (new in v0.6)

Workspace-level grouping of graph profiles that belong to the same
analytical context (e.g., "the corpus + KG + structured graphs for
ACME's HR engagement"). One workspace can have many graph sets; a
graph profile can belong to multiple graph sets. The graph set is the
unit a workflow run binds to so cross-graph analytics are first-class.

Required fields:

- `_key`
- `graph_set_id`
- `workspace_id`
- `name`
- `description`
- `graph_profile_ids` — ordered list
- `cross_graph_links` — list of `{source_graph_profile_id,
  target_graph_profile_id, source_collection, target_collection,
  edge_collection?, link_kind ∈ {extracted_from, foreign_key,
  embedding_match, mention_chain, manual}, confidence, status ∈
  {candidate, confirmed, rejected}, confirmed_at?, confirmed_by?}`
- `status` — `draft | active | archived`
- `created_at`
- `updated_at`
- `created_by`
- `metadata`

#### Updates to `aga_graph_profiles` (v0.6)

`aga_graph_profiles` gains the following non-breaking optional fields
(legacy profiles continue to validate; the discovery flow backfills on
next read):

- `schema_kind` — `pg | lpg | hybrid | rpt | unknown` (FR-61)
- `graph_purpose` — `corpus | knowledge_graph | structured | analytics | hybrid | unknown` (FR-67)
- `schema_snapshot_id` — pointer to the latest `aga_schema_snapshots` row that backs this profile
- `conceptual_schema` — copy of the conceptual schema at the version's
  freeze point (so older profile versions remain readable when the
  snapshot collection is rebuilt)
- `physical_mapping` — same rationale
- `analyzer_metadata.confidence`
- `analyzer_metadata.review_required` — derived from confidence < 0.7
  OR any unresolved endpoint OR any ANALYZER_NOT_INSTALLED warning
- `analyzer_metadata.warnings` / `assumptions` / `detected_patterns`
- `analyzer_metadata.shape_fingerprint` / `full_fingerprint`

Existing fields are unchanged. `vertex_collections`, `edge_collections`,
`edge_definitions`, `collection_roles`, and `counts` continue to work as
the *physical* collection inventory; the conceptual block is *additive*.

### Index Requirements

Product collections should index:

- `workspace_id`
- `status`
- `created_at` / `updated_at` / `timestamp`
- `run_id`
- `report_id`
- `graph_profile_id`
- `requirement_version_id`
- `sha256` for documents
- `workspace_id` plus status/date composites for dashboard queries

---

## API Requirements

The backend should expose versioned HTTP APIs. The exact framework is implementation-specific, but FastAPI is recommended.

### Workspace APIs

- `GET /api/workspaces`
- `POST /api/workspaces`
- `GET /api/workspaces/{workspace_id}`
- `PATCH /api/workspaces/{workspace_id}`
- `POST /api/workspaces/{workspace_id}/archive`
- `GET /api/workspaces/{workspace_id}/summary`

### Connection APIs

- `POST /api/workspaces/{workspace_id}/connections`
- `GET /api/workspaces/{workspace_id}/connections`
- `POST /api/connections/{connection_profile_id}/test`
- `POST /api/connections/{connection_profile_id}/test-gae`

### Graph APIs

- `GET /api/workspaces/{workspace_id}/graphs`
- `POST /api/workspaces/{workspace_id}/graph-profiles`
- `GET /api/graph-profiles/{graph_profile_id}`
- `PATCH /api/graph-profiles/{graph_profile_id}/collection-roles`
- `POST /api/graph-profiles/{graph_profile_id}/validate`

### Schema and GraphSet APIs (new in v0.6)

- `POST /api/connections/{connection_profile_id}/graph-inventory` — enumerate every named graph in the connection's database, return `{name, vertex_collections, edge_collections, edge_definitions, document_count?, edge_count?}` per graph plus a synthetic `__db__` entry covering loose collections. Server-side cached for 60s; pass `force_refresh=true` to bust.
- `POST /api/connections/{connection_profile_id}/discover-graph-profiles` — bulk-create one `GraphProfile` per named graph in a single call. Body accepts `{graph_names?: string[], strategy?: "auto" | "analyzer" | "heuristic", force_refresh?: bool}`. Returns the list of created profile IDs and per-graph confidence summaries.
- `GET /api/graph-profiles/{graph_profile_id}/conceptual-schema` — return the conceptual entity/relationship list with per-type counts and links to the underlying physical collections.
- `GET /api/graph-profiles/{graph_profile_id}/physical-mapping` — return the physical mapping (entity → `{style, collectionName, typeField?, typeValue?, ...}` and relationship → `{style, edgeCollectionName, typeField?, typeValue?, fromEntity, toEntity}`).
- `GET /api/graph-profiles/{graph_profile_id}/schema-change` — lightweight probe (FR-60): `{status: "unchanged" | "stats_changed" | "shape_changed" | "no_cache", current_shape_fingerprint, current_full_fingerprint, cached_shape_fingerprint?, cached_full_fingerprint?}`.
- `POST /api/graph-profiles/{graph_profile_id}/refresh-schema` — re-run acquisition (analyzer + LLM if triggered, then reconcile, then statistics). Body accepts `{strategy?: ..., force_refresh?: bool, force_llm?: bool}`. Returns the new snapshot ID + diff vs prior.
- `PATCH /api/graph-profiles/{graph_profile_id}/conceptual-schema` — accept a user override of an entity name, relationship name, or type assignment. The override is recorded in `metadata.user_overrides[]` and the analyzer respects it on next refresh (does not overwrite).
- `PATCH /api/graph-profiles/{graph_profile_id}/graph-purpose` — manually override the auto-classified `graph_purpose`. Records an audit event.
- `POST /api/workspaces/{workspace_id}/graph-sets` — create a `GraphSet` from a list of graph profile IDs.
- `GET /api/workspaces/{workspace_id}/graph-sets` / `GET /api/graph-sets/{graph_set_id}`.
- `PATCH /api/graph-sets/{graph_set_id}/cross-graph-links` — confirm/reject candidate cross-graph links.
- `POST /api/graph-sets/{graph_set_id}/discover-cross-graph-links` — re-run cross-graph link detection; useful after new collections are added.
- `POST /api/graph-profiles/{graph_profile_id}/projections` — materialize a typed projection for a specific conceptual entity-or-relationship subset (FR-71). Body: `{entities?: string[], relationships?: string[], strategy: "view" | "clone", ttl_seconds?: int, name?: string}`. Returns the projection ID for use in workflow runs.
- `GET /api/graph-profiles/{graph_profile_id}/projections` / `DELETE /api/projections/{projection_id}`.

### Document and Requirement APIs

- `POST /api/workspaces/{workspace_id}/documents`
- `GET /api/workspaces/{workspace_id}/documents`
- `POST /api/documents/{document_id}/extract`
- `POST /api/workspaces/{workspace_id}/requirements-copilot/sessions`
  - Accepts an optional `based_on_version_id` to reopen from a prior approved
    RequirementVersion (UC-4B). When present the new session inherits the
    prior version's domain and answers and records `based_on_version` /
    `based_on_version_id` on the resulting RequirementVersion's metadata.
- `GET /api/requirements-copilot/sessions/{session_id}`
- `POST /api/requirements-copilot/sessions/{session_id}/answer`
- `POST /api/requirements-copilot/sessions/{session_id}/generate-draft`
- `POST /api/workspaces/{workspace_id}/requirement-versions`
- `POST /api/requirement-versions/{requirement_version_id}/approve`
  - Accepts an optional `version` parameter; when omitted the backend
    auto-assigns `max(existing.version) + 1` for the workspace. Approval
    atomically supersedes any prior `approved` versions (FR-17a, FR-17b).

### Use Case and Template APIs

- `POST /api/requirement-versions/{requirement_version_id}/generate-use-cases`
- `GET /api/workspaces/{workspace_id}/use-cases`
- `PATCH /api/use-cases/{use_case_id}`
- `POST /api/use-cases/{use_case_id}/approve`
- `POST /api/use-cases/{use_case_id}/generate-template`
- `GET /api/workspaces/{workspace_id}/templates`
- `POST /api/templates/{template_id}/validate`
- `POST /api/templates/{template_id}/approve`

### Workflow APIs

- `POST /api/workspaces/{workspace_id}/runs`
- `GET /api/workspaces/{workspace_id}/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/workflow-dag`
- `GET /api/runs/{run_id}/steps`
- `GET /api/runs/{run_id}/steps/{step_id}`
- `POST /api/runs/{run_id}/cancel`
- `POST /api/runs/{run_id}/retry`
- `POST /api/runs/{run_id}/resume`

### Report APIs

- `GET /api/workspaces/{workspace_id}/reports`
- `GET /api/reports/{report_id}`
- `POST /api/runs/{run_id}/generate-reports`
- `POST /api/reports/{report_id}/publish`
- `GET /api/reports/{report_id}/export?format=html|markdown|json|pdf`

### Catalog APIs

- `GET /api/workspaces/{workspace_id}/catalog/executions`
- `GET /api/workspaces/{workspace_id}/catalog/epochs`
- `GET /api/catalog/executions/{execution_id}/lineage`
- `GET /api/catalog/stats`

### Import APIs

- `POST /api/workspaces/{workspace_id}/imports/preview`
- `POST /api/workspaces/{workspace_id}/imports/apply`
- `GET /api/imports/{import_id}`

---

## UI Requirements

### Navigation

The UI should include primary navigation for:

- Workspaces
- Graphs
- Requirements
- Use Cases
- Templates
- Runs
- Workflow Visualizer
- Reports
- Catalog
- Settings

### Workspace Dashboard

Must display:

- Connection health
- Active graph profile
- Recent runs
- Recent reports
- Open approvals
- Execution counts by status
- Latest errors or warnings

### Graph Explorer

Must display:

- Named graph list
- Collection inventory
- Edge definitions
- Collection roles
- Schema snapshot details
- Validation warnings
- **(v0.6)** Per-named-graph card showing `schema_kind` badge
  (`PG`, `LPG`, `Hybrid`, `RPT`, `Unknown`), `graph_purpose` badge
  (`Corpus`, `Knowledge Graph`, `Structured`, `Analytics`,
  `Hybrid`, `Unknown`), analyzer source (`Analyzer (LLM)`,
  `Analyzer (Baseline)`, `Heuristic`), confidence percentage, and
  a review-required indicator when confidence is below threshold.
- **(v0.6)** Conceptual schema view: tabular list of conceptual
  entities (with per-type counts and the underlying `style /
  collectionName / typeField? / typeValue?` from the physical
  mapping) and conceptual relationships (with from-entity →
  to-entity, per-type counts, and physical edge mapping).
- **(v0.6)** Schema-change indicator (badge driven by
  `GET /api/graph-profiles/{id}/schema-change`); clicking offers
  Refresh Schema with strategy/force-LLM controls.
- **(v0.6)** GraphSet workbench tab: drag-and-drop graph profiles
  into a set, review and confirm/reject candidate cross-graph
  links with evidence (sampled `_from`/`_to` documents).
- **(v0.6)** "Type Role" editor that replaces "Collection Role"
  editor when the graph profile is `lpg` or `hybrid` — assigns
  roles per conceptual entity instead of per collection.
- **(v0.6)** Sensitivity overlay on properties (badge per
  property: `none | low | medium | high | restricted`) with a
  toggle to reveal restricted values that emits an audit event.

### Requirements Studio

Must display:

- Source document list
- Requirements Copilot entry point
- Guided domain and use-case interview
- Schema observations used by the copilot
- Extracted requirements
- Editable BRD draft
- Provenance labels for generated statements
- Per-question save state (untouched / unsaved / saving / saved) so users
  can tell which answers have been persisted
- Approval status
- Links to generated use cases

#### Requirements Asset and Version Selector

The Assets panel must surface ONE consolidated **Requirements** entry per
workspace; it must not grow one row per RequirementVersion.

The consolidated row must display:

- The active version (most-recent `approved`).
- The count of prior versions, e.g. `v2 (approved) · 1 prior version`.

The Requirements canvas (opened by selecting the consolidated row) must
provide:

- A version selector dropdown listing every RequirementVersion in the
  workspace, sorted descending by version. The active version is marked.
- A default selection of the active version, so newly approved versions
  auto-advance the view without forcing the user to re-pick.
- A read-only history banner (e.g. `You are viewing v1 (read-only history)`)
  whenever a non-active version is selected, with a one-click "Return to
  active (vN)" affordance.
- A "Reopen Copilot to Produce v(N+1)" action that is only enabled when the
  active version is selected.
- Display of basis lineage when present (`Based on v(N-1)`) and supersede
  metadata for non-active versions.

The URL must reflect the currently-displayed version via a query parameter
(`?requirementVersion=<requirement_version_id>`) so audit links and shared
URLs open on the same version. The URL is rewritten in place (no history
entry per pick).

### Template Workbench

Must display:

- Template details
- Algorithm parameters
- Result collection and attributes
- Validation status
- Estimated cost/time
- Approval controls

### Run Detail

Must display:

- Visual workflow DAG
- Step timeline
- GAE job status
- Agent decisions
- Errors and warnings
- Checkpoints
- Result collection links
- Generated reports

### Workflow Visualizer

Must display:

- Run-level DAG nodes for workflow stages
- Directed dependencies between stages
- Parallel branches for parallel agentic mode
- Per-node status: pending, running, completed, failed, skipped, or paused
- Per-node details for agent decisions, inputs, outputs, warnings, errors, timing, retry count, checkpoint ID, and cost metadata
- Artifact links from steps to generated requirements, use cases, templates, executions, result collections, and reports
- Recovery actions for failed or paused steps where supported

### Report View

Must display:

- Summary
- Insights
- Recommendations
- Charts
- Evidence
- Lineage
- Export and publish controls

---

## MVP Scope

### Included in MVP

- Local/customer-hosted web app.
- Backend API around existing Python functionality.
- Workspace creation.
- Connection profile setup and test.
- Graph discovery and graph profile storage.
- Collection role editor.
- Document upload and extraction.
- Requirements Copilot guided interview and editable BRD draft generation.
- Requirement version approval.
- Use-case and template generation.
- Template validation and approval.
- Workflow launch and status tracking.
- Run-level agentic workflow visualizer.
- Dynamic report storage and rendering.
- Catalog execution browser.
- Basic lineage view.
- AdTech, clinical trials/CRO, and open source intelligence import preview/apply.

### Deferred

- SaaS tenant control plane.
- Enterprise SSO.
- Fine-grained report commenting.
- Full collaborative editing.
- Scheduling recurring workflows.
- Full graph visualization canvas.
- Billing and usage metering.
- Multi-region deployment management.

---

## Implementation Phases

### Phase 1: Metadata and Import Foundation

Deliverables:

- Product collection schema and storage layer.
- Workspace model.
- Graph profile model.
- Report manifest/section/chart models.
- Requirement interview and provenance model.
- Audit event model.
- CLI/API import preview for AdTech, clinical trials/CRO, and open source intelligence patterns.
- Workflow DAG and step-status model for run visualization.
- Tests for storage and import mapping.

Exit Criteria:

- Existing customer artifacts can be mapped into product records.
- Product records can be stored in a customer ArangoDB database.
- No secret values are persisted.

### Phase 2: Read-Only UI and Report Rendering

Deliverables:

- Workspace dashboard.
- Connection health view.
- Graph profile viewer.
- Catalog execution browser.
- Dynamic report viewer.
- Report export from stored records.

Exit Criteria:

- User can browse imported workspace data.
- User can render reports without local output folders.
- User can trace reports to catalog executions.

### Phase 3: Requirements, Use Cases, and Templates

Deliverables:

- Document upload.
- Requirements Copilot guided interview.
- Editable BRD draft generation with provenance labels.
- Requirements extraction and review.
- Requirement approval.
- Use-case generation and approval.
- Template workbench.
- Collection role editor.

Exit Criteria:

- User can move from uploaded or copilot-generated requirements to approved templates through the UI.
- Copilot-generated BRD drafts preserve schema observations, user answers, inferences, and assumptions.
- Generated templates are validated before execution.

### Phase 4: Workflow Execution

Deliverables:

- Run launch UI.
- Background worker or task queue.
- Run detail timeline.
- GAE job status integration.
- Retry/resume/cancel actions where supported.
- Dynamic report generation after runs.

Exit Criteria:

- User can execute an end-to-end workflow without a customer-specific script.
- Run state survives browser refresh.
- Executions are recorded in the Analysis Catalog.

### Phase 5: Publishing and Governance

Deliverables:

- Published report snapshots.
- Audit event browser.
- Workspace export bundles.
- Retention settings.
- Role-based access controls.

Exit Criteria:

- Business users can publish immutable report snapshots.
- Admins can review audit events and manage retention.

### Phase 6: Multi-Graph and LPG-Aware Schema (new in v0.6)

This phase implements FR-56..FR-72. Sequenced as four sub-phases so each
ships in roughly two-week increments and Phase 6a is independently
useful (it makes the existing PG path more reliable even before LPG
arrives).

#### Phase 6a — Schema analyzer integration (foundation)

Deliverables:

- New module `graph_analytics_ai/ai/schema/acquire.py` modeled after
  `arango-cypher-py/arango_cypher/schema_acquire.py`. Exposes
  `acquire_schema(db, *, strategy="auto", force_refresh=False)`
  returning a typed `SchemaAcquisitionBundle` dataclass.
- Optional dependency `arangodb-schema-analyzer>=0.6.1,<0.7` declared
  in `pyproject.toml` / `requirements.txt`. Wired through
  `graph_analytics_ai/ai/schema/__init__.py` so callers can opt in.
- New `GraphSchema.conceptual_schema`, `physical_mapping`, and
  `analyzer_metadata` fields on
  `graph_analytics_ai/ai/schema/models.py:GraphSchema`. Backward-
  compatible: legacy code paths see empty/optional values.
- New `aga_schema_snapshots` collection + repository methods
  (`product/repository.py`).
- Two-tier cache (in-memory dict + persistent collection) keyed by
  `(connection_profile_id, database, graph_name)`.
- `_shape_fingerprint` and `_full_fingerprint` wrappers (delegate to
  `schema_analyzer.fingerprint_physical_shape` /
  `fingerprint_physical_counts` when available, fallback fingerprint
  otherwise).
- `GET /api/graph-profiles/{id}/schema-change` endpoint (FR-60).

Exit Criteria:

- The existing PG demo databases (AdTech, ecommerce sample) produce
  byte-identical conceptual schemas before and after the cutover.
- The new module is exercised by unit tests for both
  `analyzer-installed` and `analyzer-missing` code paths.
- The schema-change probe responds in under 200ms on a 50-collection
  database.

#### Phase 6b — Schema kind, multi-graph, GraphSet

Deliverables:

- `schema_kind` and `graph_purpose` classifiers
  (`graph_analytics_ai/ai/schema/classify.py`). The `graph_purpose`
  classifier consumes the conceptual schema + collection-name patterns
  to pick `corpus | knowledge_graph | structured | analytics | hybrid |
  unknown`.
- `discover_graph_profile` updated to (a) list all named graphs in
  the database, (b) emit one `GraphProfile` per named graph (plus a
  synthetic `__db__` profile for loose collections), (c) populate
  `schema_kind`, `graph_purpose`, `conceptual_schema`,
  `physical_mapping`, and `analyzer_metadata` on each profile.
- New `GraphSet` model (`product/models.py`), repository, and APIs
  (`POST/GET /api/workspaces/{id}/graph-sets`, `PATCH
  /api/graph-sets/{id}/cross-graph-links`).
- Cross-graph link detector
  (`graph_analytics_ai/ai/schema/cross_graph.py`) — inspects edge
  collections for `_from`/`_to` that span multiple named graphs and
  emits candidate links with confidence.
- New Graph Explorer UI: per-named-graph cards with kind badges
  (`PG`, `LPG`, `Hybrid`, `RPT`, `Unknown`), purpose badges
  (`Corpus`, `Knowledge Graph`, `Structured`, `Analytics`),
  conceptual entity/relationship list, per-type counts, and a
  "Confidence: 0.92" / review-required indicator.
- New GraphSet workbench UI: drag-and-drop graph profiles into a
  set, review and confirm/reject candidate cross-graph links.

Exit Criteria:

- Discovering a database with both a corpus graph and a knowledge
  graph produces two profiles with the right `schema_kind` and
  `graph_purpose` plus a candidate `MENTIONED_IN`-bridged
  cross-graph link.
- Discovering an HRIS-style database produces a single `pg`/
  `structured` profile that round-trips through the new UI without
  visual regressions.
- GraphSet APIs round-trip via the API and are written into
  `aga_graph_sets`.

#### Phase 6c — LPG-aware template generation and typed projections

Deliverables:

- `TemplateGenerator` updated to consume the conceptual schema and
  emit `physical_mapping`-aware AQL fragments (FR-70), reusing
  `schema_analyzer.PhysicalMapping.aql_entity_match` /
  `aql_relationship_traversal` rather than hand-rolling the AQL.
- `AnalysisExecutor` updated to materialize typed GAE projections
  (FR-71) before running PageRank/WCC/SCC/etc. on `LABEL` /
  `GENERIC_WITH_TYPE` conceptual targets. Two strategies:
  - `view` — server-side AQL view + GAE smart-graph wrapper.
  - `clone` — temporary edge/vertex collections populated by an AQL
    `INSERT INTO`. Used when the deployment doesn't support `view`
    or when the projection is large enough to warrant a clone for
    repeat runs.

  Projection lifecycle is managed by a new `projections` repository
  with TTL-based cleanup; the executor records the projection ID on
  each `analysis_executions` row.
- `UseCaseGenerator` updated to scope suggested algorithms per
  conceptual entity/relationship type, with the
  `from_entity`/`to_entity` constraints carried through into the
  generated template.
- Cost estimator updated to account for projection materialization
  cost (rows scanned + indexes) and surface it in the "Approve
  Template" UI before launch.

Exit Criteria:

- Running PageRank against a `Person` entity (via a `WORKS_FOR`
  `GENERIC_WITH_TYPE` relationship) on a GraphRAG KG produces correct
  per-Person results, indexed and filtered server-side.
- The Analysis Catalog records the projection used per execution.
- A test fixture (`tests/fixtures/hr_graphrag_kg.py`) seeds a
  representative LPG KG and is exercised end-to-end through the
  workflow runner.

#### Phase 6d — Schema-aware Requirements Copilot and reporting

Deliverables:

- Requirements Copilot (`product/service.py:_schema_observations_*`,
  `_requirements_copilot_questions`) updated to surface conceptual
  per-type counts, `graph_purpose`, cross-graph links, and per-
  entity-type algorithm suggestions (FR-72).
- BRD draft template updated to label every statement with its
  provenance: `observed_from_schema`, `inferred_from_schema`,
  `analyzer_assumption`, `user_provided`, `assumption_requires_
  confirmation`.
- Report rendering pipeline updated to display result rows by
  conceptual type (e.g., "Top 10 Person nodes by PageRank" instead
  of "Top 10 Entities") and to include the projection ID + source
  documents (chunks) for every result row when the result trace
  through `MENTIONED_IN → Chunk → PART_OF → Document` is available.

Exit Criteria:

- The HR demo workflow ("Run influence analysis on a GraphRAG-built
  HR knowledge graph") produces a report whose result tables are
  typed, citations include source document IDs, and the BRD
  faithfully reflects the analyzer-detected purposes/kinds.
- Acceptance tests cover the full corpus + KG end-to-end pipeline.

---

## Success Metrics

- **Onboarding speed:** New customer workspace created and connected in under 15 minutes.
- **Repo reduction:** Standard customer engagements no longer require a new wrapper repository.
- **Report availability:** 95% of completed runs produce a dynamic report view without manual file handling.
- **Lineage completeness:** 100% of published reports link to requirement version, use case, template, execution, and result collection.
- **Run reliability:** 90% of failed recoverable steps expose retry or resume actions.
- **Import coverage:** AdTech, clinical trials/CRO, and open source intelligence patterns can be imported with user review.
- **User autonomy:** A non-engineering analyst can upload requirements, review use cases, and view reports without editing code.

---

## Dependencies

- Existing `graph_analytics_ai` workflow orchestration.
- Existing document extraction and requirement generation.
- Existing schema analysis.
- Existing use-case and template generation.
- Existing GAE execution support.
- Existing Analysis Catalog.
- Existing report generation and HTML/chart generation.
- ArangoDB storage backend.
- Backend web framework, recommended FastAPI.
- Frontend framework, recommended React or Next.js.
- Secret resolution mechanism for chosen deployment mode.

---

## Risks and Mitigations

### Risk: Product Metadata in Customer Database Is Not Always Allowed

Some customers may restrict new collections in production databases.

Mitigation:

- Support a separate metadata database in the same cluster.
- Support export/import bundles.
- Keep the storage backend abstract enough for a future control-plane database.

### Risk: Static HTML Report Code Is Hard to Convert to Dynamic Records

Existing report formatting may assume file output.

Mitigation:

- Introduce report manifests and chart specs as intermediate representation.
- Keep static exports as output adapters.
- Migrate report rendering incrementally.

### Risk: Long-Running Workflows Need Durable Execution

Workflow runs may exceed request timeouts or backend restarts.

Mitigation:

- Introduce persisted run state early.
- Start with in-process background workers for local mode.
- Add queue/task backend for production mode.

### Risk: Template Importers Could Execute Untrusted Code

Clinical trials/CRO and open source intelligence templates are often Python files.

Mitigation:

- Prefer AST parsing for literal dictionaries.
- Support JSON/YAML export/import as target migration format.
- Require manual review before applying imported templates.

### Risk: UI Becomes Too Broad

The product can expand into graph visualization, BI, collaboration, and admin.

Mitigation:

- Sequence delivery around replacing wrapper repo needs first.
- Treat graph visualization and SaaS control-plane features as later phases.

### Risk: LLM Cost Runaway During Schema Acquisition (v0.6)

LPG schema analysis with LLM repair on a 100+ collection database can
issue dozens of LLM calls per acquisition. With aggressive cache misses
this can dominate per-workspace cost.

Mitigation:

- The default strategy is `auto` with deterministic baseline first; LLM
  repair only fires on the explicit triggers in FR-58.
- Acquisition results are cached with shape + full fingerprints
  (FR-59); ordinary writes do not invalidate the cache.
- Per-workspace LLM token budget for schema analysis (configurable,
  default 50k tokens / 24h). The acquisition surface returns the
  baseline + a `degraded: true` flag if the budget is exhausted.
- The `force_llm=true` API flag is gated by an `analyst` role.

### Risk: Typed Projections Multiply GAE Storage and Cost (v0.6)

LPG `LABEL` and `GENERIC_WITH_TYPE` projections create per-type
filtered subgraphs; on a KG with 8 entity types and 12 relationship
types a naive "project everything" pass could produce ~96 collections.

Mitigation:

- Projections are created on demand per use case, not eagerly.
- Default strategy is `view` (no extra storage); `clone` is opt-in and
  surfaces an explicit storage estimate before approval.
- Projection registry (`aga_projections`) carries a TTL; a finalizer
  cleans up unused projections after `ttl_seconds` (default 24h, max
  30d).
- The cost estimator includes projection storage in the run cost
  before approval.

### Risk: Cross-Graph Link Confidence Misleads Workflow (v0.6)

Auto-detected cross-graph links (e.g., MENTIONED_IN as the bridge
between corpus and KG) may attach to the wrong entity collection if
the analyzer's heuristics are surprised by the data.

Mitigation:

- Candidate cross-graph links are surfaced in the GraphSet UI as
  *candidates*, never auto-confirmed. Workflow runs that depend on a
  cross-graph traversal MUST reject pending candidates with a clear
  error.
- Each link records confidence and the analyzer's evidence (`from`
  collection sample, `to` collection sample, edge sample).
- Analyst confirmation is captured in the audit log.

### Risk: PII / Sensitive Field Leakage from HR Schemas (v0.6)

HR knowledge graphs commonly contain salary, performance, SSN,
disability status, and other restricted fields. These can leak into
prompts, generated reports, or projections without explicit
classification.

Mitigation:

- The schema acquisition pipeline runs a sensitivity classifier
  (regex + name heuristics + analyzer-assisted) over property names
  and produces `sensitivity_tags` on each conceptual property:
  `none | low | medium | high | restricted`.
- The Requirements Copilot prompt redacts `restricted` and `high`
  values from sample documents before they enter the LLM context.
- Reports default to suppressing `high`/`restricted` columns in
  result tables; the user can opt in to display per workspace role.
- The `aga_audit_events` log captures every `restricted`-field
  reveal action.

---

## Feature Enhancements Identified During v0.6 Analysis

The following enhancements were identified while planning v0.6 and are
in scope for v0.6 unless explicitly tagged "deferred".

1. **Sensitivity classifier on properties** (in scope, see PII risk
   above). Without this the HR engagement is a non-starter.
2. **Embedding-aware analytics** (in scope, lightweight). Corpus
   chunks usually carry an embedding vector; the use-case generator
   should suggest semantic-search-augmented templates ("find chunks
   semantically similar to a seed chunk and run influence analysis
   on the entities they mention"). Implemented as a new template
   family `semantic_propagation`.
3. **Community-aware use cases** (in scope). KGs already carry
   pre-computed Leiden/Louvain communities. The use-case generator
   should propose templates that *use* the community assignment as
   input rather than recomputing it (e.g., "rank Persons within
   their assigned community by PageRank").
4. **Provenance trace in reports** (in scope). For LPG KG runs,
   every result row should be reverse-traceable through
   `MENTIONED_IN` → Chunk → `PART_OF` → Document. The Report Section
   `evidence_refs` array gains a `chunk_ids[]` and `document_ids[]`
   field for this.
5. **Entity resolution awareness** (in scope, deferred to v0.7).
   GraphRAG outputs frequently contain unresolved duplicates ("John
   Doe" mentioned in 3 documents → 3 nodes). Schema analysis should
   detect ER state (presence of an `ER_resolved_to` edge or a
   `canonical_id` property) and warn the user when running PageRank
   without ER first; integrate with the existing `arango-er`
   tooling for resolution suggestions.
6. **Time-travel / temporal graph awareness** (in scope, conditional
   on the temporal-graph skill being installed). HR data has
   temporal validity (employment intervals, position history). When
   the analyzer detects ProxyIn/ProxyOut/Entity collections with
   `created`/`expired` fields, the graph profile records
   `temporal: true` and templates default to point-in-time queries.
7. **Schema drift alerts** (in scope, lightweight). The schema-
   change probe API (FR-60) is the building block; phase 6b adds a
   dashboard widget that polls it on workspace open and badges the
   Graph Explorer when the cached profile is stale.
8. **Domain-knowledge import for Requirements Copilot** (deferred to
   v0.7). When the analyzer exports OWL Turtle (already supported
   upstream), the Requirements Copilot can use it as authoritative
   ontology context instead of inferring labels from collection
   names.
9. **Per-graph permissions** (deferred to v0.7). HR engagements
   typically need read-only audit access to the corpus graph,
   write access to the KG, and read-only to the structured graph.
   The `WorkspacePermission` model gains a per-`GraphProfile` ACL.
10. **Cross-graph workflow templates** (in scope at minimum, a
    "starter set" of three LPG/multi-graph templates ships with
    Phase 6c so the HR demo flows end-to-end without bespoke
    template authoring):
    - "Influence by Source" — PageRank on a Person/Org subgraph,
      enriched with a count of corpus chunks that mention each top
      result, with chunk → document provenance in the report.
    - "Topic Communities" — surface KG communities, summarize each
      with the documents whose chunks contributed most to it, and
      rank by intra-community density.
    - "Similar Entities by Skill / Policy" — Jaccard / overlap
      score on `(Person, Skill)` and `(Person, Policy)` projections
      via WORKS_ON / GOVERNED_BY relationships.
11. **Schema migration compatibility** (in scope, small). When the
    persisted GraphProfile predates v0.6, `repository.get_graph_profile`
    transparently backfills `schema_kind = "pg"` and
    `graph_purpose = "structured"` so the UI does not break for
    in-flight workspaces.
12. **Per-entity-type collection-role overrides** (in scope). The
    existing `collection_roles` map is per-collection. For LPG it
    expands to per-conceptual-entity (`role_overrides[entity_name]
    = {core, satellite, reference, result, excluded}`). The UI
    Collection Role editor splits into a Type Role editor for LPG
    profiles.
13. **Analyzer MCP tool exposure** (deferred to v0.7). The upstream
    `schema_analyzer.mcp_server` provides `analyze_database`,
    `get_conceptual_schema`, `get_physical_mapping`, and
    `validate_pattern`. Re-export these as product MCP tools so
    external agents can introspect a workspace's schema without
    Python access.
14. **Hybrid corpus-only fast path** (in scope, small). When the
    only graph in scope is a corpus (no KG yet), the use-case
    generator defaults to a two-step pipeline: (a) recommend running
    the GraphRAG importer to extract a KG, (b) only then run
    analytics. This keeps the workflow runner from suggesting
    PageRank on a `Documents`/`Chunks` graph (which is rarely
    meaningful).
15. **Unknown-purpose review queue** (in scope, lightweight). When
    `graph_purpose == unknown` the profile lands in a workspace-
    level "Needs Review" tray; the Solutions Architect picks a
    purpose from a typeahead and the choice trains a per-workspace
    overrides map that biases future auto-classification.

---

## Planned: Live Agentic Execution (FR-31a)

**Status:** Phase 1 in progress as of v0.4. Decisions locked below.

**Goal.** Make `POST /api/runs/{run_id}/start` actually execute the
agentic pipeline when `workflow_mode == AGENTIC`, and stream per-step
progress back into the existing `WorkflowStep` rows so the canvas
visualizer reflects real agent state. This closes the gap documented
under "Known limitation: workflow runs are currently deterministic
state, not executed agents."

### Locked Design Decisions (v0.4)

The four open architectural questions surfaced when writing v0.3 are
now closed. Each decision lists the chosen option and the rationale so
future readers can see why we didn't pick the alternatives.

1. **Step labels in agentic mode → six canonical steps.** When
   `workflow_mode == AGENTIC`, the service ignores any client-supplied
   step labels and seeds the run with the canonical six in fixed
   order (`schema_analysis`, `requirements_extraction`,
   `use_case_generation`, `template_generation`, `execution`,
   `reporting`). The frontend overlay replaces the free-form textarea
   with a read-only labeled preview. **Why:** the orchestrator's
   `STANDARD_WORKFLOW` only knows these six phases. Letting users
   type "Find Anomalies" and pretending an agent ran that step would
   make the visualizer lie about reality. **Traditional mode is
   unchanged** — free-form labels remain there. Per-`execution`-phase
   template selection ("which analyses run inside Execution") is a
   separate future enhancement (FR-31c-or-later).

2. **Execution surface → in-process `ThreadPoolExecutor` for Phase 1,
   hard pre-commit to FR-31b before public availability.** The
   `AgenticRunSupervisor` wraps a process-local pool sized to
   `max_workers=2` initially; orphan-sweep on startup flips runs left
   in `RUNNING` after restart to `FAILED` with a `stale_run_detected`
   reason. `WorkflowRun.metadata.executor_kind` records which executor
   produced the row (`"inprocess"` in Phase 1) so we can tell from the
   data which path produced it after we migrate. `max_executions` is
   capped at 5 in Phase 1 (default 3) to bound LLM cost blast radius.
   **Why:** ships in days, matches the existing MCP background pattern,
   keeps deployment surface unchanged. The cost is real (lost runs on
   API restart), so this Phase 1 must not be put in front of paying
   customers without first shipping FR-31b (durable executor backed by
   Arq or Celery). The supervisor is written so the swap is mostly
   replacing `executor.submit(...)` with `task.delay(...)`.

3. **LLM provider config → env-only in Phase 1, with a
   `LLMProviderFactory.for_workspace(workspace_id)` seam for
   per-workspace configuration later.** Phase 1's factory ignores the
   `workspace_id` argument and returns the env-default
   `create_llm_provider()`. **Why:** lets us ship without inventing a
   new `LLMProfile` collection, new CRUD APIs, and new UI; preserves
   the seam that future per-workspace config will plug into without
   touching `AgenticRunSupervisor`. The seam is real code (it's how
   the supervisor obtains the provider) so future work is purely
   inside the factory and a new collection — no churn at the
   integration point.

4. **Naming → `AgenticRunSupervisor` and `StepStatusReporter`.** Not
   `WorkflowExecutor` (collides with `concurrent.futures.Executor`
   ABC connotations) and not `WorkflowRunner` (collides with the
   existing `AgenticWorkflowRunner`). Not `StepStatusBridge` because
   "bridge" is a heavy GoF term for what is functionally a listener.
   **Why:** `AgenticRunSupervisor` names what it owns (the lifecycle
   of an agentic run — spawn, cancel, orphan recovery) and pairs
   naturally with `OrchestratorAgent` (one supervises runs, the other
   orchestrates phases within a run). `StepStatusReporter` says what
   it does in one verb and aligns with the `actor="workflow-runner"`
   audit pattern.

### Scope

In scope for the first slice (call this **FR-31a Phase 1**):

- A new `AgenticRunSupervisor` service that bridges the product run
  record to `AgenticWorkflowRunner`.
- A background execution surface so HTTP requests do not block on
  multi-minute LLM calls.
- A trace-event → `WorkflowStepStatus` adapter that updates persisted
  steps as the runner emits `STEP_START` / `STEP_END` /
  `AGENT_ERROR` events.
- A canonical mapping between the runner's six fixed phases
  (`schema_analysis`, `requirements_extraction`, `use_case_generation`,
  `template_generation`, `execution`, `reporting`) and `WorkflowStep`
  rows on the run.
- Cooperative cancellation via a per-run cancel flag the runner can
  observe.
- Failure surface that records the failing step, error message, and
  any partial outputs.

Explicitly **out of scope** for Phase 1:

- Replacing the in-process executor with a durable task queue (Celery,
  Arq, RQ). Phase 1 uses an in-process `ThreadPoolExecutor` matching
  the existing MCP pattern; durable execution is FR-31b.
- LLM-driven planning or step reordering. The orchestrator's
  `STANDARD_WORKFLOW` list remains the source of truth for step
  order; agentic-ness in Phase 1 means "agents execute the steps,"
  not "an agent decides which steps to run."
- Live token streaming of intermediate LLM output to the UI.

### Architecture

```
┌─────────────────────────┐        POST /api/runs/{id}/start
│   Frontend (React)      │  ─────────────────────────────────┐
└─────────────────────────┘                                   │
                                                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ FastAPI route (existing dispatcher)                                │
│   → ProductService.start_workflow_run(run_id)                      │
│       (Phase 1 change) if workflow_mode == AGENTIC:                │
│           AgenticRunSupervisor.submit(run_id)                      │
│       set status = RUNNING, return immediately                     │
└────────────────────────────────────────────────────────────────────┘
                                                              │
                                       submit()               │
                                                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ AgenticRunSupervisor (in-process ThreadPoolExecutor, max_workers=2)│
│  • One worker per run; bounded pool                                │
│  • Per-run CancelToken (threading.Event)                           │
│  • Resolves connection_profile + secrets via SecretResolver        │
│  • Builds AgenticWorkflowRunner(db, llm, graph_name=...) via       │
│    LLMProviderFactory.for_workspace(workspace_id)                  │
│  • Attaches a StepStatusReporter as a TraceCollector listener      │
│  • Calls runner.run_async(...) inside a per-thread event loop      │
└────────────────────────────────────────────────────────────────────┘
                                                              │
                              STEP_START / STEP_END events    │
                                                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ StepStatusReporter                                                 │
│  • Maps trace step_name → WorkflowStep.step_id via                 │
│    AGENTIC_STEP_LAYOUT (six canonical steps)                       │
│  • Calls ProductService.update_workflow_step(...) for each event   │
│  • Records error details + duration in step.metadata               │
│  • On WORKFLOW_END or exception, writes final status, emits        │
│    audit_event(action="execute_workflow", actor="workflow-runner") │
└────────────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
                  Existing UI poll of GET /api/runs/{id}
                  (no UI changes required for Phase 1)
```

The executor is process-local. Restarting the API drops in-flight
runs; the run row is left in `RUNNING` and Phase 1 surfaces a
`STALE_RUN_DETECTED` banner via a startup recovery sweep (see Risks).

### Step Layout (Canonical Six)

The runner's `STANDARD_WORKFLOW` is fixed:

```
schema_analysis → requirements_extraction → use_case_generation
  → template_generation → execution → reporting
```

For agentic runs, the UI's free-form step labels are replaced by a
canonical layout. `ProductService.create_workflow_run` will, when
`workflow_mode == AGENTIC`, ignore the client-supplied `steps`/
`dag_edges` and instead seed the run with these six steps in order
(label, step_id, status=`PENDING`). The frontend's Create Workflow
Run overlay loses the "type your own steps" field for agentic mode
and shows a read-only preview of the canonical layout instead. The
`TRADITIONAL` mode keeps the existing free-form behavior unchanged.

This mapping table lives in `graph_analytics_ai/product/workflow_layout.py`:

| WorkflowStep.step_id     | label                  | maps to runner phase           |
|--------------------------|------------------------|--------------------------------|
| `schema_analysis`        | "Schema Analysis"      | `WorkflowSteps.SCHEMA_ANALYSIS`|
| `requirements_extraction`| "Requirements Review"  | `REQUIREMENTS_EXTRACTION`      |
| `use_case_generation`    | "Use Case Generation"  | `USE_CASE_GENERATION`          |
| `template_generation`    | "Template Generation"  | `TEMPLATE_GENERATION`          |
| `execution`              | "Analysis Execution"   | `EXECUTION`                    |
| `reporting`              | "Report Generation"    | `REPORTING`                    |

### API Changes

- `POST /api/runs` (existing): when `workflow_mode == "agentic"`,
  the service ignores client `steps` / `dag_edges` and seeds the
  canonical layout. Returns the seeded run.
- `POST /api/runs/{run_id}/start` (existing path, behavior change):
  validates the run is `QUEUED`, fetches the workspace's active
  graph profile + connection profile, resolves secrets via the
  existing `SecretResolver` chain, submits to the executor, returns
  `{run_id, status: "running"}` immediately. Always returns within
  ~200 ms regardless of LLM latency.
- `POST /api/runs/{run_id}/cancel` (new): sets the run's
  `CancelToken`. The runner observes it between steps; cancellation
  is cooperative (no in-step interrupt).
- `GET /api/runs/{run_id}/status` (new, lightweight): returns
  `{run_status, current_step_id, step_statuses, error_message}` so
  the UI poll is cheap. Existing `GET /api/workspaces/{id}/overview`
  continues to work; the new endpoint is an optimization.

### Configuration Resolution

The runner needs a real `db_connection` and `llm_provider`. Phase 1
resolves them from product metadata:

1. **Database connection.** Look up the workspace's active
   `GraphProfile` → its `ConnectionProfile`. Use existing
   `verify_connection_profile` machinery to build a connection
   (resolving the password via `SecretResolver`). If verification
   fails, the run transitions to `FAILED` with the verification
   error before any agent runs.
2. **LLM provider.** Read provider/model selection from
   `WorkspaceMetadata.llm` (new optional field) or fall back to
   `create_llm_provider()`'s env-driven default. API keys are
   resolved through the same `SecretResolver` so they never enter
   product metadata documents.
3. **Graph name + collection roles.** Pull `graph_name`,
   `core_collections`, `satellite_collections` from the workspace's
   active `GraphProfile`.

### Status Streaming Mechanism

`AgenticWorkflowRunner` already accepts a `TraceCollector` and emits
`TraceEventType.STEP_START` / `STEP_END` / `AGENT_ERROR`. The bridge
subscribes by replacing `trace_collector.record_event` with a
wrapper (or by adding a proper `add_listener(callback)` API to
`TraceCollector` — preferred; small refactor).

```python
class StepStatusReporter:
    def __init__(self, run_id: str, service: ProductService):
        self.run_id = run_id
        self.service = service
        self.step_started_at: dict[str, datetime] = {}

    def on_event(self, event: TraceEvent) -> None:
        step_id = AGENTIC_STEP_LAYOUT.runner_phase_to_step_id(
            event.data.get("step")
        )
        if step_id is None:
            return  # not a workflow-step event we care about

        if event.event_type is TraceEventType.STEP_START:
            self.step_started_at[step_id] = utcnow()
            self.service.update_workflow_step(
                self.run_id, step_id, status=WorkflowStepStatus.RUNNING,
                actor="workflow-runner",
            )
        elif event.event_type is TraceEventType.STEP_END:
            duration_ms = ms_since(self.step_started_at.pop(step_id, None))
            self.service.update_workflow_step(
                self.run_id, step_id,
                status=WorkflowStepStatus.SUCCEEDED,
                metadata_patch={"duration_ms": duration_ms},
                actor="workflow-runner",
            )
        elif event.event_type is TraceEventType.AGENT_ERROR:
            self.service.update_workflow_step(
                self.run_id, step_id,
                status=WorkflowStepStatus.FAILED,
                metadata_patch={"error_message": str(event.data.get("error"))},
                actor="workflow-runner",
            )
```

`update_workflow_step` already rolls run status up correctly
(`_roll_up_workflow_run_status` in `service.py`), so no additional
status logic is needed for the run itself.

### Cancellation, Retry, Idempotency

- **Cancel** flips the per-run `threading.Event` and updates the
  current step to `CANCELLED` (new `WorkflowStepStatus`); the
  orchestrator checks the event between steps and raises a
  `WorkflowCancelled` exception, which the executor catches and
  translates to `WorkflowRunStatus.CANCELLED`.
- **Retry of a failed step.** Out of scope for Phase 1. Today's UI
  retry handler patches the step back to `running` (not actually
  re-executing). Phase 1 documents this as a known no-op for
  agentic runs and disables the action when `workflow_mode ==
  AGENTIC`. Phase 2 (FR-31c) introduces resumable runs by
  serializing `AgentState` to the run row and letting the executor
  resume from a checkpoint.
- **Idempotency.** `start_workflow_run` rejects (409) when the run
  is not `QUEUED`. Re-submitting a `RUNNING` run returns the
  existing future without spawning a second worker.

### Failure Modes and Error Surface

| Failure                                       | Behavior                                                                 |
|-----------------------------------------------|--------------------------------------------------------------------------|
| Connection verification fails before run      | Run → `FAILED`, no steps touched, error on run.metadata.error_message    |
| LLM provider misconfigured                    | Run → `FAILED` at submit, same surface                                   |
| Step raises during execution                  | Step → `FAILED`, run rolls up to `FAILED`, error in step.metadata        |
| Worker thread dies unexpectedly               | Watchdog timer (Phase 1: 30 min) flips run to `FAILED` with timeout msg  |
| API process restart mid-run                   | Startup sweep flips orphaned `RUNNING` runs to `FAILED` with stale msg   |
| User cancels mid-run                          | Active step → `CANCELLED`, run → `CANCELLED`, audit event recorded       |

### Audit and Observability

- A new audit event `action="execute_workflow"` is recorded at
  workflow start with `details={"run_id", "workflow_mode", "graph_profile_id"}`.
- A second audit event at workflow end with
  `details={"run_id", "outcome", "duration_ms", "report_count", "error_count"}`.
- Per-step trace events from the runner are persisted into a new
  optional collection `aga_workflow_run_traces` keyed by `(run_id,
  event_id)` so the canvas can later expose a "View Trace" affordance
  (Phase 2). Phase 1 only writes the events; the UI consumer is FR-32a.

### Migration / Backward Compatibility

- Existing demo runs (those with the four legacy step labels) are
  not migrated. They render exactly as today; the new behavior
  applies only to runs created after the deploy when `workflow_mode
  == AGENTIC`.
- `WorkflowMode.TRADITIONAL` is unchanged: free-form steps, manual
  PATCH-driven progression. This preserves the existing demo UX.
- The frontend's "type your own steps" textarea is hidden in
  agentic mode but otherwise untouched.

### Risks and Mitigations

- **In-process execution does not survive restart.** Real risk for
  long LLM workflows. Phase 1 mitigation: startup sweep marks
  orphaned runs `FAILED`; document the limitation in the FR-30
  retry/resume requirement and gate "agentic-at-scale" claims on
  Phase 2 (FR-31b: durable executor). For local dev and single-
  instance deploys this is acceptable.
- **One slow run blocks the worker pool.** Bounded
  `ThreadPoolExecutor(max_workers=N)` with N tuned per deploy;
  surface "queued" vs "running" distinction so users see when
  their run is waiting.
- **LLM cost runaway.** The runner already supports
  `max_executions`; expose it on `POST /api/runs` as
  `metadata.max_executions` (default 3) and reject values > 10
  unless an admin override is set.
- **Step status race when a user PATCHes a step the executor is
  also updating.** Phase 1 disables the manual step PATCH for
  `WorkflowMode.AGENTIC` runs (UI hides retry/cancel buttons on
  individual steps; only run-level cancel is allowed). The PATCH
  endpoint returns 409 for agentic runs.
- **Secret leakage in trace events.** `record_event` data is dict
  payload; the bridge runs `validate_no_secret_values` on
  metadata before persisting. Reuse the existing helper from
  `models.py`.

### Required Code Changes (preview, not authoritative)

1. **New module** `graph_analytics_ai/product/agentic_run_supervisor.py`:
   `AgenticRunSupervisor` class, `StepStatusReporter`,
   `LLMProviderFactory`, `AGENTIC_STEP_LAYOUT` constant.
2. **`graph_analytics_ai/product/service.py`**:
   `start_workflow_run` branches on `workflow_mode`; submits to
   executor when AGENTIC. New `cancel_workflow_run` method. New
   `_seed_agentic_steps` helper used by `create_workflow_run_from_steps`.
3. **`graph_analytics_ai/product/api.py`**: new `POST
   /api/runs/{run_id}/cancel` and `GET /api/runs/{run_id}/status`
   endpoints.
4. **`graph_analytics_ai/ai/tracing/__init__.py`**: small refactor to
   add `TraceCollector.add_listener(callback)` so the bridge does
   not have to monkey-patch `record_event`.
5. **`graph_analytics_ai/ai/agents/orchestrator.py`**: thread the
   `cancel_token` through `run_workflow` / `run_workflow_async` and
   check it between steps.
6. **`graph_analytics_ai/product/factory.py`**: wire an
   `AgenticRunSupervisor` instance into the FastAPI app's lifespan so
   it shuts down cleanly (drains the pool, marks in-flight runs
   `failed` with `shutdown_in_progress` reason).
7. **Frontend**:
   - `CreateWorkflowRunOverlay.tsx`: hide step textarea when
     `workflow_mode === "agentic"` and show canonical layout
     preview.
   - `useWorkspaceData.ts`: add `cancelWorkflowRun`,
     `getWorkflowRunStatus`; existing polling already refreshes the
     overview so step status will appear without further changes.
   - `WorkspaceShell.tsx`: hide per-step retry on agentic runs, add
     run-level cancel button.
8. **Tests**:
   - Unit tests for `AgenticRunSupervisor.submit` with a fake runner
     that emits scripted trace events.
   - Unit tests for `StepStatusReporter` event → `update_workflow_step`
     translation (start, end, error, unknown step).
   - Integration test: `start_workflow_run` with AGENTIC mode and a
     stub runner produces the expected sequence of step status rows
     and a `COMPLETED` run.
   - Cancellation test: cancel mid-run produces `CANCELLED` status
     and an audit event.
   - Frontend test: agentic-mode overlay renders the canonical
     preview and POSTs without a `steps` field.

### Phasing

- **FR-31a (this plan).** In-process executor, six-step canonical
  layout, status streaming, cooperative cancel.
- **FR-31b.** Durable executor (Celery or Arq), survives API
  restart, supports run resume from `AgentState` checkpoint.
- **FR-31c.** Per-step retry that actually re-invokes the agent
  with the prior `AgentState`.
- **FR-31d.** Live trace event streaming to the UI (SSE) so the
  visualizer reflects sub-step progress (LLM calls, tool
  invocations) instead of just step boundaries.

### Acceptance Criteria for FR-31a Phase 1

**Status: shipped on `feature/product-ui-foundation` (PRD v0.5).**
A live smoke test against real ArangoDB + LLM provider is the
remaining gate before tagging Phase 1 as production-ready (and
before starting FR-31b).

1. ✅ Creating an agentic workflow run seeds the six canonical steps
   in order, regardless of any client-supplied step labels.
2. ✅ Calling `POST /api/runs/{id}/start` returns immediately with
   `status: running` and triggers a real `AgenticWorkflowRunner`
   execution in a background worker thread.
3. ✅ Each canonical step transitions through
   `pending → running → succeeded` (or `failed`) without any UI
   PATCH calls — driven by `StepStatusReporter` consuming
   `STEP_START`, `STEP_END`, and `AGENT_ERROR` trace events.
4. ✅ A failed step records the agent's error message in
   `step.errors` and rolls the run up to `failed`.
5. ✅ `POST /api/runs/{id}/cancel` cancels an in-flight run; the
   active step lands as `cancelled` and the run as `cancelled`
   within one orchestrator step boundary. Pending steps also flip
   to `cancelled` via `_finalize_run`.
6. ✅ The audit timeline shows a paired `start_workflow_run` /
   `execute_workflow` event with outcome and step count
   (duration is implicit from the timestamps; explicit duration
   field is FR-31b territory).
7. ✅ API process restart mid-run leaves the run row in a
   recoverable state (`failed` with `stale_run_detected` reason)
   via `sweep_orphan_runs()` on supervisor init.
8. ✅ Manual step PATCH on an agentic run returns 409
   (`ConflictError`) so external callers cannot race with the
   executor; the supervisor itself uses an internal-only
   `_internal=True` bypass.
9. ✅ Connection or LLM misconfiguration produces a `failed` run
   with a clear error before any step transitions to `running` —
   the supervisor catches initialization errors during
   `_build_db_connection` / `LLMProviderFactory.for_workspace`
   and finalizes the run as `failed` immediately.

---

## Open Questions

1. Should product metadata collections use `aga_` or `analysis_` naming?
2. Should original documents be stored in ArangoDB, object storage, or both?
3. What is the first supported deployment mode: local product console, customer-hosted app, or both?
4. What authentication model is required for the MVP?
5. Should reports be editable after generation or only regenerated from source state?
6. Which report export formats are mandatory for the first release?
7. Should workflow progress use polling first, or should the MVP include server-sent events/websockets?
8. Should the UI call Python service APIs only, or should some MCP tools be reused internally?
9. **(v0.6)** Should `arangodb-schema-analyzer` be a hard dependency or
   an optional extra? Hard makes the heuristic fallback dead code in
   production but simplifies operations; optional preserves the
   `arango-cypher-py` pattern but means production deployments must
   be policy-checked. Recommendation: hard dependency for the product
   API; the underlying `graph_analytics_ai` library keeps it as an
   extra so library users keep the choice.
10. **(v0.6)** What is the right default for `schema_strategy` in
    workspaces that contain hybrid (PG + LPG) data? The `auto`
    strategy escalates to LLM on every `LABEL` collection that doesn't
    pin a tier-1 type field, which can be costly. Two viable choices:
    (a) auto, accept the LLM cost; (b) `analyzer-baseline-only` by
    default, escalate to LLM on user-clicked "Improve schema accuracy"
    button. Recommendation: (a) for first run on a new connection
    profile, (b) for refreshes.
11. **(v0.6)** When a workspace contains a corpus + KG pair, should
    the GraphSet be auto-created on discovery, or should the user
    explicitly group them? Auto is a better demo; explicit is safer
    for customers with multiple unrelated graphs. Recommendation: auto-
    create when (a) the discovery run finds exactly one `corpus`
    profile and exactly one `knowledge_graph` profile in the same
    database, AND (b) at least one cross-graph link is detected; in
    every other case prompt the user.
12. **(v0.6)** GAE typed projections: when (if ever) should the
    executor reuse a prior projection vs build a fresh one? Reuse
    saves cost but risks staleness if the underlying KG was updated.
    Recommendation: reuse iff the projection's `shape_fingerprint` of
    the source collection (computed on projection creation) matches
    the current shape; otherwise rebuild.
13. **(v0.6)** Do we need to expose the OWL Turtle export to the UI in
    Phase 6, or defer to v0.7? It's free metadata and adds maybe 30
    LOC to the API; the UI cost is the question. Recommendation:
    expose via `GET /api/graph-profiles/{id}/owl-turtle` in Phase 6a
    (cheap), defer the rendered UI tab to v0.7.

---

## Acceptance Criteria for MVP

The MVP is complete when:

1. A user can create a workspace through the UI.
2. A user can configure and test a customer database connection without editing `.env`.
3. A user can discover a named graph and save a graph profile.
4. A user can upload requirements and approve a requirement version.
5. A user can use Requirements Copilot to create an editable BRD draft from schema context and guided domain/use-case questions.
6. Copilot-generated statements include provenance labels for observed schema facts, inferred context, user-provided facts, and assumptions requiring confirmation.
7. A user can iterate from an approved Requirements v(N) to v(N+1) via the
   Reopen Copilot flow, with the prior version's domain and answers
   pre-filled and the prior version automatically transitioned to
   `superseded` upon approval.
8. The Assets panel surfaces ONE consolidated **Requirements** entry per
   workspace, and the canvas exposes a version selector dropdown that
   defaults to the active version. Historical versions are viewable
   read-only and individually deep-linkable via
   `?requirementVersion=<id>`.
9. A user can generate and approve at least one use case and template.
10. A user can launch a workflow from the UI.
11. A user can monitor the workflow through a visual run DAG with step status, dependencies, and artifact links.
12. A completed run is stored in the Analysis Catalog.
13. A dynamic report renders from database records.
14. A report can be exported to at least HTML and Markdown.
15. A published report links back to requirements, use case, template, execution, and result collection.
16. AdTech-style YAML/docs and clinical trials/CRO or open source intelligence templates can be imported through a preview-and-apply flow.
17. Secret values are not stored in product metadata collections.
18. **(v0.6)** Discovering an ArangoDB GraphRAG project (corpus + KG)
    in the same database produces two `GraphProfile` rows with
    `schema_kind ∈ {pg, lpg}`, `graph_purpose ∈ {corpus,
    knowledge_graph}`, populated `conceptual_schema` and
    `physical_mapping`, and at least one auto-detected candidate
    cross-graph link (e.g., `MENTIONED_IN`).
19. **(v0.6)** Discovering an HRIS-style PG database (e.g., Employee /
    Department / Position collections with dedicated `reports_to` /
    `holds_position` edges) produces one `GraphProfile` with
    `schema_kind == pg`, `graph_purpose == structured`, and the
    pre-v0.6 collection-centric metadata fields populated for
    backward compatibility.
20. **(v0.6)** A workflow run on a `LABEL` entity (e.g., PageRank on
    Person within a GraphRAG KG) materializes a typed projection,
    runs the algorithm against it, records the projection ID on the
    `analysis_executions` row, and the resulting report displays per-
    Person results with chunk and document provenance citations.
21. **(v0.6)** When `arangodb-schema-analyzer` is not installed, the
    discovery flow still produces a heuristic `GraphProfile` with
    `analyzer_metadata.warnings` containing
    `ANALYZER_NOT_INSTALLED` and the UI displays a "Schema accuracy
    is degraded" banner.
22. **(v0.6)** The schema-change probe API returns
    `unchanged | stats_changed | shape_changed | no_cache` in under
    200ms on a 50-collection database with cached state.
23. **(v0.6)** A property tagged `restricted` by the sensitivity
    classifier is redacted from the Requirements Copilot LLM
    context, suppressed from default report tables, and every
    explicit reveal is recorded in the audit log.

