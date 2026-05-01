"use client";

import { useEffect, useMemo, useState } from "react";
import { AssetExplorer } from "./AssetExplorer";
import { ContextMenu } from "./ContextMenu";
import { CreateConnectionProfileOverlay } from "./CreateConnectionProfileOverlay";
import { CreateWorkflowRunOverlay } from "./CreateWorkflowRunOverlay";
import { DeleteRunConfirmationOverlay } from "./DeleteRunConfirmationOverlay";
import { DiscoverGraphProfileOverlay } from "./DiscoverGraphProfileOverlay";
import { FloatingDetailPanel } from "./FloatingDetailPanel";
import { ImportWorkspaceBundleOverlay } from "./ImportWorkspaceBundleOverlay";
import { PublishReportConfirmationOverlay } from "./PublishReportConfirmationOverlay";
import { StartRequirementsCopilotOverlay } from "./StartRequirementsCopilotOverlay";
import { WorkspaceCanvas } from "./WorkspaceCanvas";
import { useWorkspaceData } from "./useWorkspaceData";
import type { ContextMenuState } from "./contextMenus/types";
import type {
  ConnectionVerificationResult,
  RequirementInterview,
  RequirementVersion,
  WorkflowDAGNode,
  WorkspaceAsset
} from "@/lib/product-api/types";

interface WorkspaceShellProps {
  initialWorkspaceId?: string;
  initialRunId?: string;
}

