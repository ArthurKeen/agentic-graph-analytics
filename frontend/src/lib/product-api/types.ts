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

export interface ProductAPIClient {
  getWorkspaceOverview(workspaceId: string): Promise<WorkspaceOverview>;
  getWorkflowDAG(runId: string): Promise<WorkflowDAGView>;
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
