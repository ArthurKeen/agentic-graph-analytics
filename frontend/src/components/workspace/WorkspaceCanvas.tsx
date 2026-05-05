"use client";

import { CanvasLensLegend } from "./CanvasLensLegend";
import { ConnectionProfileCanvas } from "./ConnectionProfileCanvas";
import { DynamicReportCanvas } from "./DynamicReportCanvas";
import { EmptyCanvasState } from "./EmptyCanvasState";
import { GraphProfileCanvas } from "./GraphProfileCanvas";
import { RequirementsCopilotPanel } from "./RequirementsCopilotPanel";
import { RequirementVersionCanvas } from "./RequirementVersionCanvas";
import { SourceDocumentCanvas } from "./SourceDocumentCanvas";
import { AssetInfoPanel } from "./AssetInfoPanel";
import { FloatingDetailPanel } from "./FloatingDetailPanel";
import { WorkspaceHelpOverlay } from "./WorkspaceHelpOverlay";
import { buildCanvasContextMenu } from "./contextMenus/canvas";
import { buildPipelineStepContextMenu } from "./contextMenus/pipelineStep";
import type { ContextMenuState } from "./contextMenus/types";
import type {
  ConnectionProfileSummary,
  ConnectionVerificationResult,
  ReportBundle,
  ReportExportFormat,
  GraphProfileSummary,
  RequirementInterview,
  RequirementVersion,
  SourceDocumentSummary,
  WorkflowDAGNode,
  WorkflowDAGView,
  WorkspaceAsset
} from "@/lib/product-api/types";

interface WorkspaceCanvasProps {
  selectedAsset: WorkspaceAsset | null;
  selectedStep: WorkflowDAGNode | null;
  connectionProfile: ConnectionProfileSummary | null;
  connectionVerificationResult: ConnectionVerificationResult | null;
  dagView: WorkflowDAGView | null;
  selectedStepRecoveryActions: string[];
  graphProfile: GraphProfileSummary | null;
  sourceDocument: SourceDocumentSummary | null;
  /** All requirement versions known to the workspace. The canvas computes
   * the active and currently-displayed versions itself based on
   * `selectedRequirementVersionId`. */
  requirementVersions: RequirementVersion[];
  /** Which version the user has selected in the canvas dropdown. `null` means
   * "follow the active version" — useful so that approving a new version
   * automatically advances the view without forcing the user to re-pick. */
  selectedRequirementVersionId: string | null;
  reportBundle: ReportBundle | null;
  dataStatus: "demo" | "loading" | "ready" | "error";
  dataErrorMessage?: string;
  isVerifyingConnection: boolean;
  isDiscoveringGraph: boolean;
  isStartingRequirementsCopilot: boolean;
  isSavingCopilotAnswer: boolean;
  isGeneratingRequirementsDraft: boolean;
  isApprovingRequirementsDraft: boolean;
  connectionVerificationErrorMessage: string | null;
  requirementsCopilotErrorMessage: string | null;
  activeRequirementInterview: RequirementInterview | null;
  approvedRequirementVersion: RequirementVersion | null;
  showHelp: boolean;
  isAssetInfoOpen: boolean;
  onSelectStep: (step: WorkflowDAGNode) => void;
  onRetryWorkflowStep: (step: WorkflowDAGNode) => void;
  onClearAssetSelection: () => void;
  onClearSelection: () => void;
  onRequestCreateWorkspace: () => void;
  /** When omitted, the "Edit Workspace" canvas action is hidden. The shell
   * passes ``undefined`` in demo mode or when no workspace is loaded so we
   * never expose dead actions. */
  onRequestEditWorkspace?: () => void;
  /** When omitted, the "Archive Workspace" canvas action is hidden. The
   * shell passes ``undefined`` for already-archived workspaces. */
  onRequestArchiveWorkspace?: () => void;
  onRequestCreateConnectionProfile: () => void;
  onRequestCreateWorkflowRun: () => void;
  onExportWorkspace: () => void;
  onRequestImportWorkspace: () => void;
  onFitCanvas: () => void;
  onCenterCanvas: () => void;
  onViewOperationalDAG: () => void;
  onVerifyConnectionProfile: (connectionProfileId: string) => void;
  onRequestDiscoverGraph: (connectionProfileId: string) => void;
  onRequestStartRequirementsCopilot: (graphProfileId: string) => void;
  /** Reopen the Requirements Copilot pre-populated from a prior approved
   * RequirementVersion. The current AdtechGraph profile is used as the
   * graph context. */
  onRequestReopenRequirementsCopilot: (basedOnVersionId: string) => void;
  /** Change the version displayed by `RequirementVersionCanvas`. Pass `null`
   * to revert to "follow active". */
  onSelectRequirementVersion: (versionId: string | null) => void;
  onAnswerRequirementsCopilotQuestion: (
    requirementInterviewId: string,
    questionId: string,
    answer: string
  ) => Promise<void>;
  onGenerateRequirementsDraft: (requirementInterviewId: string) => Promise<void>;
  onApproveRequirementsDraft: (
    requirementInterviewId: string,
    version: number | null
  ) => Promise<void>;
  onCloseRequirementsCopilot: () => void;
  onShowHelp: () => void;
  onCloseHelp: () => void;
  onOpenMenu: (menu: ContextMenuState) => void;
  /** Trigger an HTML or Markdown export of the currently displayed report.
   * The shell handles the actual download (Blob → object URL → anchor click)
   * so the canvas stays purely declarative. */
  onExportReport: (reportId: string, format: ReportExportFormat) => Promise<void>;
}

