"use client";

import { CanvasLensLegend } from "./CanvasLensLegend";
import { ConnectionProfileCanvas } from "./ConnectionProfileCanvas";
import { DynamicReportCanvas } from "./DynamicReportCanvas";
import { EmptyCanvasState } from "./EmptyCanvasState";
import { GraphProfileCanvas } from "./GraphProfileCanvas";
import { RequirementsCopilotPanel } from "./RequirementsCopilotPanel";
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
  onSelectStep: (step: WorkflowDAGNode) => void;
  onClearAssetSelection: () => void;
  onClearSelection: () => void;
  onRequestCreateConnectionProfile: () => void;
  onExportWorkspace: () => void;
  onRequestImportWorkspace: () => void;
  onVerifyConnectionProfile: (connectionProfileId: string) => void;
  onRequestDiscoverGraph: (connectionProfileId: string) => void;
  onRequestStartRequirementsCopilot: (graphProfileId: string) => void;
  onAnswerRequirementsCopilotQuestion: (
    requirementInterviewId: string,
    questionId: string,
    answer: string
  ) => Promise<void>;
  onGenerateRequirementsDraft: (requirementInterviewId: string) => Promise<void>;
  onApproveRequirementsDraft: (
    requirementInterviewId: string,
    version: number
  ) => Promise<void>;
  onCloseRequirementsCopilot: () => void;
  onShowHelp: () => void;
  onCloseHelp: () => void;
  onOpenMenu: (menu: ContextMenuState) => void;
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
  onSelectStep,
  onClearAssetSelection,
  onClearSelection,
  onRequestCreateConnectionProfile,
  onExportWorkspace,
  onRequestImportWorkspace,
  onVerifyConnectionProfile,
  onRequestDiscoverGraph,
  onRequestStartRequirementsCopilot,
  onAnswerRequirementsCopilotQuestion,
  onGenerateRequirementsDraft,
  onApproveRequirementsDraft,
  onCloseRequirementsCopilot,
  onShowHelp,
  onCloseHelp,
  onOpenMenu
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
            : "Operational DAG";
  const canvasMenuItems = () =>
    buildCanvasContextMenu({
      onCreateConnectionProfile: onRequestCreateConnectionProfile,
      onExportWorkspace,
      onImportWorkspace: onRequestImportWorkspace,
      onFitAll: () => undefined,
      onCenterView: () => undefined,
      onViewAsOperational: () => undefined,
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
                      onRetryRun: () => onSelectStep(node)
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
        <DynamicReportCanvas report={reportBundle} />
      ) : (
        <EmptyCanvasState />
      )}

      <CanvasLensLegend lensName={lensName} />

      <AssetInfoPanel asset={selectedAsset} onClose={onClearAssetSelection} />

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
