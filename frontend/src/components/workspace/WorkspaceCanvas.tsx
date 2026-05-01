"use client";

import { CanvasLensLegend } from "./CanvasLensLegend";
import { ConnectionProfileCanvas } from "./ConnectionProfileCanvas";
import { DynamicReportCanvas } from "./DynamicReportCanvas";
import { EmptyCanvasState } from "./EmptyCanvasState";
import { GraphProfileCanvas } from "./GraphProfileCanvas";
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
  graphProfile: GraphProfileSummary | null;
  sourceDocument: SourceDocumentSummary | null;
  reportBundle: ReportBundle | null;
  dataStatus: "demo" | "loading" | "ready" | "error";
  dataErrorMessage?: string;
  isVerifyingConnection: boolean;
  isDiscoveringGraph: boolean;
  isStartingRequirementsCopilot: boolean;
  connectionVerificationErrorMessage: string | null;
  activeRequirementInterview: RequirementInterview | null;
  showHelp: boolean;
  onSelectStep: (step: WorkflowDAGNode) => void;
  onClearAssetSelection: () => void;
  onClearSelection: () => void;
  onRequestCreateConnectionProfile: () => void;
  onVerifyConnectionProfile: (connectionProfileId: string) => void;
  onRequestDiscoverGraph: (connectionProfileId: string) => void;
  onRequestStartRequirementsCopilot: (graphProfileId: string) => void;
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
  graphProfile,
  sourceDocument,
  reportBundle,
  dataStatus,
  dataErrorMessage,
  isVerifyingConnection,
  isDiscoveringGraph,
  isStartingRequirementsCopilot,
  connectionVerificationErrorMessage,
  activeRequirementInterview,
  showHelp,
  onSelectStep,
  onClearAssetSelection,
  onClearSelection,
  onRequestCreateConnectionProfile,
  onVerifyConnectionProfile,
  onRequestDiscoverGraph,
  onRequestStartRequirementsCopilot,
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
        </FloatingDetailPanel>
      ) : null}

      {activeRequirementInterview ? (
        <FloatingDetailPanel
          title="Requirements Copilot"
          stackIndex={selectedStep ? 1 : 0}
          onClose={onCloseRequirementsCopilot}
        >
          <p>Status: {activeRequirementInterview.status}</p>
          <p>Domain: {activeRequirementInterview.domain ?? "Not specified"}</p>
          <h4>Starter Questions</h4>
          <ol className="copilot-question-list">
            {activeRequirementInterview.questions.map((question, index) => (
              <li key={String(question.id ?? index)}>
                {String(question.text ?? "Question")}
              </li>
            ))}
          </ol>
        </FloatingDetailPanel>
      ) : null}

      {showHelp ? <WorkspaceHelpOverlay onClose={onCloseHelp} /> : null}
    </main>
  );
}
