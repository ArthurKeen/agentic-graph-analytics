import type {
  ProductAPIClient,
  RawWorkflowDAGView,
  RawWorkspaceHealth,
  RawWorkspaceOverview,
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
    async getWorkflowDAG(runId: string): Promise<WorkflowDAGView> {
      return mapWorkflowDAGView(
        await getJSON<RawWorkflowDAGView>(
          `${normalizedBaseUrl}/api/runs/${runId}/workflow-dag`
        )
      );
    }
  };
}

export async function getJSON<T>(url: string): Promise<T> {
  const response = await fetch(url, {
    headers: {
      Accept: "application/json"
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
    latestWorkflowRuns: raw.latest_workflow_runs,
    latestReports: raw.latest_reports,
    latestAuditEvents: raw.latest_audit_events ?? []
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

export function workspaceAssetsFromOverview(overview: WorkspaceOverview): WorkspaceAsset[] {
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

  return [...runAssets, ...reportAssets];
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
