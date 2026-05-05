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
  it("creates workspaces through the product API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        workspace_id: "workspace-1",
        customer_name: "Example",
        project_name: "Graph Analytics",
        environment: "dev",
        description: "Demo workspace",
        status: "active",
        tags: ["demo"]
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const workspace = await createProductAPIClient("http://api.example").createWorkspace({
      customerName: "Example",
      projectName: "Graph Analytics",
      environment: "dev",
      description: "Demo workspace",
      tags: ["demo"],
      actor: "tester"
    });

    expect(workspace).toMatchObject({
      workspaceId: "workspace-1",
      customerName: "Example",
      projectName: "Graph Analytics",
      environment: "dev"
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/workspaces",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          customer_name: "Example",
          project_name: "Graph Analytics",
          environment: "dev",
          description: "Demo workspace",
          tags: ["demo"],
          actor: "tester"
        })
      })
    );

    vi.unstubAllGlobals();
  });

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
      latest_requirement_versions: [
        {
          requirement_version_id: "requirement-version-1",
          workspace_id: "workspace-1",
          version: 1,
          status: "approved",
          summary: "Approved BRD",
          objectives: [],
          requirements: [],
          constraints: []
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
    expect(overview.latestRequirementVersions[0]).toMatchObject({
      requirementVersionId: "requirement-version-1",
      version: 1,
      status: "approved"
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
        id: "requirements:workspace-1",
        kind: "requirements",
        label: "Requirements",
        description: "v1 (approved)"
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

  it("consolidates multiple RequirementVersion records into one Requirements asset", () => {
    // Regression test for the IA refactor: the AssetExplorer should never
    // grow one row per approved/superseded version. Instead, it surfaces a
    // single "Requirements" row whose description names the active version
    // and counts the prior ones; the canvas-side dropdown is responsible for
    // exposing history.
    const overview = mapWorkspaceOverview({
      workspace: { workspace_id: "workspace-2", customer_name: "Acme", project_name: "Households", environment: "prod" },
      counts: {},
      latest_connection_profiles: [],
      latest_graph_profiles: [],
      latest_source_documents: [],
      latest_requirement_versions: [
        {
          requirement_version_id: "requirement-version-2",
          workspace_id: "workspace-2",
          version: 2,
          status: "approved",
          summary: "Refined v2",
          objectives: [],
          requirements: [],
          constraints: []
        },
        {
          requirement_version_id: "requirement-version-1",
          workspace_id: "workspace-2",
          version: 1,
          status: "superseded",
          summary: "Initial",
          objectives: [],
          requirements: [],
          constraints: []
        }
      ],
      latest_workflow_runs: [],
      latest_reports: []
    });

    const assets = workspaceAssetsFromOverview(overview);
    const requirementsAssets = assets.filter((asset) => asset.kind === "requirements");
    expect(requirementsAssets).toHaveLength(1);
    expect(requirementsAssets[0]).toEqual({
      id: "requirements:workspace-2",
      kind: "requirements",
      label: "Requirements",
      description: "v2 (approved) · 1 prior version"
    });
  });

  it("omits the Requirements asset when the workspace has no versions yet", () => {
    const overview = mapWorkspaceOverview({
      workspace: { workspace_id: "workspace-3", customer_name: "Acme", project_name: "Empty", environment: "prod" },
      counts: {},
      latest_connection_profiles: [],
      latest_graph_profiles: [],
      latest_source_documents: [],
      latest_requirement_versions: [],
      latest_workflow_runs: [],
      latest_reports: []
    });

    const assets = workspaceAssetsFromOverview(overview);
    expect(assets.find((asset) => asset.kind === "requirements")).toBeUndefined();
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

  it("exports a report as Markdown via the product API and surfaces filename + blob", async () => {
    // FR-42: the export endpoint returns raw text with a filename in the
    // Content-Disposition header. The client must parse the header so the
    // browser-side download uses the same filename the server picked.
    const markdown = "# Risk Report\n\nFindings.\n";
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: {
        get: (header: string) =>
          header.toLowerCase() === "content-disposition"
            ? 'attachment; filename="risk-report.md"'
            : null
      },
      blob: async () => new Blob([markdown], { type: "text/markdown" }),
      text: async () => markdown,
      statusText: "OK",
      status: 200
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await createProductAPIClient("http://api.example").exportReport(
      "report-1",
      "markdown"
    );

    expect(result.filename).toBe("risk-report.md");
    expect(result.format).toBe("markdown");
    expect(await result.blob.text()).toBe(markdown);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/reports/report-1/export?format=markdown",
      { method: "GET" }
    );

    vi.unstubAllGlobals();
  });

  it("falls back to a deterministic export filename when the server omits Content-Disposition", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => null },
      blob: async () => new Blob(["<html/>"], { type: "text/html" }),
      text: async () => "<html/>",
      statusText: "OK",
      status: 200
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await createProductAPIClient("http://api.example").exportReport(
      "report-7",
      "html"
    );

    expect(result.filename).toBe("report-report-7.html");
    expect(result.format).toBe("html");

    vi.unstubAllGlobals();
  });

  it("PATCHes only the workspace fields the caller actually set", async () => {
    // FR-1 (Edit Workspace): the API client must omit unset fields so the
    // backend can distinguish "patch to empty" from "leave alone". Sending
    // every field every time would push the diff cost onto the backend.
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        workspace_id: "workspace-1",
        customer_name: "Acme Corp",
        project_name: "AdTech",
        environment: "dev",
        description: "Demo",
        status: "active",
        tags: ["adtech", "demo"]
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const updated = await createProductAPIClient(
      "http://api.example"
    ).updateWorkspace("workspace-1", {
      customerName: "Acme Corp",
      tags: ["adtech", "demo"],
      actor: "ops@example.com"
    });

    expect(updated).toMatchObject({
      workspaceId: "workspace-1",
      customerName: "Acme Corp",
      tags: ["adtech", "demo"]
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/workspaces/workspace-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({
          customer_name: "Acme Corp",
          tags: ["adtech", "demo"],
          actor: "ops@example.com"
        })
      })
    );

    vi.unstubAllGlobals();
  });

  it("archives a workspace via the dedicated lifecycle endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        workspace_id: "workspace-1",
        customer_name: "Acme",
        project_name: "AdTech",
        environment: "dev",
        description: "",
        status: "archived",
        tags: []
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const archived = await createProductAPIClient(
      "http://api.example"
    ).archiveWorkspace("workspace-1", "ops@example.com");

    expect(archived.status).toBe("archived");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/workspaces/workspace-1/archive",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ actor: "ops@example.com" })
      })
    );

    vi.unstubAllGlobals();
  });

  it("raises a descriptive error when report export fails", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      headers: { get: () => null },
      text: async () => "Unsupported report export format"
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      createProductAPIClient("http://api.example").exportReport(
        "report-1",
        "markdown"
      )
    ).rejects.toThrow(/Report export failed.*400.*Unsupported/);

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

  it("lists named graphs available on a connection profile", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        connection_profile_id: "connection-1",
        workspace_id: "workspace-1",
        database: "customer_graph",
        graphs: [
          {
            name: "CustomerGraph",
            is_system: false,
            vertex_collections: ["customers"],
            edge_collections: ["transactions"],
            orphan_collections: [],
            edge_definitions: [],
            vertex_count: 100,
            edge_count: 250
          }
        ]
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await createProductAPIClient(
      "http://api.example"
    ).listConnectionProfileGraphs("connection-1");

    expect(result).toMatchObject({
      connectionProfileId: "connection-1",
      database: "customer_graph"
    });
    expect(result.graphs).toHaveLength(1);
    expect(result.graphs[0]).toMatchObject({
      name: "CustomerGraph",
      isSystem: false,
      vertexCount: 100,
      edgeCount: 250
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/connection-profiles/connection-1/graphs",
      expect.objectContaining({ method: "GET" })
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
          approved_by: "analyst@example.com",
          version: 3
        })
      })
    );

    vi.unstubAllGlobals();
  });

  it("omits the version field when null is passed so the backend auto-increments", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        requirement_version_id: "requirement-version-7",
        workspace_id: "workspace-1",
        requirement_interview_id: "interview-1",
        version: 7,
        status: "approved",
        summary: "Auto-incremented"
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    await createProductAPIClient("http://api.example").approveRequirementsCopilotDraft(
      "interview-1",
      null,
      "analyst@example.com"
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/requirements-copilot/sessions/interview-1/approve",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ approved_by: "analyst@example.com" })
      })
    );

    vi.unstubAllGlobals();
  });

  it("forwards based_on_version_id when reopening a Requirements Copilot session", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        requirement_interview_id: "interview-2",
        workspace_id: "workspace-1",
        graph_profile_id: "graph-1",
        status: "draft",
        questions: [],
        answers: []
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    await createProductAPIClient("http://api.example").startRequirementsCopilot(
      "graph-1",
      {
        domain: "AdTech",
        createdBy: "analyst@example.com",
        basedOnVersionId: "requirement-version-1"
      }
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example/api/graph-profiles/graph-1/requirements-copilot/sessions",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          domain: "AdTech",
          created_by: "analyst@example.com",
          based_on_version_id: "requirement-version-1"
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
