"use client";

import { useEffect, useMemo, useState } from "react";
import { AssetExplorer } from "./AssetExplorer";
import { ContextMenu } from "./ContextMenu";
import { WorkspaceCanvas } from "./WorkspaceCanvas";
import { useWorkspaceData } from "./useWorkspaceData";
import type { ContextMenuState } from "./contextMenus/types";
import type { WorkflowDAGNode, WorkspaceAsset } from "@/lib/product-api/types";

interface WorkspaceShellProps {
  initialWorkspaceId?: string;
  initialRunId?: string;
}

export function WorkspaceShell({ initialWorkspaceId, initialRunId }: WorkspaceShellProps) {
  const { assets, dagByRunId, status, errorMessage } = useWorkspaceData({
    initialWorkspaceId,
    initialRunId
  });
  const [selectedAsset, setSelectedAsset] = useState<WorkspaceAsset | null>(null);
  const [selectedStep, setSelectedStep] = useState<WorkflowDAGNode | null>(null);
  const [menu, setMenu] = useState<ContextMenuState | null>(null);

  useEffect(() => {
    if (selectedAsset && assets.some((asset) => asset.id === selectedAsset.id)) {
      return;
    }

    const initialAsset =
      assets.find((asset) => asset.id === initialRunId) ??
      assets.find((asset) => asset.kind === "run") ??
      assets[0] ??
      null;
    setSelectedAsset(initialAsset);
    setSelectedStep(null);
  }, [assets, initialRunId, selectedAsset]);

  const dagView = useMemo(
    () => (selectedAsset?.kind === "run" ? dagByRunId[selectedAsset.id] ?? null : null),
    [dagByRunId, selectedAsset]
  );

  return (
    <div className="workspace-shell" onClick={() => setMenu(null)}>
      <AssetExplorer
        assets={assets}
        onSelectAsset={(asset) => {
          setSelectedAsset(asset);
          setSelectedStep(null);
        }}
        onOpenRun={(runId) => {
          const run = assets.find((asset) => asset.id === runId);
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
        dataStatus={status}
        dataErrorMessage={errorMessage}
        onSelectStep={setSelectedStep}
        onClearSelection={() => setSelectedStep(null)}
        onOpenMenu={setMenu}
      />
      <ContextMenu menu={menu} onClose={() => setMenu(null)} />
    </div>
  );
}
