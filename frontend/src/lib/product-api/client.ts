import type {
  ChartSpec,
  ConnectionGraphSummary,
  ConnectionGraphsResult,
  ConnectionProfileSummary,
  ConnectionVerificationResult,
  CreateConnectionProfileInput,
  CreateWorkspaceInput,
  CreateWorkflowRunInput,
  CreateWorkflowRunResult,
  DiscoverGraphProfileInput,
  GraphDiscoveryResult,
  GraphProfileSummary,
  ProductAPIClient,
  RawConnectionGraphSummary,
  RawConnectionGraphsResult,
  RawConnectionProfileSummary,
  RawConnectionVerificationResult,
  RawGraphDiscoveryResult,
  RawGraphProfileSummary,
  RawRequirementInterview,
  RawRequirementVersion,
  RawRequirementsDraftResult,
  RawReportBundle,
  RawSourceDocumentSummary,
  RawWorkflowDAGView,
  RawWorkflowRunSummary,
  RawWorkflowStepUpdateResult,
  RawWorkspaceBundle,
  RawWorkspaceHealth,
  RawWorkspaceImportResult,
  RawWorkspaceOverview,
  RawWorkspaceSummary,
  ReportBundle,
  ReportSection,
  RequirementInterview,
  RequirementVersion,
  RequirementsDraftResult,
  SourceDocumentSummary,
  StartRequirementsCopilotInput,
  WorkflowDAGEdge,
  WorkflowDAGNode,
  WorkflowDAGView,
  WorkflowRecoveryActions,
  WorkflowRunSummary,
  WorkflowStepStatus,
  WorkflowStepUpdateResult,
  WorkspaceAsset,
  WorkspaceBundle,
  WorkspaceHealth,
  WorkspaceImportResult,
  WorkspaceOverview,
  WorkspaceSummary
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export function createProductAPIClient(
  baseUrl = process.env.NEXT_PUBLIC_PRODUCT_API_BASE_URL ?? DEFAULT_API_BASE_URL
): ProductAPIClient {
  const normalizedBaseUrl = baseUrl.replace(/\/$/, "");

  return {
    async createWorkspace(input: CreateWorkspaceInput): Promise<WorkspaceSummary> {
      return mapWorkspaceSummary(
        await postJSON<RawWorkspaceSummary>(
          `${normalizedBaseUrl}/api/workspaces`,
          createWorkspacePayload(input)
        )
      );
    },
    async listWorkspaces(): Promise<WorkspaceSummary[]> {
      const raw = await getJSON<RawWorkspaceSummary[]>(
        `${normalizedBaseUrl}/api/workspaces`
      );
      return Array.isArray(raw) ? raw.map(mapWorkspaceSummary) : [];
    },
    async getWorkspaceOverview(workspaceId: string): Promise<WorkspaceOverview> {
      return mapWorkspaceOverview(
        await getJSON<RawWorkspaceOverview>(
          `${normalizedBaseUrl}/api/workspaces/${workspaceId}/overview`
        )
      );
    },
    async getWorkspaceHealth(workspaceId: string): Promise<WorkspaceHealth> {
      return mapWorkspaceHealth(
        await getJSON<RawWorkspaceHealth>(
          `${normalizedBaseUrl}/api/workspaces/${workspaceId}/health`
        )
      );
    },
    async createConnectionProfile(
      workspaceId: string,
      input: CreateConnectionProfileInput
    ): Promise<ConnectionProfileSummary> {
      return mapConnectionProfileSummary(
        await postJSON<RawConnectionProfileSummary>(
          `${normalizedBaseUrl}/api/workspaces/${workspaceId}/connection-profiles`,
          createConnectionProfilePayload(input)
        )
      );
    },
    async verifyConnectionProfile(
      connectionProfileId: string
    ): Promise<ConnectionVerificationResult> {
      return mapConnectionVerificationResult(
        await postJSON<RawConnectionVerificationResult>(
          `${normalizedBaseUrl}/api/connection-profiles/${connectionProfileId}/verify`,
          {}
        )
      );
    },
    async listConnectionProfileGraphs(
      connectionProfileId: string
    ): Promise<ConnectionGraphsResult> {
      return mapConnectionGraphsResult(
        await getJSON<RawConnectionGraphsResult>(
          `${normalizedBaseUrl}/api/connection-profiles/${connectionProfileId}/graphs`
        )
      );
    },
    async discoverGraphProfile(
      connectionProfileId: string,
      input: DiscoverGraphProfileInput
    ): Promise<GraphDiscoveryResult> {
      return mapGraphDiscoveryResult(
        await postJSON<RawGraphDiscoveryResult>(
          `${normalizedBaseUrl}/api/connection-profiles/${connectionProfileId}/discover-graph`,
          discoverGraphProfilePayload(input)
        )
      );
    },
    async startRequirementsCopilot(
      graphProfileId: string,
      input: StartRequirementsCopilotInput
    ): Promise<RequirementInterview> {
      return mapRequirementInterview(
        await postJSON<RawRequirementInterview>(
          `${normalizedBaseUrl}/api/graph-profiles/${graphProfileId}/requirements-copilot/sessions`,
          startRequirementsCopilotPayload(input)
        )
      );
    },
    async answerRequirementsCopilotQuestion(
      requirementInterviewId: string,
      questionId: string,
      answer: string,
      actor = "workspace-ui"
    ): Promise<RequirementInterview> {
      return mapRequirementInterview(
        await postJSON<RawRequirementInterview>(
          `${normalizedBaseUrl}/api/requirements-copilot/sessions/${requirementInterviewId}/answer`,
          {
            question_id: questionId,
            answer,
            actor
          }
        )
      );
    },
    async generateRequirementsCopilotDraft(
      requirementInterviewId: string
    ): Promise<RequirementsDraftResult> {
      return mapRequirementsDraftResult(
        await postJSON<RawRequirementsDraftResult>(
          `${normalizedBaseUrl}/api/requirements-copilot/sessions/${requirementInterviewId}/generate-draft`,
          {}
        )
      );
    },
    async approveRequirementsCopilotDraft(
      requirementInterviewId: string,
      version: number | null,
      approvedBy = "workspace-ui"
    ): Promise<RequirementVersion> {
      // Pass `version` only when explicitly provided so the backend can
      // auto-increment to max(existing.version)+1.
      const body: Record<string, unknown> = { approved_by: approvedBy };
      if (version !== null && version !== undefined) {
        body.version = version;
      }
      return mapRequirementVersion(
        await postJSON<RawRequirementVersion>(
          `${normalizedBaseUrl}/api/requirements-copilot/sessions/${requirementInterviewId}/approve`,
          body
        )
      );
    },
    async getWorkflowDAG(runId: string): Promise<WorkflowDAGView> {
      return mapWorkflowDAGView(
        await getJSON<RawWorkflowDAGView>(
          `${normalizedBaseUrl}/api/runs/${runId}/workflow-dag`
        )
      );
    },
    async getReportBundle(reportId: string): Promise<ReportBundle> {
      return mapReportBundle(
        await getJSON<RawReportBundle>(
          `${normalizedBaseUrl}/api/reports/${reportId}`
        )
      );
    },
    async publishReport(reportId: string, actor: string): Promise<ReportBundle> {
      return mapReportBundle(
        await postJSON<RawReportBundle>(
          `${normalizedBaseUrl}/api/reports/${reportId}/publish`,
          { actor }
        )
      );
    },
    async exportWorkspaceBundle(workspaceId: string): Promise<WorkspaceBundle> {
      return mapWorkspaceBundle(
        await getJSON<RawWorkspaceBundle>(
          `${normalizedBaseUrl}/api/workspaces/${workspaceId}/export`
        )
      );
    },
    async importWorkspaceBundle(bundle: WorkspaceBundle): Promise<WorkspaceImportResult> {
      return mapWorkspaceImportResult(
        await postJSON<RawWorkspaceImportResult>(
          `${normalizedBaseUrl}/api/workspaces/import`,
          workspaceBundlePayload(bundle)
        )
      );
    },
    async getWorkflowRecoveryActions(runId: string): Promise<WorkflowRecoveryActions> {
      return getJSON<WorkflowRecoveryActions>(
        `${normalizedBaseUrl}/api/runs/${runId}/recovery-actions`
      );
    },
    async createWorkflowRun(
      workspaceId: string,
      input: CreateWorkflowRunInput
    ): Promise<CreateWorkflowRunResult> {
      const workflowRun = await postJSON<RawWorkflowRunSummary>(
        `${normalizedBaseUrl}/api/runs`,
        createWorkflowRunPayload(workspaceId, input)
      );
      return {
        workflowRun: mapWorkflowRunSummary(workflowRun),
        dagView: mapWorkflowRunToDAGView(workflowRun)
      };
    },
    async startWorkflowRun(runId: string): Promise<WorkflowRunSummary> {
      return mapWorkflowRunSummary(
        await postJSON<RawWorkflowRunSummary>(
          `${normalizedBaseUrl}/api/runs/${runId}/start`,
          {}
        )
      );
    },
    async updateWorkflowStep(
      runId: string,
      stepId: string,
      status: WorkflowStepStatus
    ): Promise<WorkflowStepUpdateResult> {
      return mapWorkflowStepUpdateResult(
        await patchJSON<RawWorkflowStepUpdateResult>(
          `${normalizedBaseUrl}/api/runs/${runId}/steps/${stepId}`,
          { status }
        )
      );
    }
  };
}

export async function getJSON<T>(url: string): Promise<T> {
  return requestJSON<T>(url, { method: "GET" });
}

export async function postJSON<T>(url: string, body: Record<string, unknown>): Promise<T> {
  return requestJSON<T>(url, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function patchJSON<T>(url: string, body: Record<string, unknown>): Promise<T> {
  return requestJSON<T>(url, {
    method: "PATCH",
    body: JSON.stringify(body)
  });
}

async function requestJSON<T>(url: string, init: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...init.headers
    }
  });

  if (!response.ok) {
    throw new Error(`Product API request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export function mapWorkspaceOverview(raw: RawWorkspaceOverview): WorkspaceOverview {
  return {
    workspace: raw.workspace,
    counts: raw.counts,
    latestConnectionProfiles: (raw.latest_connection_profiles ?? []).map(
      mapConnectionProfileSummary
    ),
    latestGraphProfiles: (raw.latest_graph_profiles ?? []).map(mapGraphProfileSummary),
    latestSourceDocuments: (raw.latest_source_documents ?? []).map(mapSourceDocumentSummary),
    latestRequirementVersions: (raw.latest_requirement_versions ?? []).map(
      mapRequirementVersion
    ),
    latestWorkflowRuns: raw.latest_workflow_runs,
    latestReports: raw.latest_reports,
    latestAuditEvents: raw.latest_audit_events ?? []
  };
}

export function mapWorkspaceSummary(raw: RawWorkspaceSummary): WorkspaceSummary {
  return {
    workspaceId: raw.workspace_id,
    customerName: raw.customer_name,
    projectName: raw.project_name,
    environment: raw.environment,
    description: raw.description ?? "",
    status: raw.status ?? "active",
    tags: raw.tags ?? []
  };
}

export function mapGraphDiscoveryResult(raw: RawGraphDiscoveryResult): GraphDiscoveryResult {
  return {
    graphProfile: mapGraphProfileSummary(raw.graph_profile),
    schemaSummary: raw.schema_summary
  };
}

export function mapConnectionGraphSummary(
  raw: RawConnectionGraphSummary
): ConnectionGraphSummary {
  return {
    name: raw.name,
    isSystem: raw.is_system ?? raw.name.startsWith("_"),
    vertexCollections: raw.vertex_collections ?? [],
    edgeCollections: raw.edge_collections ?? [],
    orphanCollections: raw.orphan_collections ?? [],
    edgeDefinitions: raw.edge_definitions ?? [],
    vertexCount: raw.vertex_count ?? null,
    edgeCount: raw.edge_count ?? null
  };
}

export function mapConnectionGraphsResult(
  raw: RawConnectionGraphsResult
): ConnectionGraphsResult {
  return {
    connectionProfileId: raw.connection_profile_id,
    workspaceId: raw.workspace_id,
    database: raw.database,
    graphs: (raw.graphs ?? []).map(mapConnectionGraphSummary)
  };
}

export function mapRequirementInterview(raw: RawRequirementInterview): RequirementInterview {
  return {
    requirementInterviewId: raw.requirement_interview_id,
    workspaceId: raw.workspace_id,
    graphProfileId: raw.graph_profile_id,
    status: raw.status,
    domain: raw.domain,
    questions: raw.questions ?? [],
    answers: raw.answers ?? [],
    schemaObservations: raw.schema_observations ?? {},
    inferences: raw.inferences ?? [],
    assumptions: raw.assumptions ?? [],
    draftBrd: raw.draft_brd,
    provenanceLabels: raw.provenance_labels ?? [],
    metadata: raw.metadata ?? {}
  };
}

export function mapRequirementsDraftResult(
  raw: RawRequirementsDraftResult
): RequirementsDraftResult {
  return {
    requirementInterview: mapRequirementInterview(raw.requirement_interview),
    draftBrd: raw.draft_brd,
    provenanceLabels: raw.provenance_labels ?? []
  };
}

export function mapRequirementVersion(raw: RawRequirementVersion): RequirementVersion {
  return {
    requirementVersionId: raw.requirement_version_id,
    workspaceId: raw.workspace_id,
    version: raw.version,
    status: raw.status,
    requirementInterviewId: raw.requirement_interview_id,
    summary: raw.summary ?? "",
    objectives: raw.objectives ?? [],
    requirements: raw.requirements ?? [],
    constraints: raw.constraints ?? [],
    approvedAt: raw.approved_at,
    metadata: raw.metadata ?? {}
  };
}

export function mapConnectionVerificationResult(
  raw: RawConnectionVerificationResult
): ConnectionVerificationResult {
  return {
    connectionProfileId: raw.connection_profile_id,
    workspaceId: raw.workspace_id,
    status: raw.status,
    verifiedAt: raw.verified_at,
    endpoint: raw.endpoint,
    database: raw.database,
    errorMessage: raw.error_message
  };
}

export function mapConnectionProfileSummary(
  raw: RawConnectionProfileSummary
): ConnectionProfileSummary {
  return {
    connectionProfileId: raw.connection_profile_id,
    workspaceId: raw.workspace_id,
    name: raw.name,
    deploymentMode: raw.deployment_mode,
    endpoint: raw.endpoint,
    database: raw.database,
    username: raw.username,
    verifySsl: raw.verify_ssl ?? true,
    secretRefs: raw.secret_refs ?? {},
    lastVerificationStatus: raw.last_verification_status ?? "unknown",
    lastVerifiedAt: raw.last_verified_at,
    metadata: raw.metadata ?? {}
  };
}

export function mapGraphProfileSummary(raw: RawGraphProfileSummary): GraphProfileSummary {
  return {
    graphProfileId: raw.graph_profile_id,
    workspaceId: raw.workspace_id,
    connectionProfileId: raw.connection_profile_id,
    graphName: raw.graph_name,
    status: raw.status,
    version: raw.version ?? 1,
    vertexCollections: raw.vertex_collections ?? [],
    edgeCollections: raw.edge_collections ?? [],
    edgeDefinitions: raw.edge_definitions ?? [],
    collectionRoles: raw.collection_roles ?? {},
    counts: raw.counts ?? {}
  };
}

export function mapSourceDocumentSummary(raw: RawSourceDocumentSummary): SourceDocumentSummary {
  return {
    documentId: raw.document_id,
    workspaceId: raw.workspace_id,
    filename: raw.filename,
    mimeType: raw.mime_type,
    sha256: raw.sha256 ?? "",
    storageMode: raw.storage_mode ?? "unknown",
    storageUri: raw.storage_uri,
    extractedText: raw.extracted_text,
    uploadedAt: raw.uploaded_at,
    metadata: raw.metadata ?? {}
  };
}

export function mapWorkflowDAGView(raw: RawWorkflowDAGView): WorkflowDAGView {
  return {
    runId: raw.run_id,
    workspaceId: raw.workspace_id,
    status: raw.status,
    workflowMode: raw.workflow_mode,
    nodes: raw.nodes.map(mapWorkflowNode),
    edges: raw.edges.map(mapWorkflowEdge),
    warnings: raw.warnings,
    errors: raw.errors
  };
}

export function mapWorkflowRunSummary(raw: RawWorkflowRunSummary): WorkflowRunSummary {
  return {
    runId: raw.run_id,
    workspaceId: raw.workspace_id,
    workflowMode: raw.workflow_mode,
    status: raw.status,
    startedAt: raw.started_at,
    completedAt: raw.completed_at
  };
}

export function mapWorkflowRunToDAGView(raw: RawWorkflowRunSummary): WorkflowDAGView {
  return {
    runId: raw.run_id,
    workspaceId: raw.workspace_id,
    status: raw.status,
    workflowMode: raw.workflow_mode,
    nodes: (raw.steps ?? []).map((step) => ({
      id: step.step_id,
      label: step.label,
      status: step.status,
      agentName: step.agent_name,
      artifactCount: step.artifact_refs?.length ?? 0,
      warningCount: step.warnings?.length ?? 0,
      errorCount: step.errors?.length ?? 0
    })),
    edges: (raw.dag_edges ?? []).map((edge) => ({
      id: `${edge.from_step_id}-${edge.to_step_id}`,
      from: edge.from_step_id,
      to: edge.to_step_id,
      label: edge.label
    })),
    warnings: raw.warnings ?? [],
    errors: raw.errors ?? []
  };
}

export function mapWorkflowStepUpdateResult(
  raw: RawWorkflowStepUpdateResult
): WorkflowStepUpdateResult {
  return {
    workflowRun: mapWorkflowRunSummary(raw.workflow_run),
    dagView: mapWorkflowDAGView(raw.dag_view)
  };
}

export function mapWorkspaceHealth(raw: RawWorkspaceHealth): WorkspaceHealth {
  return {
    workspaceId: raw.workspace_id,
    status: raw.status,
    counts: raw.counts,
    issues: raw.issues.map((issue) => ({
      severity: issue.severity,
      code: issue.code,
      message: issue.message,
      entityIds: issue.entity_ids ?? []
    }))
  };
}

export function mapReportBundle(raw: RawReportBundle): ReportBundle {
  return {
    manifest: {
      reportId: raw.manifest.report_id,
      workspaceId: raw.manifest.workspace_id,
      runId: raw.manifest.run_id,
      title: raw.manifest.title,
      status: raw.manifest.status,
      summary: raw.manifest.summary ?? "",
      version: raw.manifest.version ?? 1
    },
    sections: raw.sections
      .map(mapReportSection)
      .sort((left, right) => left.order - right.order),
    charts: raw.charts.map(mapChartSpec),
    snapshots: raw.snapshots
  };
}

export function mapWorkspaceBundle(raw: RawWorkspaceBundle): WorkspaceBundle {
  return {
    schemaVersion: raw.schema_version,
    workspace: raw.workspace,
    connectionProfiles: raw.connection_profiles ?? [],
    graphProfiles: raw.graph_profiles ?? [],
    sourceDocuments: raw.source_documents ?? [],
    requirementInterviews: raw.requirement_interviews ?? [],
    requirementVersions: raw.requirement_versions ?? [],
    workflowRuns: raw.workflow_runs ?? [],
    reports: raw.reports ?? [],
    auditEvents: raw.audit_events ?? []
  };
}

export function mapWorkspaceImportResult(
  raw: RawWorkspaceImportResult
): WorkspaceImportResult {
  return {
    workspaceId: raw.workspace_id,
    counts: raw.counts
  };
}

export function workspaceAssetsFromOverview(overview: WorkspaceOverview): WorkspaceAsset[] {
  const connectionProfileAssets = overview.latestConnectionProfiles.map((profile) => ({
    id: profile.connectionProfileId,
    kind: "connection-profile" as const,
    label: profile.name,
    description: `${profile.deploymentMode} connection (${profile.lastVerificationStatus})`
  }));
  const graphProfileAssets = overview.latestGraphProfiles.map((profile) => ({
    id: profile.graphProfileId,
    kind: "graph-profile" as const,
    label: profile.graphName,
    description: `Graph profile (${profile.status})`
  }));
  const documentAssets = overview.latestSourceDocuments.map((document) => ({
    id: document.documentId,
    kind: "document" as const,
    label: document.filename,
    description: document.mimeType
  }));
  // Project ONE consolidated "Requirements" row regardless of how many
  // RequirementVersion records exist (v1, v2,…). The id is synthetic so it
  // stays stable as new versions are approved and prior versions flip to
  // SUPERSEDED. Description shows the active version + history depth so the
  // user gets a one-glance summary without expanding the canvas. When no
  // versions exist yet the row is omitted entirely (caller decides whether
  // to surface a "Start Requirements Copilot" affordance elsewhere).
  const sortedVersions = [...overview.latestRequirementVersions].sort(
    (a, b) => b.version - a.version
  );
  const activeRequirementVersion =
    sortedVersions.find((version) => version.status === "approved") ??
    sortedVersions[0] ??
    null;
  const requirementsAssets: WorkspaceAsset[] = activeRequirementVersion
    ? [
        {
          id: `requirements:${overview.workspace.workspace_id}`,
          kind: "requirements" as const,
          label: "Requirements",
          description:
            sortedVersions.length === 1
              ? `v${activeRequirementVersion.version} (${activeRequirementVersion.status})`
              : `v${activeRequirementVersion.version} (${activeRequirementVersion.status}) · ${
                  sortedVersions.length - 1
                } prior version${sortedVersions.length - 1 === 1 ? "" : "s"}`
        }
      ]
    : [];
  const runAssets = overview.latestWorkflowRuns.map((run) => ({
    id: run.run_id,
    kind: "run" as const,
    label: `Run ${run.run_id}`,
    description: `${run.workflow_mode} workflow (${run.status})`
  }));
  const reportAssets = overview.latestReports.map((report) => ({
    id: report.report_id,
    kind: "report" as const,
    label: report.title,
    description: `Report (${report.status})`
  }));

  return [
    ...connectionProfileAssets,
    ...graphProfileAssets,
    ...requirementsAssets,
    ...documentAssets,
    ...runAssets,
    ...reportAssets
  ];
}

function createConnectionProfilePayload(
  input: CreateConnectionProfileInput
): Record<string, unknown> {
  const passwordSecretEnvVar = input.passwordSecretEnvVar?.trim() ?? "";
  const secretRefs = passwordSecretEnvVar
    ? { password: { kind: "env", ref: passwordSecretEnvVar } }
    : {};

  return {
    name: input.name,
    deployment_mode: input.deploymentMode,
    endpoint: input.endpoint,
    database: input.database,
    username: input.username,
    verify_ssl: input.verifySsl,
    secret_refs: secretRefs
  };
}

function createWorkspacePayload(input: CreateWorkspaceInput): Record<string, unknown> {
  const description = input.description?.trim() ?? "";
  const actor = input.actor?.trim() ?? "";
  return {
    customer_name: input.customerName,
    project_name: input.projectName,
    environment: input.environment,
    ...(description ? { description } : {}),
    tags: input.tags ?? [],
    ...(actor ? { actor } : {})
  };
}

function discoverGraphProfilePayload(input: DiscoverGraphProfileInput): Record<string, unknown> {
  const graphName = input.graphName?.trim() ?? "";
  return {
    ...(graphName ? { graph_name: graphName } : {}),
    sample_size: input.sampleSize,
    max_samples_per_collection: input.maxSamplesPerCollection,
    verify_system: input.verifySystem
  };
}

function startRequirementsCopilotPayload(
  input: StartRequirementsCopilotInput
): Record<string, unknown> {
  const domain = input.domain?.trim() ?? "";
  const createdBy = input.createdBy?.trim() ?? "";
  const basedOnVersionId = input.basedOnVersionId?.trim() ?? "";
  return {
    ...(domain ? { domain } : {}),
    ...(createdBy ? { created_by: createdBy } : {}),
    ...(basedOnVersionId ? { based_on_version_id: basedOnVersionId } : {})
  };
}

function workspaceBundlePayload(bundle: WorkspaceBundle): Record<string, unknown> {
  return {
    schema_version: bundle.schemaVersion,
    workspace: bundle.workspace,
    connection_profiles: bundle.connectionProfiles,
    graph_profiles: bundle.graphProfiles,
    source_documents: bundle.sourceDocuments,
    requirement_interviews: bundle.requirementInterviews,
    requirement_versions: bundle.requirementVersions,
    workflow_runs: bundle.workflowRuns,
    reports: bundle.reports,
    audit_events: bundle.auditEvents
  };
}

function createWorkflowRunPayload(
  workspaceId: string,
  input: CreateWorkflowRunInput
): Record<string, unknown> {
  const steps = input.stepLabels.map((label, index) => ({
    step_id: slugifyStepId(label, index),
    label,
    status: "pending"
  }));
  return {
    workspace_id: workspaceId,
    workflow_mode: input.workflowMode,
    steps,
    dag_edges: steps.slice(1).map((step, index) => ({
      from_step_id: steps[index].step_id,
      to_step_id: step.step_id
    }))
  };
}

function slugifyStepId(label: string, index: number): string {
  const slug = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return slug || `step-${index + 1}`;
}

function mapReportSection(raw: RawReportBundle["sections"][number]): ReportSection {
  return {
    sectionId: raw.section_id,
    order: raw.order,
    type: raw.type,
    title: raw.title,
    content: raw.content ?? {},
    evidenceRefs: raw.evidence_refs ?? []
  };
}

function mapChartSpec(raw: RawReportBundle["charts"][number]): ChartSpec {
  return {
    chartId: raw.chart_id,
    title: raw.title,
    chartType: raw.chart_type,
    dataSource: raw.data_source ?? {},
    data: raw.data ?? {},
    encoding: raw.encoding ?? {}
  };
}

function mapWorkflowNode(raw: RawWorkflowDAGView["nodes"][number]): WorkflowDAGNode {
  return {
    id: raw.id,
    label: raw.label,
    status: raw.status,
    agentName: raw.agent_name,
    artifactCount: raw.artifact_count,
    warningCount: raw.warning_count,
    errorCount: raw.error_count
  };
}

function mapWorkflowEdge(raw: RawWorkflowDAGView["edges"][number]): WorkflowDAGEdge {
  return {
    id: raw.id,
    from: raw.from,
    to: raw.to,
    label: raw.label
  };
}
