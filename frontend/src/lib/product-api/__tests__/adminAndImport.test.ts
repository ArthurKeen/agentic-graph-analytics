import { describe, expect, it, vi } from "vitest";

import {
  createProductAPIClient,
  mapGraphProfileSummary,
  mapRetentionPolicy,
  mapRetentionSweepResult,
  mapVerticalProjectImportResult
} from "../client";

/**
 * Every payload below was captured by running the real Python service and
 * dumping the response, not hand-written from the type definitions. A previous
 * contract bug (FR-36/37) survived both test suites precisely because the
 * frontend test invented field names the backend never sent.
 */

const RETENTION_POLICY_UNSET = {
  workspace_id: "workspace-1",
  enabled: false,
  draft_retention_days: 0,
  run_retention_days: 0,
  document_retention_days: 0,
  report_snapshot_retention_days: 0,
  audit_log_retention_days: 0,
  configured: false
  // NOTE: the unset response carries no last_applied_at key at all.
};

const RETENTION_POLICY_SET = {
  _key: "retention-policy-1",
  retention_policy_id: "retention-policy-1",
  workspace_id: "workspace-1",
  enabled: true,
  draft_retention_days: 30,
  run_retention_days: 90,
  document_retention_days: 0,
  report_snapshot_retention_days: 0,
  audit_log_retention_days: 0,
  created_at: "2026-08-16T18:56:19.414340+00:00",
  updated_at: "2026-08-16T18:56:19.414344+00:00",
  updated_by: null,
  last_applied_at: null,
  metadata: {},
  configured: true
};

const RETENTION_DRY_RUN = {
  workspace_id: "workspace-1",
  deleted: false,
  enabled: true,
  candidates: {
    drafts: [
      {
        id: "requirement-version-1",
        collection: "aga_requirement_versions",
        label: "v1 (draft)"
      }
    ],
    runs: [
      {
        id: "run-1",
        collection: "aga_workflow_runs",
        label: "agentic",
        ephemeral: false
      }
    ],
    documents: [],
    report_snapshots: [],
    audit_logs: []
  },
  protected: { published_report_ids: [], runs_with_published_reports: [] },
  counts: { drafts: 1, runs: 1, documents: 0, report_snapshots: 0, audit_logs: 0 }
};

const VERTICAL_IMPORT = {
  workspace_id: "workspace-1",
  vertical: "adtech",
  project_name: "Audience Planning",
  use_cases: [{ use_case_id: "use-case-1", title: "Rank audiences by influence" }],
  templates: [{ analysis_template_id: "analysis-template-1", name: "PageRank" }],
  counts: { use_cases: 1, templates: 1 },
  warnings: []
};

const SHARDED_GRAPH_PROFILE = {
  graph_profile_id: "graph-profile-1",
  workspace_id: "workspace-1",
  connection_profile_id: "connection-1",
  graph_name: "demo",
  status: "discovered",
  version: 1,
  vertex_collections: ["Account"],
  edge_collections: ["Transfer"],
  edge_definitions: [],
  collection_roles: {},
  counts: {},
  analyzer_metadata: {
    sharding_profile: {
      deployment_kind: "cluster",
      is_one_shard: false,
      is_multitenant: true,
      tenant_key: "tenant_id",
      shard_keys: ["tenant_id"],
      smart_graph_attributes: [],
      max_number_of_shards: 6,
      min_replication_factor: 2,
      satellite_collections: [],
      warnings: [
        "Collections are sharded by 'tenant_id'; a cross-tenant analysis will span shards and may mix tenants."
      ]
    }
  }
};

