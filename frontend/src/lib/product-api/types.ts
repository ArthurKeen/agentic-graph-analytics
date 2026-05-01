export type WorkflowStepStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped"
  | "paused";

export type WorkspaceAssetKind = "document" | "graph-profile" | "run" | "report";

export interface WorkspaceAsset {
  id: string;
  kind: WorkspaceAssetKind;
  label: string;
  description?: string;
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

export interface WorkspaceOverview {
  workspace: {
    workspace_id: string;
    customer_name: string;
    project_name: string;
    environment: string;
  };
  counts: Record<string, number>;
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

export interface ProductAPIClient {
  getWorkspaceOverview(workspaceId: string): Promise<WorkspaceOverview>;
  getWorkspaceHealth(workspaceId: string): Promise<WorkspaceHealth>;
  getWorkflowDAG(runId: string): Promise<WorkflowDAGView>;
  getReportBundle(reportId: string): Promise<ReportBundle>;
  publishReport(reportId: string, actor: string): Promise<ReportBundle>;
}

export interface RawWorkspaceOverview {
  workspace: WorkspaceOverview["workspace"];
  counts: Record<string, number>;
  latest_workflow_runs: WorkspaceOverview["latestWorkflowRuns"];
  latest_reports: WorkspaceOverview["latestReports"];
  latest_audit_events?: Array<Record<string, unknown>>;
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
