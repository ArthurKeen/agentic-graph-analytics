import type {
  ConnectionProfileSummary,
  GraphProfileSummary,
  ReportBundle,
  SourceDocumentSummary,
  WorkflowDAGView,
  WorkspaceAsset
} from "./types";

export const demoAssets: WorkspaceAsset[] = [
  {
    id: "connection-demo",
    kind: "connection-profile",
    label: "Demo ArangoDB",
    description: "local connection (unknown)"
  },
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
    id: "document-demo",
    kind: "document",
    label: "requirements.md",
    description: "text/markdown"
  },
  {
    id: "report-demo",
    kind: "report",
    label: "Dynamic Graph Analytics Report",
    description: "Structured report bundle"
  }
];

export const demoConnectionProfile: ConnectionProfileSummary = {
  connectionProfileId: "connection-demo",
  workspaceId: "workspace-demo",
  name: "Demo ArangoDB",
  deploymentMode: "local",
  endpoint: "http://localhost:8529",
  database: "customer_graph",
  username: "root",
  verifySsl: false,
  secretRefs: { password: { kind: "env", ref: "ARANGO_PASSWORD" } },
  lastVerificationStatus: "unknown",
  lastVerifiedAt: null,
  metadata: { source: "demo" }
};

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

export const demoSourceDocument: SourceDocumentSummary = {
  documentId: "document-demo",
  workspaceId: "workspace-demo",
  filename: "requirements.md",
  mimeType: "text/markdown",
  sha256: "demo-sha256",
  storageMode: "inline_text",
  storageUri: null,
  extractedText:
    "Analyze the customer graph for entity risk, workflow status, and report-ready findings.",
  uploadedAt: "2026-01-01T00:00:00Z",
  metadata: {
    source: "demo",
    vertical: "example"
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
