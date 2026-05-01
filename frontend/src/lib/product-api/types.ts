export type WorkflowStepStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped"
  | "paused";

export type WorkspaceAssetKind =
  | "connection-profile"
  | "document"
  | "graph-profile"
  | "run"
  | "report";

export interface WorkspaceAsset {
  id: string;
  kind: WorkspaceAssetKind;
  label: string;
  description?: string;
}

export interface GraphProfileSummary {
  graphProfileId: string;
  workspaceId: string;
  connectionProfileId: string;
  graphName: string;
  status: string;
  version: number;
  vertexCollections: string[];
  edgeCollections: string[];
  edgeDefinitions: Array<Record<string, unknown>>;
  collectionRoles: Record<string, string[]>;
  counts: Record<string, number>;
}

export interface SourceDocumentSummary {
  documentId: string;
  workspaceId: string;
  filename: string;
  mimeType: string;
  sha256: string;
  storageMode: string;
  storageUri?: string | null;
  extractedText?: string | null;
  uploadedAt?: string;
  metadata: Record<string, unknown>;
}

export interface ConnectionProfileSummary {
  connectionProfileId: string;
  workspaceId: string;
  name: string;
  deploymentMode: string;
  endpoint: string;
  database: string;
  username: string;
  verifySsl: boolean;
  secretRefs: Record<string, Record<string, string>>;
  lastVerificationStatus: string;
  lastVerifiedAt?: string | null;
  metadata: Record<string, unknown>;
}

export interface CreateConnectionProfileInput {
  name: string;
  deploymentMode: string;
  endpoint: string;
  database: string;
  username: string;
  verifySsl: boolean;
  passwordSecretEnvVar?: string;
}

export interface ConnectionVerificationResult {
  connectionProfileId: string;
  workspaceId: string;
  status: string;
  verifiedAt: string;
  endpoint: string;
  database: string;
  errorMessage?: string | null;
}

export interface DiscoverGraphProfileInput {
  graphName?: string;
  sampleSize: number;
  maxSamplesPerCollection: number;
  verifySystem: boolean;
}

export interface GraphDiscoveryResult {
  graphProfile: GraphProfileSummary;
  schemaSummary: Record<string, unknown>;
}

export interface StartRequirementsCopilotInput {
  domain?: string;
  createdBy?: string;
}

export interface RequirementInterview {
  requirementInterviewId: string;
  workspaceId: string;
  graphProfileId: string;
  status: string;
  domain?: string | null;
  questions: Array<Record<string, unknown>>;
  answers: Array<Record<string, unknown>>;
  schemaObservations: Record<string, unknown>;
  inferences: Array<Record<string, unknown>>;
  assumptions: Array<Record<string, unknown>>;
  draftBrd?: string | null;
  provenanceLabels: Array<Record<string, unknown>>;
}

export interface RequirementsDraftResult {
  requirementInterview: RequirementInterview;
  draftBrd: string;
  provenanceLabels: Array<Record<string, unknown>>;
}

export interface RequirementVersion {
  requirementVersionId: string;
  workspaceId: string;
  version: number;
  status: string;
  requirementInterviewId?: string | null;
  summary: string;
  objectives: Array<Record<string, unknown>>;
  requirements: Array<Record<string, unknown>>;
  constraints: Array<Record<string, unknown>>;
  approvedAt?: string | null;
  metadata: Record<string, unknown>;
}

export interface WorkflowDAGNode {
  id: string;
  label: string;
  status: WorkflowStepStatus;
  agentName?: string;
  artifactCount: number;
  warningCount: number;
  errorCount: number;
}

export interface WorkflowDAGEdge {
  id: string;
  from: string;
  to: string;
  label?: string;
}

export interface WorkflowDAGView {
  runId: string;
  workspaceId: string;
  status: string;
  workflowMode: string;
  nodes: WorkflowDAGNode[];
  edges: WorkflowDAGEdge[];
  warnings: string[];
  errors: string[];
}

export type WorkflowRecoveryActions = Record<string, string[]>;

export interface WorkflowRunSummary {
  runId: string;
  workspaceId: string;
  workflowMode: string;
  status: string;
  startedAt?: string | null;
  completedAt?: string | null;
}

export interface WorkspaceOverview {
  workspace: {
    workspace_id: string;
    customer_name: string;
    project_name: string;
    environment: string;
  };
  counts: Record<string, number>;
  latestConnectionProfiles: ConnectionProfileSummary[];
  latestGraphProfiles: GraphProfileSummary[];
  latestSourceDocuments: SourceDocumentSummary[];
  latestWorkflowRuns: Array<{
    run_id: string;
    status: string;
    workflow_mode: string;
  }>;
  latestReports: Array<{
    report_id: string;
    title: string;
    status: string;
  }>;
  latestAuditEvents: Array<Record<string, unknown>>;
}

