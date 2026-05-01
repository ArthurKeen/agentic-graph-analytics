"use client";

import { useEffect, useMemo, useState } from "react";
import { AssetExplorer } from "./AssetExplorer";
import { ContextMenu } from "./ContextMenu";
import { CreateConnectionProfileOverlay } from "./CreateConnectionProfileOverlay";
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
  const {
    assets,
    graphProfileById,
    documentById,
    dagByRunId,
    reportById,
    health,
    status,
    errorMessage,
    createConnectionProfile,
    publishReport
  } = useWorkspaceData({
    initialWorkspaceId,
    initialRunId
  });
  const [selectedAsset, setSelectedAsset] = useState<WorkspaceAsset | null>(null);
  const [selectedStep, setSelectedStep] = useState<WorkflowDAGNode | null>(null);
  const [menu, setMenu] = useState<ContextMenuState | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const [pendingDeleteRun, setPendingDeleteRun] = useState<WorkspaceAsset | null>(null);
  const [pendingPublishReport, setPendingPublishReport] = useState<WorkspaceAsset | null>(null);
  const [showCreateConnectionProfile, setShowCreateConnectionProfile] = useState(false);
  const [createConnectionErrorMessage, setCreateConnectionErrorMessage] = useState<string | null>(
    null
  );
  const [isCreatingConnectionProfile, setIsCreatingConnectionProfile] = useState(false);
  const [publishErrorMessage, setPublishErrorMessage] = useState<string | null>(null);
  const [publishingReportId, setPublishingReportId] = useState<string | null>(null);
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
  const graphProfile = useMemo(
    () =>
      selectedAsset?.kind === "graph-profile"
        ? graphProfileById[selectedAsset.id] ?? null
        : null,
    [graphProfileById, selectedAsset]
  );
  const sourceDocument = useMemo(
    () =>
      selectedAsset?.kind === "document"
        ? documentById[selectedAsset.id] ?? null
        : null,
    [documentById, selectedAsset]
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
      setShowCreateConnectionProfile(false);
      setCreateConnectionErrorMessage(null);
      setPublishErrorMessage(null);
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
        onOpenDocument={(documentId) => {
          const documentAsset = visibleAssets.find((asset) => asset.id === documentId);
          if (documentAsset) {
            setSelectedAsset(documentAsset);
            setSelectedStep(null);
          }
        }}
        onOpenGraphProfile={(graphProfileId) => {
          const graphProfileAsset = visibleAssets.find((asset) => asset.id === graphProfileId);
          if (graphProfileAsset) {
            setSelectedAsset(graphProfileAsset);
            setSelectedStep(null);
          }
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
        graphProfile={graphProfile}
        sourceDocument={sourceDocument}
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
        onRequestCreateConnectionProfile={() => {
          setCreateConnectionErrorMessage(null);
          setShowCreateConnectionProfile(true);
        }}
        onShowHelp={() => setShowHelp(true)}
        onCloseHelp={() => setShowHelp(false)}
        onOpenMenu={setMenu}
      />
      <ContextMenu menu={menu} onClose={() => setMenu(null)} />
      {showCreateConnectionProfile ? (
        <CreateConnectionProfileOverlay
          isCreating={isCreatingConnectionProfile}
          errorMessage={createConnectionErrorMessage}
          onCancel={() => setShowCreateConnectionProfile(false)}
          onSubmit={async (input) => {
            setCreateConnectionErrorMessage(null);
            setIsCreatingConnectionProfile(true);
            try {
              const profile = await createConnectionProfile(input);
              setSelectedAsset({
                id: profile.connectionProfileId,
                kind: "connection-profile",
                label: profile.name,
                description: `${profile.deploymentMode} connection (${profile.lastVerificationStatus})`
              });
              setSelectedStep(null);
              setShowCreateConnectionProfile(false);
            } catch (error) {
              setCreateConnectionErrorMessage(
                error instanceof Error ? error.message : "Failed to create connection profile"
              );
            } finally {
              setIsCreatingConnectionProfile(false);
            }
          }}
        />
      ) : null}
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
          isPublishing={publishingReportId === pendingPublishReport.id}
          errorMessage={publishErrorMessage}
          onCancel={() => setPendingPublishReport(null)}
          onConfirm={async () => {
            setPublishErrorMessage(null);
            setPublishingReportId(pendingPublishReport.id);
            try {
              const publishedReport = await publishReport(pendingPublishReport.id);
              setPublishedReportIds(
                (current) => new Set([...current, publishedReport.manifest.reportId])
              );
              setSelectedAsset({
                ...pendingPublishReport,
                description: `Report (${publishedReport.manifest.status})`
              });
              setPendingPublishReport(null);
            } catch (error) {
              setPublishErrorMessage(
                error instanceof Error ? error.message : "Failed to publish report"
              );
            } finally {
              setPublishingReportId(null);
            }
          }}
        />
      ) : null}
    </div>
  );
}
