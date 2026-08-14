"""Constants for Agentic Graph Analytics product metadata."""

# Bumped to 1.4.0 for FR-19..FR-26: aga_use_cases and aga_analysis_templates
# join the additive collection set (1.3.0 added the Analysis Catalog pair).
# The bundle import path accepts the open set 1.0.0 .. 1.4.0 so older callers
# can still round-trip.
PRODUCT_SCHEMA_VERSION = "1.4.0"

META_COLLECTION = "aga_product_meta"
WORKSPACES_COLLECTION = "aga_workspaces"
CONNECTION_PROFILES_COLLECTION = "aga_connection_profiles"
GRAPH_PROFILES_COLLECTION = "aga_graph_profiles"
COLLECTION_ROLES_COLLECTION = "aga_collection_roles"
DOCUMENTS_COLLECTION = "aga_documents"
REQUIREMENT_INTERVIEWS_COLLECTION = "aga_requirement_interviews"
REQUIREMENT_VERSIONS_COLLECTION = "aga_requirement_versions"
WORKFLOW_RUNS_COLLECTION = "aga_workflow_runs"
REPORT_MANIFESTS_COLLECTION = "aga_report_manifests"
REPORT_SECTIONS_COLLECTION = "aga_report_sections"
CHART_SPECS_COLLECTION = "aga_chart_specs"
PUBLISHED_SNAPSHOTS_COLLECTION = "aga_published_snapshots"
AUDIT_EVENTS_COLLECTION = "aga_audit_events"
# PRD v0.6 / FR-59: persistent L2 cache backing
# graph_analytics_ai.ai.schema.acquire. Stores acquisition bundles
# keyed by hash(database, graph_name) plus shape/full fingerprints
# so repeated discoveries skip the analyzer and ordinary writes
# only refresh statistics.
SCHEMA_SNAPSHOTS_COLLECTION = "aga_schema_snapshots"
# PRD v0.6 / FR-68..FR-70: curated grouping of multiple GraphProfile
# rows within a workspace. Encodes the "this workspace's analyses
# operate over corpus_g + acme_kg + hris_pg, with these cross-graph
# bridges" relationship so GAE projections + Requirements Copilot
# can target the right combination.
GRAPH_SETS_COLLECTION = "aga_graph_sets"
# FR-31 / FR-45..FR-48: the product-layer Analysis Catalog. These MIRROR
# the AI-layer catalog (graph_analytics_ai/catalog/), which is global and
# has no workspace scoping — product rows carry workspace_id, own their
# own ids/lifecycle, and keep a soft `catalog_execution_id` /
# `catalog_epoch_id` back-pointer to the AI-layer row when one exists.
# Mirroring rather than proxying keeps the product API off catalog/
# internals.
ANALYSIS_EXECUTIONS_COLLECTION = "aga_analysis_executions"
ANALYSIS_EPOCHS_COLLECTION = "aga_analysis_epochs"
# FR-19..FR-26: product-layer Use Cases and Analysis Templates. The AI layer
# (ai/generation/use_cases.py, ai/templates/models.py) has dataclasses for both
# but no ids, no to_dict/from_dict, and no persistence — they exist only inside
# a running agent pipeline. These are first-class workspace-scoped records with
# their own lifecycle, so users can author and approve them directly.
USE_CASES_COLLECTION = "aga_use_cases"
ANALYSIS_TEMPLATES_COLLECTION = "aga_analysis_templates"

PRODUCT_COLLECTIONS = [
    META_COLLECTION,
    WORKSPACES_COLLECTION,
    CONNECTION_PROFILES_COLLECTION,
    GRAPH_PROFILES_COLLECTION,
    COLLECTION_ROLES_COLLECTION,
    DOCUMENTS_COLLECTION,
    REQUIREMENT_INTERVIEWS_COLLECTION,
    REQUIREMENT_VERSIONS_COLLECTION,
    WORKFLOW_RUNS_COLLECTION,
    REPORT_MANIFESTS_COLLECTION,
    REPORT_SECTIONS_COLLECTION,
    CHART_SPECS_COLLECTION,
    PUBLISHED_SNAPSHOTS_COLLECTION,
    AUDIT_EVENTS_COLLECTION,
    SCHEMA_SNAPSHOTS_COLLECTION,
    GRAPH_SETS_COLLECTION,
    ANALYSIS_EXECUTIONS_COLLECTION,
    ANALYSIS_EPOCHS_COLLECTION,
    USE_CASES_COLLECTION,
    ANALYSIS_TEMPLATES_COLLECTION,
]
