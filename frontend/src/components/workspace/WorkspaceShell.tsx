"use client";

import { useEffect, useMemo, useState } from "react";
import { ArchiveWorkspaceConfirmationOverlay } from "./ArchiveWorkspaceConfirmationOverlay";
import { AssetExplorer } from "./AssetExplorer";
import { ContextMenu } from "./ContextMenu";
import { CreateConnectionProfileOverlay } from "./CreateConnectionProfileOverlay";
import { CreateWorkspaceOverlay } from "./CreateWorkspaceOverlay";
import { CreateWorkflowRunOverlay } from "./CreateWorkflowRunOverlay";
import { DeleteRunConfirmationOverlay } from "./DeleteRunConfirmationOverlay";
import { DiscoverGraphProfileOverlay } from "./DiscoverGraphProfileOverlay";
import { EditWorkspaceOverlay } from "./EditWorkspaceOverlay";
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
  WorkspaceAsset,
  WorkspaceSummary
} from "@/lib/product-api/types";

interface WorkspaceShellProps {
  initialWorkspaceId?: string;
  initialRunId?: string;
  /** Deep-link target: render the Requirements canvas with this specific
   * version selected (read-only history mode if it isn't the active version).
   * Sourced from `?requirementVersion=` in the URL; once the user changes the
   * dropdown the URL is rewritten to match. */
  initialRequirementVersionId?: string;
}