export function WorkspaceShell({ initialWorkspaceId, initialRunId }: WorkspaceShellProps) {
  const {
    assets,
    connectionProfileById,
    graphProfileById,
    documentById,
    dagByRunId,
    recoveryActionsByRunId,
    reportById,
    health,
    status,
    errorMessage,
    createConnectionProfile,
    discoverGraphProfile,
    startRequirementsCopilot,
    answerRequirementsCopilotQuestion,
    generateRequirementsCopilotDraft,
    approveRequirementsCopilotDraft,
    verifyConnectionProfile,
    publishReport,
    exportWorkspaceBundle,
    importWorkspaceBundle,
    createWorkflowRun,
    startWorkflowRun,
    updateWorkflowStep
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
  const [pendingDiscoverGraph, setPendingDiscoverGraph] = useState<WorkspaceAsset | null>(null);
  const [pendingStartCopilot, setPendingStartCopilot] = useState<WorkspaceAsset | null>(null);
  const [showCreateConnectionProfile, setShowCreateConnectionProfile] = useState(false);
  const [showCreateWorkflowRun, setShowCreateWorkflowRun] = useState(false);
  const [createConnectionErrorMessage, setCreateConnectionErrorMessage] = useState<string | null>(
    null
  );
  const [createWorkflowRunErrorMessage, setCreateWorkflowRunErrorMessage] = useState<
    string | null
  >(null);
  const [isCreatingConnectionProfile, setIsCreatingConnectionProfile] = useState(false);
  const [isCreatingWorkflowRun, setIsCreatingWorkflowRun] = useState(false);
  const [verifyingConnectionProfileId, setVerifyingConnectionProfileId] = useState<string | null>(
    null
  );
  const [connectionVerificationById, setConnectionVerificationById] = useState<
    Record<string, ConnectionVerificationResult>
  >({});
  const [connectionVerificationErrorMessage, setConnectionVerificationErrorMessage] = useState<
    string | null
  >(null);
  const [discoverGraphErrorMessage, setDiscoverGraphErrorMessage] = useState<string | null>(null);
  const [discoveringGraphConnectionProfileId, setDiscoveringGraphConnectionProfileId] = useState<
    string | null
  >(null);
  const [startingCopilotGraphProfileId, setStartingCopilotGraphProfileId] = useState<string | null>(
    null
  );
  const [startCopilotErrorMessage, setStartCopilotErrorMessage] = useState<string | null>(null);
  const [requirementsCopilotErrorMessage, setRequirementsCopilotErrorMessage] = useState<
    string | null
  >(null);
  const [isSavingCopilotAnswer, setIsSavingCopilotAnswer] = useState(false);
  const [isGeneratingRequirementsDraft, setIsGeneratingRequirementsDraft] = useState(false);
  const [isApprovingRequirementsDraft, setIsApprovingRequirementsDraft] = useState(false);
  const [activeRequirementInterview, setActiveRequirementInterview] =
    useState<RequirementInterview | null>(null);
  const [approvedRequirementVersion, setApprovedRequirementVersion] =
    useState<RequirementVersion | null>(null);
  const [publishErrorMessage, setPublishErrorMessage] = useState<string | null>(null);
  const [publishingReportId, setPublishingReportId] = useState<string | null>(null);
  const [startingRunId, setStartingRunId] = useState<string | null>(null);
  const [updatingStepId, setUpdatingStepId] = useState<string | null>(null);
  const [runActionMessage, setRunActionMessage] = useState<string | null>(null);
  const [runActionErrorMessage, setRunActionErrorMessage] = useState<string | null>(null);
  const [exportMessage, setExportMessage] = useState<string | null>(null);
  const [exportErrorMessage, setExportErrorMessage] = useState<string | null>(null);
  const [showImportWorkspaceBundle, setShowImportWorkspaceBundle] = useState(false);
  const [isImportingWorkspaceBundle, setIsImportingWorkspaceBundle] = useState(false);
  const [importWorkspaceErrorMessage, setImportWorkspaceErrorMessage] = useState<string | null>(
    null
  );
  const [importWorkspaceMessage, setImportWorkspaceMessage] = useState<string | null>(null);
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
  const selectedStepRecoveryActions = useMemo(() => {
    if (!selectedStep || selectedAsset?.kind !== "run") {
      return [];
    }
    return recoveryActionsByRunId[selectedAsset.id]?.[selectedStep.id] ?? [];
  }, [recoveryActionsByRunId, selectedAsset, selectedStep]);
  const reportBundle = useMemo(
    () => (selectedAsset?.kind === "report" ? reportById[selectedAsset.id] ?? null : null),
    [reportById, selectedAsset]
  );
  const connectionProfile = useMemo(
    () =>
      selectedAsset?.kind === "connection-profile"
        ? connectionProfileById[selectedAsset.id] ?? null
        : null,
    [connectionProfileById, selectedAsset]
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
      setPendingDiscoverGraph(null);
      setPendingStartCopilot(null);
      setShowCreateConnectionProfile(false);
      setShowCreateWorkflowRun(false);
      setCreateConnectionErrorMessage(null);
      setCreateWorkflowRunErrorMessage(null);
      setConnectionVerificationErrorMessage(null);
      setDiscoverGraphErrorMessage(null);
      setStartCopilotErrorMessage(null);
      setRequirementsCopilotErrorMessage(null);
      setPublishErrorMessage(null);
      setRunActionMessage(null);
      setRunActionErrorMessage(null);
      setExportMessage(null);
      setExportErrorMessage(null);
      setShowImportWorkspaceBundle(false);
      setImportWorkspaceErrorMessage(null);
      setImportWorkspaceMessage(null);
    }

    window.addEventListener("keydown", closePanels);
    return () => window.removeEventListener("keydown", closePanels);
  }, []);

  function verifySelectedConnectionProfile(connectionProfileId: string) {
    setConnectionVerificationErrorMessage(null);
    setVerifyingConnectionProfileId(connectionProfileId);
    void verifyConnectionProfile(connectionProfileId)
      .then((result) =>
        setConnectionVerificationById((current) => ({
          ...current,
          [connectionProfileId]: result
        }))
      )
      .catch((error) =>
        setConnectionVerificationErrorMessage(
          error instanceof Error ? error.message : "Failed to verify connection profile"
        )
      )
      .finally(() => setVerifyingConnectionProfileId(null));
  }

  return (
    <div className="workspace-shell" onClick={() => setMenu(null)}>
      <AssetExplorer
        assets={visibleAssets}
        health={health}
        onSelectAsset={(asset) => {
          setSelectedAsset(asset);
          setSelectedStep(null);
        }}
        onOpenConnectionProfile={(connectionProfileId) => {
          const connectionAsset = visibleAssets.find((asset) => asset.id === connectionProfileId);
          if (connectionAsset) {
            setSelectedAsset(connectionAsset);
            setSelectedStep(null);
          }
        }}
        onVerifyConnectionProfile={(connectionProfileId) => {
          const connectionAsset = visibleAssets.find((asset) => asset.id === connectionProfileId);
          if (connectionAsset) {
            setSelectedAsset(connectionAsset);
            setSelectedStep(null);
          }
          verifySelectedConnectionProfile(connectionProfileId);
        }}
        onRequestDiscoverGraph={(asset) => {
          setDiscoverGraphErrorMessage(null);
          setPendingDiscoverGraph(asset);
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
        onRequestStartRequirementsCopilot={(asset) => {
          setStartCopilotErrorMessage(null);
          setPendingStartCopilot(asset);
        }}
        onOpenRun={(runId) => {
          const run = visibleAssets.find((asset) => asset.id === runId);
          if (run) {
            setSelectedAsset(run);
            setSelectedStep(null);
          }
        }}
        onStartRun={(asset) => {
          setRunActionMessage(null);
          setRunActionErrorMessage(null);
          setStartingRunId(asset.id);
          void startWorkflowRun(asset.id)
            .then((workflowRun) => {
              setSelectedAsset({
                ...asset,
                description: `${workflowRun.workflowMode} workflow (${workflowRun.status})`
              });
              setRunActionMessage(`Started run ${workflowRun.runId}.`);
            })
            .catch((error) =>
              setRunActionErrorMessage(
                error instanceof Error ? error.message : "Failed to start workflow run"
              )
            )
            .finally(() => setStartingRunId(null));
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
        connectionProfile={connectionProfile}
        connectionVerificationResult={
          selectedAsset?.kind === "connection-profile"
            ? connectionVerificationById[selectedAsset.id] ?? null
            : null
        }
        dagView={dagView}
        selectedStepRecoveryActions={selectedStepRecoveryActions}
        graphProfile={graphProfile}
        sourceDocument={sourceDocument}
        reportBundle={reportBundle}
        dataStatus={status}
        dataErrorMessage={errorMessage}
        isVerifyingConnection={
          selectedAsset?.kind === "connection-profile" &&
          verifyingConnectionProfileId === selectedAsset.id
        }
        isDiscoveringGraph={
          selectedAsset?.kind === "connection-profile" &&
          discoveringGraphConnectionProfileId === selectedAsset.id
        }
        isStartingRequirementsCopilot={
          selectedAsset?.kind === "graph-profile" &&
          startingCopilotGraphProfileId === selectedAsset.id
        }
        isSavingCopilotAnswer={isSavingCopilotAnswer}
        isGeneratingRequirementsDraft={isGeneratingRequirementsDraft}
        isApprovingRequirementsDraft={isApprovingRequirementsDraft}
        connectionVerificationErrorMessage={connectionVerificationErrorMessage}
        requirementsCopilotErrorMessage={requirementsCopilotErrorMessage}
        activeRequirementInterview={activeRequirementInterview}
        approvedRequirementVersion={approvedRequirementVersion}
        showHelp={showHelp}
        onSelectStep={setSelectedStep}
        onRetryWorkflowStep={(step) => {
          if (selectedAsset?.kind !== "run") {
            return;
          }
          setRunActionMessage(null);
          setRunActionErrorMessage(null);
          setUpdatingStepId(step.id);
          void updateWorkflowStep(selectedAsset.id, step.id, "running")
            .then((result) => {
              setSelectedStep(
                result.dagView.nodes.find((node) => node.id === step.id) ?? null
              );
              setSelectedAsset({
                ...selectedAsset,
                description: `${result.workflowRun.workflowMode} workflow (${result.workflowRun.status})`
              });
              setRunActionMessage(`Retried step ${step.label}.`);
            })
            .catch((error) =>
              setRunActionErrorMessage(
                error instanceof Error ? error.message : "Failed to retry workflow step"
              )
            )
            .finally(() => setUpdatingStepId(null));
        }}
        onClearAssetSelection={() => {
          setSelectedAsset(null);
          setSelectedStep(null);
        }}
        onClearSelection={() => setSelectedStep(null)}
        onRequestCreateConnectionProfile={() => {
          setCreateConnectionErrorMessage(null);
          setShowCreateConnectionProfile(true);
        }}
        onRequestCreateWorkflowRun={() => {
          setCreateWorkflowRunErrorMessage(null);
          setShowCreateWorkflowRun(true);
        }}
        onExportWorkspace={() => {
          setExportMessage(null);
          setExportErrorMessage(null);
          void exportWorkspaceBundle()
            .then((bundle) => {
              const workspaceId = String(
                bundle.workspace.workspace_id ?? bundle.workspace._key ?? "workspace"
              );
              const filename = `${workspaceId}-aga-workspace-bundle.json`;
              downloadJSON(filename, bundle);
              setExportMessage(`Exported ${filename}`);
            })
            .catch((error) =>
              setExportErrorMessage(
                error instanceof Error ? error.message : "Failed to export workspace bundle"
              )
            );
        }}
        onRequestImportWorkspace={() => {
          setImportWorkspaceErrorMessage(null);
          setImportWorkspaceMessage(null);
          setShowImportWorkspaceBundle(true);
        }}
        onVerifyConnectionProfile={verifySelectedConnectionProfile}
        onRequestDiscoverGraph={(connectionProfileId) => {
          const connectionAsset = visibleAssets.find((asset) => asset.id === connectionProfileId);
          if (connectionAsset) {
            setDiscoverGraphErrorMessage(null);
            setPendingDiscoverGraph(connectionAsset);
          }
        }}
        onRequestStartRequirementsCopilot={(graphProfileId) => {
          const graphProfileAsset = visibleAssets.find((asset) => asset.id === graphProfileId);
          if (graphProfileAsset) {
            setStartCopilotErrorMessage(null);
            setPendingStartCopilot(graphProfileAsset);
          }
        }}
        onAnswerRequirementsCopilotQuestion={async (
          requirementInterviewId,
          questionId,
          answer
        ) => {
          setRequirementsCopilotErrorMessage(null);
          setIsSavingCopilotAnswer(true);
          try {
            const interview = await answerRequirementsCopilotQuestion(
              requirementInterviewId,
              questionId,
              answer
            );
            setActiveRequirementInterview(interview);
          } catch (error) {
            setRequirementsCopilotErrorMessage(
              error instanceof Error ? error.message : "Failed to save Copilot answer"
            );
          } finally {
            setIsSavingCopilotAnswer(false);
          }
        }}
        onGenerateRequirementsDraft={async (requirementInterviewId) => {
          setRequirementsCopilotErrorMessage(null);
          setIsGeneratingRequirementsDraft(true);
          try {
            const result = await generateRequirementsCopilotDraft(requirementInterviewId);
            setActiveRequirementInterview(result.requirementInterview);
          } catch (error) {
            setRequirementsCopilotErrorMessage(
              error instanceof Error ? error.message : "Failed to generate requirements draft"
            );
          } finally {
            setIsGeneratingRequirementsDraft(false);
          }
        }}
        onApproveRequirementsDraft={async (requirementInterviewId, version) => {
          setRequirementsCopilotErrorMessage(null);
          setIsApprovingRequirementsDraft(true);
          try {
            const requirementVersion = await approveRequirementsCopilotDraft(
              requirementInterviewId,
              version
            );
            setApprovedRequirementVersion(requirementVersion);
            setActiveRequirementInterview((current) =>
              current?.requirementInterviewId === requirementInterviewId
                ? { ...current, status: "approved" }
                : current
            );
          } catch (error) {
            setRequirementsCopilotErrorMessage(
              error instanceof Error ? error.message : "Failed to approve requirements draft"
            );
          } finally {
            setIsApprovingRequirementsDraft(false);
          }
        }}
        onCloseRequirementsCopilot={() => setActiveRequirementInterview(null)}
        onShowHelp={() => setShowHelp(true)}
        onCloseHelp={() => setShowHelp(false)}
        onOpenMenu={setMenu}
      />
      <ContextMenu menu={menu} onClose={() => setMenu(null)} />
      {showCreateWorkflowRun ? (
        <CreateWorkflowRunOverlay
          isCreating={isCreatingWorkflowRun}
          errorMessage={createWorkflowRunErrorMessage}
          onCancel={() => setShowCreateWorkflowRun(false)}
          onSubmit={async (input) => {
            setCreateWorkflowRunErrorMessage(null);
            setIsCreatingWorkflowRun(true);
            try {
              const result = await createWorkflowRun(input);
              setSelectedAsset({
                id: result.workflowRun.runId,
                kind: "run",
                label: `Run ${result.workflowRun.runId}`,
                description: `${result.workflowRun.workflowMode} workflow (${result.workflowRun.status})`
              });
              setSelectedStep(null);
              setShowCreateWorkflowRun(false);
            } catch (error) {
              setCreateWorkflowRunErrorMessage(
                error instanceof Error ? error.message : "Failed to create workflow run"
              );
            } finally {
              setIsCreatingWorkflowRun(false);
            }
          }}
        />
      ) : null}
      {runActionMessage || runActionErrorMessage || startingRunId || updatingStepId ? (
        <FloatingDetailPanel
          title="Workflow Run"
          stackIndex={2}
          onClose={() => {
            setRunActionMessage(null);
            setRunActionErrorMessage(null);
          }}
        >
          {startingRunId ? <p className="muted">Starting run {startingRunId}...</p> : null}
          {updatingStepId ? <p className="muted">Updating step {updatingStepId}...</p> : null}
          {runActionMessage ? <p className="success-text">{runActionMessage}</p> : null}
          {runActionErrorMessage ? <p className="error-text">{runActionErrorMessage}</p> : null}
        </FloatingDetailPanel>
      ) : null}
      {exportMessage || exportErrorMessage ? (
        <FloatingExportStatusPanel
          message={exportMessage}
          errorMessage={exportErrorMessage}
          onClose={() => {
            setExportMessage(null);
            setExportErrorMessage(null);
          }}
        />
      ) : null}
      {importWorkspaceMessage ? (
        <FloatingDetailPanel
          title="Workspace Import"
          stackIndex={2}
          onClose={() => setImportWorkspaceMessage(null)}
        >
          <p className="success-text">{importWorkspaceMessage}</p>
        </FloatingDetailPanel>
      ) : null}
      {showImportWorkspaceBundle ? (
        <ImportWorkspaceBundleOverlay
          isImporting={isImportingWorkspaceBundle}
          errorMessage={importWorkspaceErrorMessage}
          onCancel={() => setShowImportWorkspaceBundle(false)}
          onSubmit={async (bundle) => {
            setImportWorkspaceErrorMessage(null);
            setIsImportingWorkspaceBundle(true);
            try {
              const result = await importWorkspaceBundle(bundle);
              const importedTotal = Object.values(result.counts).reduce(
                (sum, count) => sum + count,
                0
              );
              setImportWorkspaceMessage(
                `Imported workspace ${result.workspaceId} (${importedTotal} records).`
              );
              setShowImportWorkspaceBundle(false);
            } catch (error) {
              setImportWorkspaceErrorMessage(
                error instanceof Error ? error.message : "Failed to import workspace bundle"
              );
            } finally {
              setIsImportingWorkspaceBundle(false);
            }
          }}
        />
      ) : null}
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
      {pendingDiscoverGraph ? (
        <DiscoverGraphProfileOverlay
          connectionProfile={pendingDiscoverGraph}
          isDiscovering={discoveringGraphConnectionProfileId === pendingDiscoverGraph.id}
          errorMessage={discoverGraphErrorMessage}
          onCancel={() => setPendingDiscoverGraph(null)}
          onSubmit={async (input) => {
            setDiscoverGraphErrorMessage(null);
            setDiscoveringGraphConnectionProfileId(pendingDiscoverGraph.id);
            try {
              const discovery = await discoverGraphProfile(pendingDiscoverGraph.id, input);
              setSelectedAsset({
                id: discovery.graphProfile.graphProfileId,
                kind: "graph-profile",
                label: discovery.graphProfile.graphName,
                description: `Graph profile (${discovery.graphProfile.status})`
              });
              setSelectedStep(null);
              setPendingDiscoverGraph(null);
            } catch (error) {
              setDiscoverGraphErrorMessage(
                error instanceof Error ? error.message : "Failed to discover graph profile"
              );
            } finally {
              setDiscoveringGraphConnectionProfileId(null);
            }
          }}
        />
      ) : null}
      {pendingStartCopilot ? (
        <StartRequirementsCopilotOverlay
          graphProfile={pendingStartCopilot}
          isStarting={startingCopilotGraphProfileId === pendingStartCopilot.id}
          errorMessage={startCopilotErrorMessage}
          onCancel={() => setPendingStartCopilot(null)}
          onSubmit={async (input) => {
            setStartCopilotErrorMessage(null);
            setStartingCopilotGraphProfileId(pendingStartCopilot.id);
            try {
              const interview = await startRequirementsCopilot(pendingStartCopilot.id, input);
              setActiveRequirementInterview(interview);
              setApprovedRequirementVersion(null);
              setSelectedAsset(pendingStartCopilot);
              setSelectedStep(null);
              setPendingStartCopilot(null);
            } catch (error) {
              setStartCopilotErrorMessage(
                error instanceof Error
                  ? error.message
                  : "Failed to start Requirements Copilot"
              );
            } finally {
              setStartingCopilotGraphProfileId(null);
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

function FloatingExportStatusPanel({
  message,
  errorMessage,
  onClose
}: {
  message: string | null;
  errorMessage: string | null;
  onClose: () => void;
}) {
  return (
    <FloatingDetailPanel title="Workspace Export" stackIndex={2} onClose={onClose}>
      {message ? <p className="success-text">{message}</p> : null}
      {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
      <p className="muted">
        Exports include product metadata only. Runtime secrets remain referenced, not resolved.
      </p>
    </FloatingDetailPanel>
  );
}

function downloadJSON(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json"
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
