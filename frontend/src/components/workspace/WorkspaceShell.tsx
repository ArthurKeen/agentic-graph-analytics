"use client";

import { useMemo, useState } from "react";
import { AssetExplorer } from "./AssetExplorer";
import { ContextMenu } from "./ContextMenu";
import { WorkspaceCanvas } from "./WorkspaceCanvas";
import type { ContextMenuState } from "./contextMenus/types";
import type { WorkflowDAGNode, WorkflowDAGView, WorkspaceAsset } from "@/lib/product-api/types";

const demoAssets: WorkspaceAsset[] = [
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

const demoDag: WorkflowDAGView = {
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

export function WorkspaceShell() {
  const [selectedAsset, setSelectedAsset] = useState<WorkspaceAsset | null>(demoAssets[0]);
  const [selectedStep, setSelectedStep] = useState<WorkflowDAGNode | null>(null);
  const [menu, setMenu] = useState<ContextMenuState | null>(null);
  const dagView = useMemo(
    () => (selectedAsset?.kind === "run" ? demoDag : null),
    [selectedAsset]
  );

  return (
    <div className="workspace-shell" onClick={() => setMenu(null)}>
      <AssetExplorer
        assets={demoAssets}
        onSelectAsset={(asset) => {
          setSelectedAsset(asset);
          setSelectedStep(null);
        }}
        onOpenRun={(runId) => {
          const run = demoAssets.find((asset) => asset.id === runId);
          if (run) {
            setSelectedAsset(run);
            setSelectedStep(null);
          }
        }}
        onOpenMenu={setMenu}
      />
      <WorkspaceCanvas
        selectedAsset={selectedAsset}
        selectedStep={selectedStep}
        dagView={dagView}
        onSelectStep={setSelectedStep}
        onClearSelection={() => setSelectedStep(null)}
        onOpenMenu={setMenu}
      />
      <ContextMenu menu={menu} onClose={() => setMenu(null)} />
    </div>
  );
}
