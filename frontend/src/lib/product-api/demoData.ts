import type { WorkflowDAGView, WorkspaceAsset } from "./types";

export const demoAssets: WorkspaceAsset[] = [
  {
    id: "run-demo",
    kind: "run",
    label: "Requirements to Report Run",
    description: "Agentic workflow execution"
  },
  {
    id: "graph-profile-demo",
    kind: "graph-profile",
    label: "Customer Graph Profile",
    description: "Discovered graph schema"
  }
];

export const demoDag: WorkflowDAGView = {
  runId: "run-demo",
  workspaceId: "workspace-demo",
  status: "running",
  workflowMode: "agentic",
  nodes: [
    {
      id: "requirements",
      label: "Requirements",
      status: "completed",
      artifactCount: 1,
      warningCount: 0,
      errorCount: 0
    },
    {
      id: "schema",
      label: "Schema Discovery",
      status: "completed",
      artifactCount: 2,
      warningCount: 0,
      errorCount: 0
    },
    {
      id: "analysis",
      label: "Agent Analysis",
      status: "running",
      artifactCount: 0,
      warningCount: 1,
      errorCount: 0
    },
    {
      id: "report",
      label: "Dynamic Report",
      status: "pending",
      artifactCount: 0,
      warningCount: 0,
      errorCount: 0
    }
  ],
  edges: [
    { id: "requirements-schema", from: "requirements", to: "schema" },
    { id: "schema-analysis", from: "schema", to: "analysis" },
    { id: "analysis-report", from: "analysis", to: "report" }
  ],
  warnings: [],
  errors: []
};