export function WorkspaceCanvas({
  selectedAsset,
  selectedStep,
  connectionProfile,
  connectionVerificationResult,
  dagView,
  selectedStepRecoveryActions,
  graphProfile,
  sourceDocument,
  requirementVersions,
  selectedRequirementVersionId,
  reportBundle,
  dataStatus,
  dataErrorMessage,
  isVerifyingConnection,
  isDiscoveringGraph,
  isStartingRequirementsCopilot,
  isSavingCopilotAnswer,
  isGeneratingRequirementsDraft,
  isApprovingRequirementsDraft,
  connectionVerificationErrorMessage,
  requirementsCopilotErrorMessage,
  activeRequirementInterview,
  approvedRequirementVersion,
  showHelp,
  isAssetInfoOpen,
  onSelectStep,
  onRetryWorkflowStep,
  onClearAssetSelection,
  onClearSelection,
  onRequestCreateWorkspace,
  onRequestEditWorkspace,
  onRequestArchiveWorkspace,
  onRequestCreateConnectionProfile,
  onRequestCreateWorkflowRun,
  onExportWorkspace,
  onRequestImportWorkspace,
  onFitCanvas,
  onCenterCanvas,
  onViewOperationalDAG,
  onVerifyConnectionProfile,
  onRequestDiscoverGraph,
  onRequestStartRequirementsCopilot,
  onRequestReopenRequirementsCopilot,
  onSelectRequirementVersion,
  onAnswerRequirementsCopilotQuestion,
  onGenerateRequirementsDraft,
  onApproveRequirementsDraft,
  onCloseRequirementsCopilot,
  onShowHelp,
  onCloseHelp,
  onOpenMenu,
  onExportReport
}: WorkspaceCanvasProps) {
  const lensName =
    selectedAsset?.kind === "report"
      ? "Dynamic Report"
      : selectedAsset?.kind === "connection-profile"
        ? "Connection Profile"
        : selectedAsset?.kind === "graph-profile"
          ? "Graph Profile"
          : selectedAsset?.kind === "document"
            ? "Source Document"
            : selectedAsset?.kind === "requirements"
              ? "Requirements"
              : "Operational DAG";
  const canvasMenuItems = () =>
    buildCanvasContextMenu({
      onCreateWorkspace: onRequestCreateWorkspace,
      onEditWorkspace: onRequestEditWorkspace,
      onArchiveWorkspace: onRequestArchiveWorkspace,
      onCreateConnectionProfile: onRequestCreateConnectionProfile,
      onCreateWorkflowRun: onRequestCreateWorkflowRun,
      onExportWorkspace,
      onImportWorkspace: onRequestImportWorkspace,
      onFitAll: onFitCanvas,
      onCenterView: onCenterCanvas,
      onViewAsOperational: onViewOperationalDAG,
      onShowHelp
    });

  if (!selectedAsset) {
    return (
      <main
        className="workspace-canvas"
        onContextMenu={(event) => {
          event.preventDefault();
          onOpenMenu({
            x: event.clientX,
            y: event.clientY,
            items: canvasMenuItems()
          });
        }}
      >
        <EmptyCanvasState />
        {showHelp ? <WorkspaceHelpOverlay onClose={onCloseHelp} /> : null}
      </main>
    );
  }

  return (
    <main
      className="workspace-canvas"
      onContextMenu={(event) => {
        event.preventDefault();
        onOpenMenu({
          x: event.clientX,
          y: event.clientY,
          items: canvasMenuItems()
        });
      }}
    >
      <header className="workspace-header">
        <div>
          <h2>{selectedAsset.label}</h2>
          <div className="lens-indicator">({lensName} view)</div>
        </div>
        <div className="workspace-header-actions">
          <p className="muted">Right-click steps or canvas for actions.</p>
          <button
            className="help-button"
            type="button"
            aria-label="Show workspace help"
            onClick={(event) => {
              event.stopPropagation();
              onShowHelp();
            }}
          >
            ?
          </button>
        </div>
      </header>
      <p className="muted">
        Data source: {dataStatus}
        {dataErrorMessage ? ` (${dataErrorMessage})` : ""}
      </p>

      {connectionProfile && selectedAsset.kind === "connection-profile" ? (
        <ConnectionProfileCanvas
          connectionProfile={connectionProfile}
          verificationResult={connectionVerificationResult}
          isVerifying={isVerifyingConnection}
          isDiscovering={isDiscoveringGraph}
          verificationErrorMessage={connectionVerificationErrorMessage}
          onVerify={onVerifyConnectionProfile}
          onDiscoverGraph={onRequestDiscoverGraph}
        />
      ) : sourceDocument && selectedAsset.kind === "document" ? (
        <SourceDocumentCanvas document={sourceDocument} />
      ) : graphProfile && selectedAsset.kind === "graph-profile" ? (
        <GraphProfileCanvas
          graphProfile={graphProfile}
          isStartingRequirementsCopilot={isStartingRequirementsCopilot}
          onStartRequirementsCopilot={onRequestStartRequirementsCopilot}
        />
      ) : selectedAsset.kind === "requirements" ? (
        <RequirementVersionCanvas
          versions={requirementVersions}
          selectedVersionId={selectedRequirementVersionId}
          isStartingRequirementsCopilot={isStartingRequirementsCopilot}
          onSelectVersion={onSelectRequirementVersion}
          onReopenCopilot={onRequestReopenRequirementsCopilot}
        />
      ) : dagView && selectedAsset.kind === "run" ? (
        <section className="pipeline-dag" aria-label="Workflow DAG">
          {dagView.nodes.map((node, index) => (
            <div key={node.id} style={{ display: "contents" }}>
              {index > 0 ? <span className="pipeline-edge">→</span> : null}
              <button
                className="pipeline-step"
                data-status={node.status}
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onSelectStep(node);
                }}
                onContextMenu={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  onOpenMenu({
                    x: event.clientX,
                    y: event.clientY,
                    items: buildPipelineStepContextMenu({
                      onViewStepDetails: () => onSelectStep(node),
                      onCopyError: () =>
                        void navigator.clipboard?.writeText(
                          node.errorCount > 0 ? `${node.errorCount} errors` : "No errors"
                        ),
                      onViewRunResults: () => onSelectStep(node),
                      onRetryRun: () => onRetryWorkflowStep(node)
                    })
                  });
                }}
              >
                <strong>{node.label}</strong>
                <br />
                <span className="muted">{node.status}</span>
              </button>
            </div>
          ))}
        </section>
      ) : reportBundle && selectedAsset.kind === "report" ? (
        <DynamicReportCanvas
          report={reportBundle}
          onExport={(format) => onExportReport(reportBundle.manifest.reportId, format)}
        />
      ) : (
        <EmptyCanvasState />
      )}

      <CanvasLensLegend lensName={lensName} />

      {isAssetInfoOpen && !selectedStep ? (
        <AssetInfoPanel asset={selectedAsset} onClose={onClearAssetSelection} />
      ) : null}

      {selectedStep ? (
        <FloatingDetailPanel title={selectedStep.label} onClose={onClearSelection}>
          <p>Status: {selectedStep.status}</p>
          <p>Artifacts: {selectedStep.artifactCount}</p>
          <p>Warnings: {selectedStep.warningCount}</p>
          <p>Errors: {selectedStep.errorCount}</p>
          <p>
            Recovery actions:{" "}
            {selectedStepRecoveryActions.length > 0
              ? selectedStepRecoveryActions.join(", ")
              : "None"}
          </p>
        </FloatingDetailPanel>
      ) : null}

      {activeRequirementInterview ? (
        <RequirementsCopilotPanel
          interview={activeRequirementInterview}
          stackIndex={selectedStep ? 1 : 0}
          isSavingAnswer={isSavingCopilotAnswer}
          isGeneratingDraft={isGeneratingRequirementsDraft}
          isApprovingDraft={isApprovingRequirementsDraft}
          errorMessage={requirementsCopilotErrorMessage}
          approvedRequirementVersion={approvedRequirementVersion}
          existingRequirementVersions={requirementVersions}
          onAnswerQuestion={(questionId, answer) =>
            onAnswerRequirementsCopilotQuestion(
              activeRequirementInterview.requirementInterviewId,
              questionId,
              answer
            )
          }
          onGenerateDraft={() =>
            onGenerateRequirementsDraft(activeRequirementInterview.requirementInterviewId)
          }
          onApproveDraft={(version) =>
            onApproveRequirementsDraft(
              activeRequirementInterview.requirementInterviewId,
              version
            )
          }
          onClose={onCloseRequirementsCopilot}
        />
      ) : null}

      {showHelp ? <WorkspaceHelpOverlay onClose={onCloseHelp} /> : null}
    </main>
  );
}
