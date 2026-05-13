"""Constants for Agentic Graph Analytics product metadata."""

# Bumped to 1.2.0 in Phase 6c: aga_graph_sets joins aga_schema_snapshots
# as the second additive v0.6 collection. The bundle import path accepts
# the open set 1.0.0 / 1.1.0 / 1.2.0 so older callers can still round-trip.
PRODUCT_SCHEMA_VERSION = "1.2.0"

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
]