describe("retention policy (FR-54)", () => {
  it("maps an unconfigured policy without inventing a configured state", () => {
    const policy = mapRetentionPolicy(RETENTION_POLICY_UNSET);

    expect(policy.configured).toBe(false);
    expect(policy.enabled).toBe(false);
    expect(policy.draftRetentionDays).toBe(0);
    // The unset payload omits last_applied_at entirely — the mapper must not
    // turn a missing key into a bogus timestamp.
    expect(policy.lastAppliedAt ?? null).toBeNull();
  });

  it("maps a configured policy", () => {
    const policy = mapRetentionPolicy(RETENTION_POLICY_SET);

    expect(policy).toMatchObject({
      workspaceId: "workspace-1",
      configured: true,
      enabled: true,
      draftRetentionDays: 30,
      runRetentionDays: 90
    });
  });

  it("sends only the windows the admin actually edited", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => RETENTION_POLICY_SET });
    vi.stubGlobal("fetch", fetchMock);

    await createProductAPIClient("http://api.example").setRetentionPolicy(
      "workspace-1",
      { runRetentionDays: 90 }
    );

    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    // A partial edit must not silently reset every other window to 0.
    expect(body).toEqual({ run_retention_days: 90 });
    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://api.example/api/workspaces/workspace-1/retention-policy"
    );
    expect(fetchMock.mock.calls[0][1].method).toBe("PUT");
  });

  it("marks a dry run as not deleted so the UI can offer a confirmation", () => {
    const sweep = mapRetentionSweepResult(RETENTION_DRY_RUN);

    expect(sweep.deleted).toBe(false);
    expect(sweep.counts.drafts).toBe(1);
    expect(sweep.counts.runs).toBe(1);
    expect(sweep.candidates.drafts[0].label).toBe("v1 (draft)");
  });

  it("treats an unknown response as already deleted", () => {
    // The dangerous direction is showing "nothing was deleted" when the
    // server actually deleted, so an ambiguous payload reads as deleted.
    const sweep = mapRetentionSweepResult({ workspace_id: "workspace-1" });

    expect(sweep.deleted).toBe(true);
  });

  it("defaults the sweep to a dry run", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => RETENTION_DRY_RUN });
    vi.stubGlobal("fetch", fetchMock);

    await createProductAPIClient("http://api.example").applyRetentionPolicy(
      "workspace-1"
    );

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ dry_run: true });
  });

  it("only deletes when the caller explicitly asks", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ...RETENTION_DRY_RUN, deleted: true, removed: 2 })
    });
    vi.stubGlobal("fetch", fetchMock);

    const sweep = await createProductAPIClient(
      "http://api.example"
    ).applyRetentionPolicy("workspace-1", false);

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ dry_run: false });
    expect(sweep.deleted).toBe(true);
    expect(sweep.removed).toBe(2);
  });
});

describe("vertical project import (FR-49/FR-50)", () => {
  it("maps the import summary", () => {
    const result = mapVerticalProjectImportResult(VERTICAL_IMPORT);

    expect(result).toEqual({
      workspaceId: "workspace-1",
      vertical: "adtech",
      projectName: "Audience Planning",
      counts: { use_cases: 1, templates: 1 },
      warnings: []
    });
  });

  it("posts the bundle document and its declared format", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => VERTICAL_IMPORT });
    vi.stubGlobal("fetch", fetchMock);

    await createProductAPIClient("http://api.example").importVerticalProject(
      "workspace-1",
      "vertical: adtech\nname: Audience Planning\n",
      "yaml"
    );

    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://api.example/api/workspaces/workspace-1/vertical-projects/import"
    );
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      document: "vertical: adtech\nname: Audience Planning\n",
      document_format: "yaml"
    });
  });
});

describe("sharding profile on the graph profile (FR-65)", () => {
  it("carries the sharding profile out of analyzer_metadata", () => {
    const profile = mapGraphProfileSummary(SHARDED_GRAPH_PROFILE);

    expect(profile.shardingProfile).toMatchObject({
      deploymentKind: "cluster",
      isMultitenant: true,
      tenantKey: "tenant_id",
      maxNumberOfShards: 6,
      minReplicationFactor: 2
    });
    // The warning is what drives the cross-tenant run confirmation.
    expect(profile.shardingProfile?.warnings[0]).toContain("cross-tenant");
  });

  it("leaves the sharding profile null on a profile discovered before FR-65", () => {
    const { analyzer_metadata: _omitted, ...legacy } = SHARDED_GRAPH_PROFILE;

    const profile = mapGraphProfileSummary(legacy);

    // A missing profile must read as "unknown", never as single-tenant —
    // otherwise the cross-tenant warning silently stops firing.
    expect(profile.shardingProfile ?? null).toBeNull();
  });
});
