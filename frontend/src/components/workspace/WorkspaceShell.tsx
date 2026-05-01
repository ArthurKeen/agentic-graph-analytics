"use client";

import { useEffect, useMemo, useState } from "react";
import { AssetExplorer } from "./AssetExplorer";
import { ContextMenu } from "./ContextMenu";
import { DeleteRunConfirmationOverlay } from "./DeleteRunConfirmationOverlay";
import { PublishReportConfirmationOverlay } from "./PublishReportConfirmationOverlay";
import { WorkspaceCanvas } from "./WorkspaceCanvas";
import { useWorkspaceData } from "./useWorkspaceData";
import type { ContextMenuState } from "./contextMenus/types";
import type { WorkflowDAGNode, WorkspaceAsset } from "@/lib/product-api/types";

interface WorkspaceShellProps {
  initialWorkspaceId?: string;
  initialRunId?: string;
}

export function WorkspaceShell({ initialWorkspaceId, initialRunId }: WorkspaceShellProps) {
  const { assets, dagByRunId, reportById, health, status, errorMessage } = useWorkspaceData({
    initialWorkspaceId,
    initialRunId
  });
  const [selectedAsset, setSelectedAsset] = useState<WorkspaceAsset | null>(null);
  const [selectedStep, setSelectedStep] = useState<WorkflowDAGNode | null>(null);
  const [menu, setMenu] = useState<ContextMenuState | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const [pendingDeleteRun, setPendingDeleteRun] = useState<WorkspaceAsset | null>(null);
  const [pendingPublishReport, setPendingPublishReport] = useState<WorkspaceAsset | null>(null);
  const [deletedRunIds, setDeletedRunIds] = useState<Set<string>>(() => new Set());
  const [publishedReportIds, setPublishedReportIds] = useState<Set<string>>(() => new Set());
  const visibleAssets = useMemo(
    () =>
      assets
        .filter((asset) => asset.kind !== "run" || !deletedRunIds.has(asset.id))
        .map((asset) =>
          asset.kind === "report" && publishedReportIds.has(asset.id)
            ? { ...asset, description: "Report (published)" }
            : asset
        ),
    [assets, deletedRunIds, publishedReportIds]
  );

  useEffect(() => {
    if (selectedAsset && visibleAssets.some((asset) => asset.id === selectedAsset.id)) {
      return;
    }

    const initialAsset =
      visibleAssets.find((asset) => asset.id === initialRunId) ??
      visibleAssets.find((asset) => asset.kind === "run") ??
      visibleAssets[0] ??
      null;
    setSelectedAsset(initialAsset);
    setSelectedStep(null);
  }, [initialRunId, selectedAsset, visibleAssets]);

  const dagView = useMemo(
    () => (selectedAsset?.kind === "run" ? dagByRunId[selectedAsset.id] ?? null : null),
    [dagByRunId, selectedAsset]
  );
  const reportBundle = useMemo(
    () => (selectedAsset?.kind === "report" ? reportById[selectedAsset.id] ?? null : null),
    [reportById, selectedAsset]
  );

  useEffect(() => {
    function closePanels(event: KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }
      setMenu(null);
      setShowHelp(false);
      setSelectedStep(null);
      setPendingDeleteRun(null);
      setPendingPublishReport(null);
    }

    window.addEventListener("keydown", closePanels);
    return () => window.removeEventListener("keydown", closePanels);
  }, []);

  return (
    <div className="workspace-shell" onClick={() => setMenu(null)}>
      <AssetExplorer
        assets={visibleAssets}
        health={health}
        onSelectAsset={(asset) => {
          setSelectedAsset(asset);
          setSelectedStep(null);
        }}
        onOpenRun={(runId) => {
          const run = visibleAssets.find((asset) => asset.id === runId);
          if (run) {
            setSelectedAsset(run);
            setSelectedStep(null);
          }
        }}
        onOpenReport={(reportId) => {
          const report = visibleAssets.find((asset) => asset.id === reportId);
          if (report) {
            setSelectedAsset(report);
            setSelectedStep(null);
          }
        }}
        onRequestPublishReport={(asset) => setPendingPublishReport(asset)}
        onRequestDeleteRun={(asset) => setPendingDeleteRun(asset)}
        onOpenMenu={setMenu}
      />
      <WorkspaceCanvas
        selectedAsset={selectedAsset}
        selectedStep={selectedStep}
        dagView={dagView}
        reportBundle={reportBundle}
        dataStatus={status}
        dataErrorMessage={errorMessage}
        showHelp={showHelp}
        onSelectStep={setSelectedStep}
        onClearAssetSelection={() => {
          setSelectedAsset(null);
          setSelectedStep(null);
        }}
        onClearSelection={() => setSelectedStep(null)}
        onShowHelp={() => setShowHelp(true)}
        onCloseHelp={() => setShowHelp(false)}
        onOpenMenu={setMenu}
      />
      <ContextMenu menu={menu} onClose={() => setMenu(null)} />
      {pendingDeleteRun ? (
        <DeleteRunConfirmationOverlay
          run={pendingDeleteRun}
          onCancel={() => setPendingDeleteRun(null)}
          onConfirm={() => {
            setDeletedRunIds((current) => new Set([...current, pendingDeleteRun.id]));
            if (selectedAsset?.id === pendingDeleteRun.id) {
              setSelectedAsset(null);
              setSelectedStep(null);
            }
            setPendingDeleteRun(null);
          }}
        />
      ) : null}
      {pendingPublishReport ? (
        <PublishReportConfirmationOverlay
          report={pendingPublishReport}
          onCancel={() => setPendingPublishReport(null)}
          onConfirm={() => {
            setPublishedReportIds(
              (current) => new Set([...current, pendingPublishReport.id])
            );
            setSelectedAsset({
              ...pendingPublishReport,
              description: "Report (published)"
            });
            setPendingPublishReport(null);
          }}
        />
      ) : null}
    </div>
  );
}
