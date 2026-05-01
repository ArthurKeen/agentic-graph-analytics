import { describe, expect, it, vi } from "vitest";

import {
  createProductAPIClient,
  mapReportBundle,
  mapWorkflowDAGView,
  mapWorkspaceHealth,
  mapWorkspaceOverview,
  workspaceAssetsFromOverview
} from "../client";

describe("product API client mappers", () => {
  it("maps workspace overview payloads into UI assets", () => {
    const overview = mapWorkspaceOverview({
      workspace: {
        workspace_id: "workspace-1",
        customer_name: "Example",
        project_name: "Graph Analytics",
        environment: "dev"
      },
      counts: { workflow_runs: 1, reports: 1 },
      latest_graph_profiles: [
        {
          graph_profile_id: "graph-profile-1",
          graph_name: "CustomerGraph",
          status: "active"
        }
      ],
      latest_source_documents: [
        {
          document_id: "document-1",
          filename: "requirements.md",
          mime_type: "text/markdown"
        }
      ],
      latest_workflow_runs: [
        {
          run_id: "run-1",
          status: "running",
          workflow_mode: "agentic"
        }
      ],
      latest_reports: [
        {
          report_id: "report-1",
          title: "Risk Report",
          status: "draft"
        }
      ]
    });

    expect(overview.latestWorkflowRuns[0].run_id).toBe("run-1");
    expect(workspaceAssetsFromOverview(overview)).toEqual([
      {
        id: "graph-profile-1",
        kind: "graph-profile",
        label: "CustomerGraph",
        description: "Graph profile (active)"
      },
      {
        id: "document-1",
        kind: "document",
        label: "requirements.md",
        description: "text/markdown"
      },
      {
        id: "run-1",
        kind: "run",
        label: "Run run-1",
        description: "agentic workflow (running)"
      },
      {
        id: "report-1",
        kind: "report",
        label: "Risk Report",
        description: "Report (draft)"
      }
    ]);
  });

  it("maps workflow DAG payloads into canvas-friendly shape", () => {
    const dag = mapWorkflowDAGView({
      run_id: "run-1",
      workspace_id: "workspace-1",
      status: "running",
      workflow_mode: "agentic",
      nodes: [
        {
          id: "step-1",
          label: "Extract",
          status: "completed",
          agent_name: "extractor",
          artifact_count: 2,
          warning_count: 1,
          error_count: 0
        }
      ],
      edges: [{ id: "edge-1", from: "step-1", to: "step-2" }],
      warnings: [],
      errors: []
    });

    expect(dag.runId).toBe("run-1");
    expect(dag.nodes[0]).toMatchObject({
      id: "step-1",
      agentName: "extractor",
      artifactCount: 2
    });
    expect(dag.edges[0]).toEqual({ id: "edge-1", from: "step-1", to: "step-2" });
  });

  it("maps workspace health payloads into explorer-ready shape", () => {
    const health = mapWorkspaceHealth({
      workspace_id: "workspace-1",
      status: "needs_attention",
      counts: { connection_profiles: 0 },
      issues: [
        {
          severity: "warning",
          code: "missing_connection_profile",
          message: "Workspace has no connection profiles.",
          entity_ids: ["connection-1"]
        }
      ]
    });

    expect(health.workspaceId).toBe("workspace-1");
    expect(health.issues[0]).toEqual({
      severity: "warning",
      code: "missing_connection_profile",
      message: "Workspace has no connection profiles.",
      entityIds: ["connection-1"]
    });
  });

  it("maps and orders report bundles for dynamic rendering", () => {
    const report = mapReportBundle({
      manifest: {
        report_id: "report-1",
        workspace_id: "workspace-1",
        run_id: "run-1",
        title: "Risk Report",
        status: "draft",
        summary: "Summary",
        version: 2
      },
      sections: [
        {
          section_id: "section-2",
          order: 2,
          type: "recommendation",
          title: "Recommendation",
          content: { text: "Act" }
        },
        {
          section_id: "section-1",
          order: 1,
          type: "summary",
          title: "Summary",
          content: { text: "Read" }
        }
      ],
      charts: [
        {
          chart_id: "chart-1",
          title: "Counts",
          chart_type: "table",
          data: { rows: [] }
        }
      ],
      snapshots: []
    });

    expect(report.manifest.reportId).toBe("report-1");
    expect(report.sections.map((section) => section.sectionId)).toEqual([
      "section-1",
      "section-2"
    ]);
    expect(report.charts[0]).toMatchObject({
      chartId: "chart-1",
      chartType: "table"
    });
  });

  it("publishes reports through the product API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        manifest: {
          report_id: "report-1",
          workspace_id: "workspace-1",
          run_id: "run-1",
          title: "Risk Report",
          status: "published"
        },
        sections: [],
        charts: [],
        snapshots: []
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const report = await createProductAPIClient("http://api.example").publishReport(
      "report-1",
      "tester"
    );

    expect(report.manifest.status).toBe("published");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/reports/report-1/publish",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ actor: "tester" })
      })
    );

    vi.unstubAllGlobals();
  });
});
