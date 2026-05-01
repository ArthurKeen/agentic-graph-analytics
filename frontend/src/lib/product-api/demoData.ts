import type {
  GraphProfileSummary,
  ReportBundle,
  WorkflowDAGView,
  WorkspaceAsset
} from "./types";

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
  },
  {
    id: "report-demo",
    kind: "report",
    label: "Dynamic Graph Analytics Report",
    description: "Structured report bundle"
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

export const demoGraphProfile: GraphProfileSummary = {
  graphProfileId: "graph-profile-demo",
  workspaceId: "workspace-demo",
  connectionProfileId: "connection-demo",
  graphName: "Customer Graph Profile",
  status: "discovered",
  version: 1,
  vertexCollections: ["accounts", "devices", "transactions"],
  edgeCollections: ["uses_device", "sent_transaction"],
  edgeDefinitions: [
    {
      edge_collection: "uses_device",
      from_vertex_collections: ["accounts"],
      to_vertex_collections: ["devices"]
    },
    {
      edge_collection: "sent_transaction",
      from_vertex_collections: ["accounts"],
      to_vertex_collections: ["transactions"]
    }
  ],
  collectionRoles: {
    accounts: ["entity"],
    devices: ["entity"],
    transactions: ["event"]
  },
  counts: {
    accounts: 1250,
    devices: 780,
    transactions: 6240
  }
};

export const demoReport: ReportBundle = {
  manifest: {
    reportId: "report-demo",
    workspaceId: "workspace-demo",
    runId: "run-demo",
    title: "Dynamic Graph Analytics Report",
    status: "draft",
    summary: "A workspace-rendered report assembled from structured product metadata.",
    version: 1
  },
  sections: [
    {
      sectionId: "summary",
      order: 1,
      type: "summary",
      title: "Executive Summary",
      content: {
        text: "This report is rendered from a structured report bundle rather than a static file."
      },
      evidenceRefs: []
    },
    {
      sectionId: "recommendation",
      order: 2,
      type: "recommendation",
      title: "Recommended Next Step",
      content: {
        text: "Connect a workspaceId to load live report bundles from the product API."
      },
      evidenceRefs: []
    }
  ],
  charts: [
    {
      chartId: "status-counts",
      title: "Workflow Status Counts",
      chartType: "table",
      dataSource: { kind: "demo" },
      data: {
        rows: [
          { status: "completed", count: 2 },
          { status: "running", count: 1 },
          { status: "pending", count: 1 }
        ]
      },
      encoding: {}
    }
  ],
  snapshots: []
};
