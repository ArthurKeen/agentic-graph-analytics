import type {
  ChartSpec,
  ConnectionProfileSummary,
  ConnectionVerificationResult,
  CreateConnectionProfileInput,
  DiscoverGraphProfileInput,
  GraphDiscoveryResult,
  GraphProfileSummary,
  ProductAPIClient,
  RawConnectionProfileSummary,
  RawConnectionVerificationResult,
  RawGraphDiscoveryResult,
  RawGraphProfileSummary,
  RawRequirementInterview,
  RawReportBundle,
  RawSourceDocumentSummary,
  RawWorkflowDAGView,
  RawWorkspaceHealth,
  RawWorkspaceOverview,
  ReportBundle,
  ReportSection,
  RequirementInterview,
  SourceDocumentSummary,
  StartRequirementsCopilotInput,
  WorkflowDAGEdge,
  WorkflowDAGNode,
  WorkflowDAGView,
  WorkspaceAsset,
  WorkspaceHealth,
  WorkspaceOverview
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export function createProductAPIClient(
  baseUrl = process.env.NEXT_PUBLIC_PRODUCT_API_BASE_URL ?? DEFAULT_API_BASE_URL
): ProductAPIClient {
  const normalizedBaseUrl = baseUrl.replace(/\/$/, "");

  return {
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
    latestWorkflowRuns: raw.latest_workflow_runs,
    latestReports: raw.latest_reports,
    latestAuditEvents: raw.latest_audit_events ?? []
  };
}

export function mapGraphDiscoveryResult(raw: RawGraphDiscoveryResult): GraphDiscoveryResult {
  return {
    graphProfile: mapGraphProfileSummary(raw.graph_profile),
    schemaSummary: raw.schema_summary
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
    provenanceLabels: raw.provenance_labels ?? []
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
  return {
    ...(domain ? { domain } : {}),
    ...(createdBy ? { created_by: createdBy } : {})
  };
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
