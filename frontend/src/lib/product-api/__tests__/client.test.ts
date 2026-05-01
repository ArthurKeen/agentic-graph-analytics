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
      latest_connection_profiles: [
        {
          connection_profile_id: "connection-1",
          workspace_id: "workspace-1",
          name: "Development",
          deployment_mode: "local",
          endpoint: "http://localhost:8529",
          database: "customer_graph",
          username: "root",
          last_verification_status: "unknown"
        }
      ],
      latest_graph_profiles: [
        {
          graph_profile_id: "graph-profile-1",
          workspace_id: "workspace-1",
          connection_profile_id: "connection-1",
          graph_name: "CustomerGraph",
          status: "active",
          version: 2,
          vertex_collections: ["customers"],
          edge_collections: ["transactions"],
          counts: { customers: 10 }
        }
      ],
      latest_source_documents: [
        {
          document_id: "document-1",
          workspace_id: "workspace-1",
          filename: "requirements.md",
          mime_type: "text/markdown",
          sha256: "abc123",
          storage_mode: "inline_text",
          extracted_text: "Requirements content",
          metadata: { source: "upload" }
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
    expect(overview.latestConnectionProfiles[0]).toMatchObject({
      connectionProfileId: "connection-1",
      name: "Development",
      deploymentMode: "local"
    });
    expect(overview.latestGraphProfiles[0]).toMatchObject({
      graphProfileId: "graph-profile-1",
      graphName: "CustomerGraph",
      vertexCollections: ["customers"],
      counts: { customers: 10 }
    });
    expect(overview.latestSourceDocuments[0]).toMatchObject({
      documentId: "document-1",
      filename: "requirements.md",
      storageMode: "inline_text",
      metadata: { source: "upload" }
    });
    expect(workspaceAssetsFromOverview(overview)).toEqual([
      {
        id: "connection-1",
        kind: "connection-profile",
        label: "Development",
        description: "local connection (unknown)"
      },
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

  it("creates connection profiles through the product API without plaintext secrets", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        connection_profile_id: "connection-1",
        workspace_id: "workspace-1",
        name: "Development",
        deployment_mode: "local",
        endpoint: "http://localhost:8529",
        database: "customer_graph",
        username: "root",
        verify_ssl: false,
        secret_refs: { password: { kind: "env", ref: "ARANGO_PASSWORD" } }
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const profile = await createProductAPIClient(
      "http://api.example"
    ).createConnectionProfile("workspace-1", {
      name: "Development",
      deploymentMode: "local",
      endpoint: "http://localhost:8529",
      database: "customer_graph",
      username: "root",
      verifySsl: false,
      passwordSecretEnvVar: "ARANGO_PASSWORD"
    });

    expect(profile.connectionProfileId).toBe("connection-1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/workspaces/workspace-1/connection-profiles",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          name: "Development",
          deployment_mode: "local",
          endpoint: "http://localhost:8529",
          database: "customer_graph",
          username: "root",
          verify_ssl: false,
          secret_refs: { password: { kind: "env", ref: "ARANGO_PASSWORD" } }
        })
      })
    );

    vi.unstubAllGlobals();
  });

  it("verifies connection profiles through the product API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        connection_profile_id: "connection-1",
        workspace_id: "workspace-1",
        status: "success",
        verified_at: "2026-01-01T00:00:00Z",
        endpoint: "http://localhost:8529",
        database: "customer_graph",
        error_message: null
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await createProductAPIClient(
      "http://api.example"
    ).verifyConnectionProfile("connection-1");

    expect(result).toMatchObject({
      connectionProfileId: "connection-1",
      status: "success",
      errorMessage: null
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/connection-profiles/connection-1/verify",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({})
      })
    );

    vi.unstubAllGlobals();
  });

  it("discovers graph profiles through the product API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        graph_profile: {
          graph_profile_id: "graph-profile-1",
          workspace_id: "workspace-1",
          connection_profile_id: "connection-1",
          graph_name: "CustomerGraph",
          status: "active",
          vertex_collections: ["customers"],
          edge_collections: ["transactions"]
        },
        schema_summary: {
          database_name: "customer_graph"
        }
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const discovery = await createProductAPIClient(
      "http://api.example"
    ).discoverGraphProfile("connection-1", {
      graphName: "CustomerGraph",
      sampleSize: 50,
      maxSamplesPerCollection: 2,
      verifySystem: false
    });

    expect(discovery.graphProfile).toMatchObject({
      graphProfileId: "graph-profile-1",
      graphName: "CustomerGraph"
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/connection-profiles/connection-1/discover-graph",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          graph_name: "CustomerGraph",
          sample_size: 50,
          max_samples_per_collection: 2,
          verify_system: false
        })
      })
    );

    vi.unstubAllGlobals();
  });

  it("starts Requirements Copilot sessions from graph profiles", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        requirement_interview_id: "interview-1",
        workspace_id: "workspace-1",
        graph_profile_id: "graph-profile-1",
        status: "draft",
        domain: "Clinical trials",
        questions: [
          {
            id: "business_goal",
            text: "What business decision should CustomerGraph support?"
          }
        ],
        schema_observations: {
          graph_name: "CustomerGraph"
        }
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const interview = await createProductAPIClient(
      "http://api.example"
    ).startRequirementsCopilot("graph-profile-1", {
      domain: "Clinical trials",
      createdBy: "analyst@example.com"
    });

    expect(interview).toMatchObject({
      requirementInterviewId: "interview-1",
      graphProfileId: "graph-profile-1",
      domain: "Clinical trials"
    });
    expect(interview.questions[0]).toMatchObject({ id: "business_goal" });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/graph-profiles/graph-profile-1/requirements-copilot/sessions",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          domain: "Clinical trials",
          created_by: "analyst@example.com"
        })
      })
    );

    vi.unstubAllGlobals();
  });

  it("answers Requirements Copilot questions through the product API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        requirement_interview_id: "interview-1",
        workspace_id: "workspace-1",
        graph_profile_id: "graph-profile-1",
        status: "draft",
        answers: [
          {
            question_id: "business_goal",
            answer: "Prioritize trial sites"
          }
        ]
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const interview = await createProductAPIClient(
      "http://api.example"
    ).answerRequirementsCopilotQuestion(
      "interview-1",
      "business_goal",
      "Prioritize trial sites",
      "analyst@example.com"
    );

    expect(interview.answers[0]).toMatchObject({
      question_id: "business_goal",
      answer: "Prioritize trial sites"
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/requirements-copilot/sessions/interview-1/answer",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          question_id: "business_goal",
          answer: "Prioritize trial sites",
          actor: "analyst@example.com"
        })
      })
    );

    vi.unstubAllGlobals();
  });

  it("generates Requirements Copilot drafts through the product API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        requirement_interview: {
          requirement_interview_id: "interview-1",
          workspace_id: "workspace-1",
          graph_profile_id: "graph-profile-1",
          status: "ready_for_review",
          draft_brd: "# Draft"
        },
        draft_brd: "# Draft",
        provenance_labels: [{ path: "answers", label: "user_provided" }]
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const draft = await createProductAPIClient(
      "http://api.example"
    ).generateRequirementsCopilotDraft("interview-1");

    expect(draft.requirementInterview.status).toBe("ready_for_review");
    expect(draft.draftBrd).toBe("# Draft");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/requirements-copilot/sessions/interview-1/generate-draft",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({})
      })
    );

    vi.unstubAllGlobals();
  });

  it("approves Requirements Copilot drafts through the product API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        requirement_version_id: "requirement-version-1",
        workspace_id: "workspace-1",
        requirement_interview_id: "interview-1",
        version: 3,
        status: "approved",
        summary: "Prioritize trial sites",
        objectives: [{ id: "OBJ-1", text: "Prioritize trial sites" }]
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const requirementVersion = await createProductAPIClient(
      "http://api.example"
    ).approveRequirementsCopilotDraft("interview-1", 3, "analyst@example.com");

    expect(requirementVersion).toMatchObject({
      requirementVersionId: "requirement-version-1",
      version: 3,
      status: "approved",
      summary: "Prioritize trial sites"
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/requirements-copilot/sessions/interview-1/approve",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          version: 3,
          approved_by: "analyst@example.com"
        })
      })
    );

    vi.unstubAllGlobals();
  });

  it("exports workspace bundles through the product API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        schema_version: "1",
        workspace: {
          workspace_id: "workspace-1",
          project_name: "Graph Analytics"
        },
        connection_profiles: [{ connection_profile_id: "connection-1" }],
        graph_profiles: [],
        source_documents: [],
        requirement_interviews: [],
        requirement_versions: [],
        workflow_runs: [],
        reports: [],
        audit_events: []
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const bundle = await createProductAPIClient("http://api.example").exportWorkspaceBundle(
      "workspace-1"
    );

    expect(bundle).toMatchObject({
      schemaVersion: "1",
      workspace: { workspace_id: "workspace-1" },
      connectionProfiles: [{ connection_profile_id: "connection-1" }]
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/workspaces/workspace-1/export",
      expect.objectContaining({ method: "GET" })
    );

    vi.unstubAllGlobals();
  });

  it("imports workspace bundles through the product API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        workspace_id: "workspace-1",
        counts: {
          connection_profiles: 1,
          reports: 2
        }
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await createProductAPIClient("http://api.example").importWorkspaceBundle({
      schemaVersion: "1",
      workspace: { workspace_id: "workspace-1" },
      connectionProfiles: [{ connection_profile_id: "connection-1" }],
      graphProfiles: [],
      sourceDocuments: [],
      requirementInterviews: [],
      requirementVersions: [],
      workflowRuns: [],
      reports: [],
      auditEvents: []
    });

    expect(result).toEqual({
      workspaceId: "workspace-1",
      counts: {
        connection_profiles: 1,
        reports: 2
      }
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/workspaces/import",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          schema_version: "1",
          workspace: { workspace_id: "workspace-1" },
          connection_profiles: [{ connection_profile_id: "connection-1" }],
          graph_profiles: [],
          source_documents: [],
          requirement_interviews: [],
          requirement_versions: [],
          workflow_runs: [],
          reports: [],
          audit_events: []
        })
      })
    );

    vi.unstubAllGlobals();
  });

  it("loads workflow recovery actions through the product API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        "step-1": ["retry", "open_logs"],
        "step-2": []
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const actions = await createProductAPIClient(
      "http://api.example"
    ).getWorkflowRecoveryActions("run-1");

    expect(actions["step-1"]).toEqual(["retry", "open_logs"]);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/runs/run-1/recovery-actions",
      expect.objectContaining({ method: "GET" })
    );

    vi.unstubAllGlobals();
  });

  it("starts workflow runs through the product API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        run_id: "run-1",
        workspace_id: "workspace-1",
        workflow_mode: "agentic",
        status: "running",
        started_at: "2026-01-01T00:00:00Z"
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const workflowRun = await createProductAPIClient("http://api.example").startWorkflowRun(
      "run-1"
    );

    expect(workflowRun).toMatchObject({
      runId: "run-1",
      workflowMode: "agentic",
      status: "running"
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/runs/run-1/start",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({})
      })
    );

    vi.unstubAllGlobals();
  });

  it("updates workflow steps through the product API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        workflow_run: {
          run_id: "run-1",
          workspace_id: "workspace-1",
          workflow_mode: "agentic",
          status: "running"
        },
        dag_view: {
          run_id: "run-1",
          workspace_id: "workspace-1",
          status: "running",
          workflow_mode: "agentic",
          nodes: [
            {
              id: "step-1",
              label: "Retry",
              status: "running",
              artifact_count: 0,
              warning_count: 0,
              error_count: 0
            }
          ],
          edges: [],
          warnings: [],
          errors: []
        }
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await createProductAPIClient("http://api.example").updateWorkflowStep(
      "run-1",
      "step-1",
      "running"
    );

    expect(result.dagView.nodes[0].status).toBe("running");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/runs/run-1/steps/step-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ status: "running" })
      })
    );

    vi.unstubAllGlobals();
  });

  it("creates workflow runs from planned steps through the product API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        run_id: "run-1",
        workspace_id: "workspace-1",
        workflow_mode: "agentic",
        status: "queued",
        steps: [
          {
            step_id: "schema-discovery",
            label: "Schema Discovery",
            status: "pending"
          },
          {
            step_id: "agent-analysis",
            label: "Agent Analysis",
            status: "pending"
          }
        ],
        dag_edges: [
          {
            from_step_id: "schema-discovery",
            to_step_id: "agent-analysis"
          }
        ]
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await createProductAPIClient("http://api.example").createWorkflowRun(
      "workspace-1",
      {
        workflowMode: "agentic",
        stepLabels: ["Schema Discovery", "Agent Analysis"]
      }
    );

    expect(result.workflowRun.status).toBe("queued");
    expect(result.dagView.nodes.map((node) => node.id)).toEqual([
      "schema-discovery",
      "agent-analysis"
    ]);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/runs",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          workspace_id: "workspace-1",
          workflow_mode: "agentic",
          steps: [
            {
              step_id: "schema-discovery",
              label: "Schema Discovery",
              status: "pending"
            },
            {
              step_id: "agent-analysis",
              label: "Agent Analysis",
              status: "pending"
            }
          ],
          dag_edges: [
            {
              from_step_id: "schema-discovery",
              to_step_id: "agent-analysis"
            }
          ]
        })
      })
    );

    vi.unstubAllGlobals();
  });
});