export interface WorkspaceHealthIssue {
  severity: "info" | "warning" | "error";
  code: string;
  message: string;
  entityIds: string[];
}

export interface WorkspaceHealth {
  workspaceId: string;
  status: "healthy" | "needs_attention" | string;
  counts: Record<string, number>;
  issues: WorkspaceHealthIssue[];
}

export interface ReportManifest {
  reportId: string;
  workspaceId: string;
  runId: string;
  title: string;
  status: string;
  summary: string;
  version: number;
}

export interface ReportSection {
  sectionId: string;
  order: number;
  type: string;
  title: string;
  content: Record<string, unknown>;
  evidenceRefs: Array<Record<string, string>>;
}

export interface ChartSpec {
  chartId: string;
  title: string;
  chartType: string;
  dataSource: Record<string, unknown>;
  data: Record<string, unknown>;
  encoding: Record<string, unknown>;
}

export interface ReportBundle {
  manifest: ReportManifest;
  sections: ReportSection[];
  charts: ChartSpec[];
  snapshots: Array<Record<string, unknown>>;
}

export interface WorkspaceBundle {
  schemaVersion: string;
  workspace: Record<string, unknown>;
  connectionProfiles: Array<Record<string, unknown>>;
  graphProfiles: Array<Record<string, unknown>>;
  sourceDocuments: Array<Record<string, unknown>>;
  requirementInterviews: Array<Record<string, unknown>>;
  requirementVersions: Array<Record<string, unknown>>;
  workflowRuns: Array<Record<string, unknown>>;
  reports: Array<Record<string, unknown>>;
  auditEvents: Array<Record<string, unknown>>;
}

export interface WorkspaceImportResult {
  workspaceId: string;
  counts: Record<string, number>;
}

export interface ProductAPIClient {
  getWorkspaceOverview(workspaceId: string): Promise<WorkspaceOverview>;
  getWorkspaceHealth(workspaceId: string): Promise<WorkspaceHealth>;
  createConnectionProfile(
    workspaceId: string,
    input: CreateConnectionProfileInput
  ): Promise<ConnectionProfileSummary>;
  verifyConnectionProfile(connectionProfileId: string): Promise<ConnectionVerificationResult>;
  discoverGraphProfile(
    connectionProfileId: string,
    input: DiscoverGraphProfileInput
  ): Promise<GraphDiscoveryResult>;
  startRequirementsCopilot(
    graphProfileId: string,
    input: StartRequirementsCopilotInput
  ): Promise<RequirementInterview>;
  answerRequirementsCopilotQuestion(
    requirementInterviewId: string,
    questionId: string,
    answer: string,
    actor?: string
  ): Promise<RequirementInterview>;
  generateRequirementsCopilotDraft(
    requirementInterviewId: string
  ): Promise<RequirementsDraftResult>;
  approveRequirementsCopilotDraft(
    requirementInterviewId: string,
    version: number,
    approvedBy?: string
  ): Promise<RequirementVersion>;
  getWorkflowDAG(runId: string): Promise<WorkflowDAGView>;
  getReportBundle(reportId: string): Promise<ReportBundle>;
  publishReport(reportId: string, actor: string): Promise<ReportBundle>;
  exportWorkspaceBundle(workspaceId: string): Promise<WorkspaceBundle>;
  importWorkspaceBundle(bundle: WorkspaceBundle): Promise<WorkspaceImportResult>;
  getWorkflowRecoveryActions(runId: string): Promise<WorkflowRecoveryActions>;
  startWorkflowRun(runId: string): Promise<WorkflowRunSummary>;
}

export interface RawWorkspaceOverview {
  workspace: WorkspaceOverview["workspace"];
  counts: Record<string, number>;
  latest_connection_profiles?: RawConnectionProfileSummary[];
  latest_graph_profiles?: RawGraphProfileSummary[];
  latest_source_documents?: RawSourceDocumentSummary[];
  latest_workflow_runs: WorkspaceOverview["latestWorkflowRuns"];
  latest_reports: WorkspaceOverview["latestReports"];
  latest_audit_events?: Array<Record<string, unknown>>;
}