export function WorkspaceShell({
  initialWorkspaceId,
  initialRunId,
  initialRequirementVersionId
}: WorkspaceShellProps) {
  const {
    assets,
    connectionProfileById,
    graphProfileById,
    documentById,
    dagByRunId,
    recoveryActionsByRunId,
    reportById,
    overview,
    health,
    status,
    errorMessage,
    createWorkspace,
    updateWorkspace,
    archiveWorkspace,
    createConnectionProfile,
    listConnectionProfileGraphs,
    discoverGraphProfile,
    startRequirementsCopilot,
    answerRequirementsCopilotQuestion,
    generateRequirementsCopilotDraft,
    approveRequirementsCopilotDraft,
    verifyConnectionProfile,
    publishReport,
    exportReport,
    exportWorkspaceBundle,
    importWorkspaceBundle,
    createWorkflowRun,
    startWorkflowRun,
    updateWorkflowStep,
    requirementVersions,
    approvedRequirementVersion: activeApprovedRequirementVersion,
    refreshOverview
  } = useWorkspaceData({
    initialWorkspaceId,
    initialRunId
  });
  const [selectedAsset, setSelectedAsset] = useState<WorkspaceAsset | null>(null);
  const [selectedStep, setSelectedStep] = useState<WorkflowDAGNode | null>(null);
  // The asset info panel is opt-in (right-click → View Info) so it does not
  // obscure per-canvas action buttons like "Start Requirements Copilot".
  const [isAssetInfoOpen, setIsAssetInfoOpen] = useState(false);
  const [menu, setMenu] = useState<ContextMenuState | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const [pendingDeleteRun, setPendingDeleteRun] = useState<WorkspaceAsset | null>(null);
  const [pendingPublishReport, setPendingPublishReport] = useState<WorkspaceAsset | null>(null);
  const [pendingDiscoverGraph, setPendingDiscoverGraph] = useState<WorkspaceAsset | null>(null);
  const [pendingStartCopilot, setPendingStartCopilot] = useState<WorkspaceAsset | null>(null);
  // When non-null, the start overlay is invoked in "reopen" mode; the
  // basedOnVersion is passed through to the backend so the new interview is
  // pre-populated from this approved RequirementVersion and the prior version
  // gets flipped to SUPERSEDED on approve.
  const [pendingReopenVersion, setPendingReopenVersion] = useState<{
    requirementVersionId: string;
    version: number;
  } | null>(null);
  const [showCreateWorkspace, setShowCreateWorkspace] = useState(false);
  const [showEditWorkspace, setShowEditWorkspace] = useState(false);
  const [showArchiveWorkspace, setShowArchiveWorkspace] = useState(false);
  const [editWorkspaceErrorMessage, setEditWorkspaceErrorMessage] = useState<string | null>(null);
  const [archiveWorkspaceErrorMessage, setArchiveWorkspaceErrorMessage] = useState<string | null>(
    null
  );
  const [isSavingWorkspaceEdit, setIsSavingWorkspaceEdit] = useState(false);
  const [isArchivingWorkspace, setIsArchivingWorkspace] = useState(false);
  const [showCreateConnectionProfile, setShowCreateConnectionProfile] = useState(false);
  const [showCreateWorkflowRun, setShowCreateWorkflowRun] = useState(false);
  const [createConnectionErrorMessage, setCreateConnectionErrorMessage] = useState<string | null>(
    null
  );
  const [createWorkspaceErrorMessage, setCreateWorkspaceErrorMessage] = useState<string | null>(
    null
  );
  const [createWorkflowRunErrorMessage, setCreateWorkflowRunErrorMessage] = useState<
    string | null
  >(null);
  const [isCreatingConnectionProfile, setIsCreatingConnectionProfile] = useState(false);
  const [isCreatingWorkspace, setIsCreatingWorkspace] = useState(false);
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
  const [canvasActionMessage, setCanvasActionMessage] = useState<string | null>(null);
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
  const requirementVersionById = useMemo(
    () =>
      Object.fromEntries(
        requirementVersions.map((version) => [
          version.requirementVersionId,
          version
        ])
      ),
    [requirementVersions]
  );
  // The Assets panel exposes ONE consolidated "Requirements" row per
  // workspace; the canvas owns version selection via a dropdown. `null` means
  // "follow the active version" — newly approved versions auto-advance the
  // view without forcing the user to re-pick. URL deep-links seed this with
  // an explicit id; the URL is rewritten whenever the user picks a different
  // version (see effect below).
  const [selectedRequirementVersionId, setSelectedRequirementVersionId] = useState<
    string | null
  >(initialRequirementVersionId ?? null);

  // Keep the URL in sync with the dropdown so the current view is shareable
  // and the back/forward buttons make sense. We use replaceState (not push)
  // so the dropdown doesn't pollute browser history with one entry per
  // version pick. SSR guards: only touch `window` on the client.
  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const url = new URL(window.location.href);
    if (selectedRequirementVersionId) {
      url.searchParams.set("requirementVersion", selectedRequirementVersionId);
    } else {
      url.searchParams.delete("requirementVersion");
    }
    if (url.toString() !== window.location.href) {
      window.history.replaceState(null, "", url.toString());
    }
  }, [selectedRequirementVersionId]);

  // Pre-fill value for the StartRequirementsCopilotOverlay's "Domain" input.
  // Priority:
  //   1. The prior version's metadata.domain (set by the service when the
  //      version was approved through the Copilot — see service.py).
  //   2. The workspace's customer_name with a trailing " Demo" stripped
  //      (covers seeded demos like "AdTech Demo" → "AdTech").
  //   3. Empty string (first-time interview, no signal — user types it).
  // The user can always overwrite the prefilled value in the form.
  const startCopilotDefaultDomain = useMemo(() => {
    if (pendingReopenVersion) {
      const priorVersion = requirementVersionById[pendingReopenVersion.requirementVersionId];
      const priorDomain = priorVersion?.metadata?.domain;
      if (typeof priorDomain === "string" && priorDomain.trim().length > 0) {
        return priorDomain;
      }
    }
    const customerName = overview?.workspace?.customer_name?.trim();
    if (customerName) {
      return customerName.replace(/\s+demo$/i, "").trim();
    }
    return "";
  }, [pendingReopenVersion, requirementVersionById, overview]);

  // Project the loaded overview into a `WorkspaceSummary` so the edit
  // overlay and archive confirmation can render current values without
  // round-tripping through the API. ``null`` means we have nothing to edit
  // (no workspace loaded, or the loader is still resolving) and the
  // canvas hides the action.
  const currentWorkspaceSummary: WorkspaceSummary | null = useMemo(() => {
    const ws = overview?.workspace;
    if (!ws?.workspace_id) {
      return null;
    }
    return {
      workspaceId: ws.workspace_id,
      customerName: ws.customer_name,
      projectName: ws.project_name,
      environment: ws.environment,
      description: ws.description ?? "",
      status: ws.status ?? "active",
      tags: ws.tags ?? []
    };
  }, [overview]);

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
      setShowCreateWorkspace(false);
      setShowCreateConnectionProfile(false);
      setCreateWorkspaceErrorMessage(null);
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
      setCanvasActionMessage(null);
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

  const activeGraphProfile = useMemo(() => {
    const fromOverview = overview?.latestGraphProfiles?.[0];
    if (fromOverview) {
      return fromOverview;
    }
    const profiles = Object.values(graphProfileById);
    return profiles.length > 0 ? profiles[0] : null;
  }, [graphProfileById, overview]);
  const activeConnectionProfile = useMemo(() => {
    if (!activeGraphProfile) {
      return null;
    }
    return (
      connectionProfileById[activeGraphProfile.connectionProfileId] ??
      overview?.latestConnectionProfiles?.find(
        (profile) => profile.connectionProfileId === activeGraphProfile.connectionProfileId
      ) ??
      null
    );
  }, [activeGraphProfile, connectionProfileById, overview]);

  return (
    <div className="workspace-shell" onClick={() => setMenu(null)}>
      <DataSourceBanner
        status={status}
        errorMessage={errorMessage}
        workspaceName={overview?.workspace?.customer_name}
        graphName={activeGraphProfile?.graphName ?? null}
        databaseName={activeConnectionProfile?.database ?? null}
      />
      <AssetExplorer
        assets={visibleAssets}
        health={health}
        auditEvents={overview?.latestAuditEvents ?? []}
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
        onRequestAssetInfo={(asset) => {
          setSelectedAsset(asset);
          setSelectedStep(null);
          setIsAssetInfoOpen(true);
        }}
        onRequestReopenRequirementsCopilot={(asset) => {
          // The Assets panel surfaces the consolidated "Requirements" row, so
          // `asset.id` is `requirements:<workspaceId>` and reopen always means
          // "produce v(N+1) from the current ACTIVE version" — historical
          // versions are read-only via the canvas dropdown. We resolve the
          // active version here and anchor the new interview on the
          // workspace's first graph profile (BRD-seeded workspaces have one).
          const graphProfileAsset =
            visibleAssets.find((profile) => profile.kind === "graph-profile") ?? null;
          const priorVersion = activeApprovedRequirementVersion;
          if (!graphProfileAsset || !priorVersion) {
            setStartCopilotErrorMessage(
              "Cannot reopen the Requirements Copilot without an active version and a graph profile in this workspace."
            );
            return;
          }
          setStartCopilotErrorMessage(null);
          setSelectedAsset(asset);
          setSelectedStep(null);
          setPendingReopenVersion({
            requirementVersionId: priorVersion.requirementVersionId,
            version: priorVersion.version
          });
          setPendingStartCopilot(graphProfileAsset);
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
        requirementVersions={requirementVersions}
        selectedRequirementVersionId={selectedRequirementVersionId}
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
          (selectedAsset?.kind === "graph-profile" &&
            startingCopilotGraphProfileId === selectedAsset.id) ||
          (selectedAsset?.kind === "requirements" &&
            startingCopilotGraphProfileId !== null)
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
        onClearAssetSelection={() => setIsAssetInfoOpen(false)}
        isAssetInfoOpen={isAssetInfoOpen}
        onClearSelection={() => setSelectedStep(null)}
        onRequestCreateWorkspace={() => {
          setCreateWorkspaceErrorMessage(null);
          setShowCreateWorkspace(true);
        }}
        onRequestEditWorkspace={
          // Hide the action when there is nothing to edit so the menu
          // never lists a dead entry.
          currentWorkspaceSummary
            ? () => {
                setEditWorkspaceErrorMessage(null);
                setShowEditWorkspace(true);
              }
            : undefined
        }
        onRequestArchiveWorkspace={
          currentWorkspaceSummary && currentWorkspaceSummary.status !== "archived"
            ? () => {
                setArchiveWorkspaceErrorMessage(null);
                setShowArchiveWorkspace(true);
              }
            : undefined
        }
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
        onFitCanvas={() => {
          setCanvasActionMessage("Fit All requested. The current workspace layout is already fit to visible assets.");
        }}
        onCenterCanvas={() => {
          setCanvasActionMessage("Canvas centered on the selected workspace object.");
        }}
        onViewOperationalDAG={() => {
          const runAsset =
            selectedAsset?.kind === "run"
              ? selectedAsset
              : visibleAssets.find((asset) => asset.kind === "run") ?? null;
          if (runAsset) {
            setSelectedAsset(runAsset);
            setSelectedStep(null);
            setCanvasActionMessage(`Showing operational DAG for ${runAsset.label}.`);
            return;
          }
          setCanvasActionMessage("No workflow run is available for an operational DAG view.");
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
            setPendingReopenVersion(null);
            setPendingStartCopilot(graphProfileAsset);
          }
        }}
        onRequestReopenRequirementsCopilot={(basedOnVersionId) => {
          const priorVersion = requirementVersionById[basedOnVersionId];
          // Reopen requires a graph profile to anchor the copilot session.
          // Prefer the graph profile referenced by the prior interview if we
          // can resolve it; otherwise fall back to the first graph profile in
          // the workspace (typical AdTech / BRD-driven workspaces have only
          // one anyway).
          const graphProfileAsset =
            visibleAssets.find((asset) => asset.kind === "graph-profile") ?? null;
          if (!priorVersion || !graphProfileAsset) {
            setStartCopilotErrorMessage(
              "Cannot reopen the Requirements Copilot without a graph profile in this workspace."
            );
            return;
          }
          setStartCopilotErrorMessage(null);
          setPendingReopenVersion({
            requirementVersionId: priorVersion.requirementVersionId,
            version: priorVersion.version
          });
          setPendingStartCopilot(graphProfileAsset);
        }}
        onSelectRequirementVersion={setSelectedRequirementVersionId}
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
            // Re-fetch the overview so the consolidated "Requirements" row
            // reflects the new version count + active label, and clear the
            // canvas's pinned version so it follows the new active by default
            // (avoids the user being stuck looking at v1 after they just
            // approved v2).
            setSelectedRequirementVersionId(null);
            await refreshOverview();
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
        onExportReport={async (reportId, format) => {
          // The shell owns the actual file download because it has a stable
          // place in the React tree across canvas reloads — handing it to a
          // child means the click can be aborted by an unrelated rerender.
          const download = await exportReport(reportId, format);
          triggerBrowserDownload(download.blob, download.filename);
        }}
      />
      <ContextMenu menu={menu} onClose={() => setMenu(null)} />
      {showCreateWorkspace ? (
        <CreateWorkspaceOverlay
          isCreating={isCreatingWorkspace}
          errorMessage={createWorkspaceErrorMessage}
          onCancel={() => setShowCreateWorkspace(false)}
          onSubmit={async (input) => {
            setCreateWorkspaceErrorMessage(null);
            setIsCreatingWorkspace(true);
            try {
              const workspace = await createWorkspace(input);
              setSelectedAsset(null);
              setSelectedStep(null);
              setCanvasActionMessage(
                `Created workspace ${workspace.customerName} / ${workspace.projectName}.`
              );
              setShowCreateWorkspace(false);
            } catch (error) {
              setCreateWorkspaceErrorMessage(
                error instanceof Error ? error.message : "Failed to create workspace"
              );
            } finally {
              setIsCreatingWorkspace(false);
            }
          }}
        />
      ) : null}
      {showEditWorkspace && currentWorkspaceSummary ? (
        <EditWorkspaceOverlay
          workspace={currentWorkspaceSummary}
          isSaving={isSavingWorkspaceEdit}
          errorMessage={editWorkspaceErrorMessage}
          onCancel={() => setShowEditWorkspace(false)}
          onSubmit={async (input) => {
            setEditWorkspaceErrorMessage(null);
            setIsSavingWorkspaceEdit(true);
            try {
              const updated = await updateWorkspace(
                currentWorkspaceSummary.workspaceId,
                input
              );
              setShowEditWorkspace(false);
              setCanvasActionMessage(
                `Updated workspace ${updated.customerName} / ${updated.projectName}.`
              );
            } catch (error) {
              setEditWorkspaceErrorMessage(
                error instanceof Error ? error.message : "Failed to update workspace"
              );
            } finally {
              setIsSavingWorkspaceEdit(false);
            }
          }}
        />
      ) : null}
      {showArchiveWorkspace && currentWorkspaceSummary ? (
        <ArchiveWorkspaceConfirmationOverlay
          workspace={currentWorkspaceSummary}
          isArchiving={isArchivingWorkspace}
          errorMessage={archiveWorkspaceErrorMessage}
          onCancel={() => setShowArchiveWorkspace(false)}
          onConfirm={() => {
            setArchiveWorkspaceErrorMessage(null);
            setIsArchivingWorkspace(true);
            void archiveWorkspace(currentWorkspaceSummary.workspaceId)
              .then((archived) => {
                setShowArchiveWorkspace(false);
                setCanvasActionMessage(
                  `Archived workspace ${archived.customerName} / ${archived.projectName}.`
                );
              })
              .catch((error) =>
                setArchiveWorkspaceErrorMessage(
                  error instanceof Error ? error.message : "Failed to archive workspace"
                )
              )
              .finally(() => setIsArchivingWorkspace(false));
          }}
        />
      ) : null}
      {canvasActionMessage ? (
        <FloatingDetailPanel
          title="Canvas View"
          stackIndex={2}
          onClose={() => setCanvasActionMessage(null)}
        >
          <p className="muted">{canvasActionMessage}</p>
        </FloatingDetailPanel>
      ) : null}
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
          onLoadGraphs={listConnectionProfileGraphs}
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
          basedOnVersion={pendingReopenVersion}
          defaultDomain={startCopilotDefaultDomain}
          onCancel={() => {
            setPendingStartCopilot(null);
            setPendingReopenVersion(null);
          }}
          onSubmit={async (input) => {
            setStartCopilotErrorMessage(null);
            setStartingCopilotGraphProfileId(pendingStartCopilot.id);
            try {
              const interview = await startRequirementsCopilot(
                pendingStartCopilot.id,
                {
                  ...input,
                  basedOnVersionId:
                    input.basedOnVersionId ??
                    pendingReopenVersion?.requirementVersionId
                }
              );
              setActiveRequirementInterview(interview);
              setApprovedRequirementVersion(null);
              setSelectedAsset(pendingStartCopilot);
              setSelectedStep(null);
              setPendingStartCopilot(null);
              setPendingReopenVersion(null);
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

function DataSourceBanner({
  status,
  errorMessage,
  workspaceName,
  graphName,
  databaseName
}: {
  status: "demo" | "loading" | "ready" | "error";
  errorMessage?: string;
  workspaceName?: string;
  graphName?: string | null;
  databaseName?: string | null;
}) {
  if (status === "ready") {
    return (
      <div className="data-source-banner data-source-banner-ready" role="status">
        <strong>Live</strong>
        <span>
          Loaded from Product API{workspaceName ? ` — ${workspaceName}` : ""}
          {graphName ? (
            <>
              {" · Analyzing "}
              <span className="data-source-banner-graph">{graphName}</span>
              {databaseName ? (
                <>
                  {" in "}
                  <code className="data-source-banner-database">{databaseName}</code>
                </>
              ) : null}
            </>
          ) : null}
        </span>
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div className="data-source-banner data-source-banner-loading" role="status">
        <strong>Loading…</strong>
        <span>Fetching workspace from Product API</span>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="data-source-banner data-source-banner-error" role="alert">
        <strong>Error</strong>
        <span>{errorMessage ?? "Failed to load workspace from Product API"}. Showing demo data.</span>
        <button type="button" onClick={() => window.location.reload()}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="data-source-banner data-source-banner-demo" role="status">
      <strong>Demo data</strong>
      <span>
        Product API has no workspaces yet, or this tab is showing a stale bundle. Hard-reload the
        page (⌘⇧R) to fetch live data.
      </span>
      <button type="button" onClick={() => window.location.reload()}>
        Reload
      </button>
    </div>
  );
}

function triggerBrowserDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function downloadJSON(filename: string, data: unknown) {
  triggerBrowserDownload(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
    filename
  );
}
