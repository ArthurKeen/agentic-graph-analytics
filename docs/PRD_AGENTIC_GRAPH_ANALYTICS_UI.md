# Product Requirements Document: Agentic Graph Analytics UI

**Version:** 0.1  
**Date:** 2026-04-30  
**Status:** Draft  
**Target Release:** Product UI MVP  
**Related Document:** [Agentic Graph Analytics UI Vision](UI_PRODUCT_VISION.md)

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

- **FR-1:** Users can create, view, update, archive, and export workspaces.
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

### Requirements Copilot

- **RC-1:** Users can launch a guided Requirements Copilot session from a graph profile or Requirements Studio.
- **RC-2:** The copilot uses graph schema context, including named graphs, collections, edge definitions, counts, sample fields, and collection roles.
- **RC-3:** The copilot asks domain and use-case discovery questions before drafting requirements.
- **RC-4:** The copilot captures constraints including runtime, cost, refresh cadence, data sensitivity, reporting audience, and required evidence.
- **RC-5:** The copilot generates an editable BRD draft with domain description, business objectives, analytics questions, success criteria, assumptions, constraints, and candidate GAE use cases.
- **RC-6:** Each generated statement is labeled as observed from schema, inferred from schema, user-provided, or assumption requiring confirmation.
- **RC-7:** Copilot-generated requirements must be reviewed and approved before use-case or template generation.

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
- **FR-42:** Users can export reports to HTML, Markdown, JSON, and PDF.
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

### Document and Requirement APIs

- `POST /api/workspaces/{workspace_id}/documents`
- `GET /api/workspaces/{workspace_id}/documents`
- `POST /api/documents/{document_id}/extract`
- `POST /api/workspaces/{workspace_id}/requirements-copilot/sessions`
- `GET /api/requirements-copilot/sessions/{session_id}`
- `POST /api/requirements-copilot/sessions/{session_id}/answer`
- `POST /api/requirements-copilot/sessions/{session_id}/generate-draft`
- `POST /api/workspaces/{workspace_id}/requirement-versions`
- `POST /api/requirement-versions/{requirement_version_id}/approve`

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

### Requirements Studio

Must display:

- Source document list
- Requirements Copilot entry point
- Guided domain and use-case interview
- Schema observations used by the copilot
- Extracted requirements
- Editable BRD draft
- Provenance labels for generated statements
- Requirement versions
- Approval status
- Links to generated use cases

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

---

## Acceptance Criteria for MVP

The MVP is complete when:

1. A user can create a workspace through the UI.
2. A user can configure and test a customer database connection without editing `.env`.
3. A user can discover a named graph and save a graph profile.
4. A user can upload requirements and approve a requirement version.
5. A user can use Requirements Copilot to create an editable BRD draft from schema context and guided domain/use-case questions.
6. Copilot-generated statements include provenance labels for observed schema facts, inferred context, user-provided facts, and assumptions requiring confirmation.
7. A user can generate and approve at least one use case and template.
8. A user can launch a workflow from the UI.
9. A user can monitor the workflow through a visual run DAG with step status, dependencies, and artifact links.
10. A completed run is stored in the Analysis Catalog.
11. A dynamic report renders from database records.
12. A report can be exported to at least HTML and Markdown.
13. A published report links back to requirements, use case, template, execution, and result collection.
14. AdTech-style YAML/docs and clinical trials/CRO or open source intelligence templates can be imported through a preview-and-apply flow.
15. Secret values are not stored in product metadata collections.

