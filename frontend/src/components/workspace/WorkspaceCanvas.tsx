"use client";

import { CanvasLensLegend } from "./CanvasLensLegend";
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
  ReportBundle,
  GraphProfileSummary,
  SourceDocumentSummary,
  WorkflowDAGNode,
  WorkflowDAGView,
  WorkspaceAsset
} from "@/lib/product-api/types";

interface WorkspaceCanvasProps {
  selectedAsset: WorkspaceAsset | null;
  selectedStep: WorkflowDAGNode | null;
  dagView: WorkflowDAGView | null;
  graphProfile: GraphProfileSummary | null;
  sourceDocument: SourceDocumentSummary | null;
  reportBundle: ReportBundle | null;
  dataStatus: "demo" | "loading" | "ready" | "error";
  dataErrorMessage?: string;
  showHelp: boolean;
  onSelectStep: (step: WorkflowDAGNode) => void;
  onClearAssetSelection: () => void;
  onClearSelection: () => void;
  onRequestCreateConnectionProfile: () => void;
  onShowHelp: () => void;
  onCloseHelp: () => void;
  onOpenMenu: (menu: ContextMenuState) => void;
}

export function WorkspaceCanvas({
  selectedAsset,
  selectedStep,
  dagView,
  graphProfile,
  sourceDocument,
  reportBundle,
  dataStatus,
  dataErrorMessage,
  showHelp,
  onSelectStep,
  onClearAssetSelection,
  onClearSelection,
  onRequestCreateConnectionProfile,
  onShowHelp,
  onCloseHelp,
  onOpenMenu
}: WorkspaceCanvasProps) {
  const lensName =
    selectedAsset?.kind === "report"
      ? "Dynamic Report"
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

      {sourceDocument && selectedAsset.kind === "document" ? (
        <SourceDocumentCanvas document={sourceDocument} />
      ) : graphProfile && selectedAsset.kind === "graph-profile" ? (
        <GraphProfileCanvas graphProfile={graphProfile} />
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

      {showHelp ? <WorkspaceHelpOverlay onClose={onCloseHelp} /> : null}
    </main>
  );
}