export interface RawConnectionProfileSummary {
  connection_profile_id: string;
  workspace_id: string;
  name: string;
  deployment_mode: string;
  endpoint: string;
  database: string;
  username: string;
  verify_ssl?: boolean;
  secret_refs?: Record<string, Record<string, string>>;
  last_verification_status?: string;
  last_verified_at?: string | null;
  metadata?: Record<string, unknown>;
}

export interface RawConnectionVerificationResult {
  connection_profile_id: string;
  workspace_id: string;
  status: string;
  verified_at: string;
  endpoint: string;
  database: string;
  error_message?: string | null;
}

export interface RawGraphDiscoveryResult {
  graph_profile: RawGraphProfileSummary;
  schema_summary: Record<string, unknown>;
}

export interface RawRequirementInterview {
  requirement_interview_id: string;
  workspace_id: string;
  graph_profile_id: string;
  status: string;
  domain?: string | null;
  questions?: Array<Record<string, unknown>>;
  answers?: Array<Record<string, unknown>>;
  schema_observations?: Record<string, unknown>;
  inferences?: Array<Record<string, unknown>>;
  assumptions?: Array<Record<string, unknown>>;
  draft_brd?: string | null;
  provenance_labels?: Array<Record<string, unknown>>;
}

export interface RawRequirementsDraftResult {
  requirement_interview: RawRequirementInterview;
  draft_brd: string;
  provenance_labels?: Array<Record<string, unknown>>;
}

export interface RawRequirementVersion {
  requirement_version_id: string;
  workspace_id: string;
  version: number;
  status: string;
  requirement_interview_id?: string | null;
  summary?: string;
  objectives?: Array<Record<string, unknown>>;
  requirements?: Array<Record<string, unknown>>;
  constraints?: Array<Record<string, unknown>>;
  approved_at?: string | null;
  metadata?: Record<string, unknown>;
}

export interface RawSourceDocumentSummary {
  document_id: string;
  workspace_id: string;
  filename: string;
  mime_type: string;
  sha256?: string;
  storage_mode?: string;
  storage_uri?: string | null;
  extracted_text?: string | null;
  uploaded_at?: string;
  metadata?: Record<string, unknown>;
}

export interface RawGraphProfileSummary {
  graph_profile_id: string;
  workspace_id: string;
  connection_profile_id: string;
  graph_name: string;
  status: string;
  version?: number;
  vertex_collections?: string[];
  edge_collections?: string[];
  edge_definitions?: Array<Record<string, unknown>>;
  collection_roles?: Record<string, string[]>;
  counts?: Record<string, number>;
}

export interface RawWorkflowDAGView {
  run_id: string;
  workspace_id: string;
  status: string;
  workflow_mode: string;
  nodes: Array<{
    id: string;
    label: string;
    status: WorkflowStepStatus;
    agent_name?: string;
    artifact_count: number;
    warning_count: number;
    error_count: number;
  }>;
  edges: Array<{
    id: string;
    from: string;
    to: string;
    label?: string;
  }>;
  warnings: string[];
  errors: string[];
}

export interface RawWorkflowRunSummary {
  run_id: string;
  workspace_id: string;
  workflow_mode: string;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface RawWorkspaceHealth {
  workspace_id: string;
  status: string;
  counts: Record<string, number>;
  issues: Array<{
    severity: "info" | "warning" | "error";
    code: string;
    message: string;
    entity_ids?: string[];
  }>;
}

export interface RawReportBundle {
  manifest: {
    report_id: string;
    workspace_id: string;
    run_id: string;
    title: string;
    status: string;
    summary?: string;
    version?: number;
  };
  sections: Array<{
    section_id: string;
    order: number;
    type: string;
    title: string;
    content?: Record<string, unknown>;
    evidence_refs?: Array<Record<string, string>>;
  }>;
  charts: Array<{
    chart_id: string;
    title: string;
    chart_type: string;
    data_source?: Record<string, unknown>;
    data?: Record<string, unknown>;
    encoding?: Record<string, unknown>;
  }>;
  snapshots: Array<Record<string, unknown>>;
}

export interface RawWorkspaceBundle {
  schema_version: string;
  workspace: Record<string, unknown>;
  connection_profiles?: Array<Record<string, unknown>>;
  graph_profiles?: Array<Record<string, unknown>>;
  source_documents?: Array<Record<string, unknown>>;
  requirement_interviews?: Array<Record<string, unknown>>;
  requirement_versions?: Array<Record<string, unknown>>;
  workflow_runs?: Array<Record<string, unknown>>;
  reports?: Array<Record<string, unknown>>;
  audit_events?: Array<Record<string, unknown>>;
}

export interface RawWorkspaceImportResult {
  workspace_id: string;
  counts: Record<string, number>;
}
