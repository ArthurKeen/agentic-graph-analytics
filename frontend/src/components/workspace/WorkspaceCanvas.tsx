"use client";

import { CanvasLensLegend } from "./CanvasLensLegend";
import { EmptyCanvasState } from "./EmptyCanvasState";
import { FloatingDetailPanel } from "./FloatingDetailPanel";
import { buildCanvasContextMenu } from "./contextMenus/canvas";
import { buildPipelineStepContextMenu } from "./contextMenus/pipelineStep";
import type { ContextMenuState } from "./contextMenus/types";
import type { WorkflowDAGNode, WorkflowDAGView, WorkspaceAsset } from "@/lib/product-api/types";

interface WorkspaceCanvasProps {
  selectedAsset: WorkspaceAsset | null;
  selectedStep: WorkflowDAGNode | null;
  dagView: WorkflowDAGView | null;
  onSelectStep: (step: WorkflowDAGNode) => void;
  onClearSelection: () => void;
  onOpenMenu: (menu: ContextMenuState) => void;
}

export function WorkspaceCanvas({
  selectedAsset,
  selectedStep,
  dagView,
  onSelectStep,
  onClearSelection,
  onOpenMenu
}: WorkspaceCanvasProps) {
  if (!selectedAsset) {
    return (
      <main
        className="workspace-canvas"
        onContextMenu={(event) => {
          event.preventDefault();
          onOpenMenu({
            x: event.clientX,
            y: event.clientY,
            items: buildCanvasContextMenu({
              onFitAll: () => undefined,
              onCenterView: () => undefined,
              onViewAsOperational: () => undefined
            })
          });
        }}
      >
        <EmptyCanvasState />
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
          items: buildCanvasContextMenu({
            onFitAll: () => undefined,
            onCenterView: () => undefined,
            onViewAsOperational: () => undefined
          })
        });
      }}
    >
      <header className="workspace-header">
        <div>
          <h2>{selectedAsset.label}</h2>
          <div className="lens-indicator">(Operational DAG view)</div>
        </div>
        <p className="muted">Right-click steps or canvas for actions.</p>
      </header>

      {dagView && selectedAsset.kind === "run" ? (
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
      ) : (
        <EmptyCanvasState />
      )}

      <CanvasLensLegend lensName="Operational DAG" />

      {selectedStep ? (
        <FloatingDetailPanel title={selectedStep.label} onClose={onClearSelection}>
          <p>Status: {selectedStep.status}</p>
          <p>Artifacts: {selectedStep.artifactCount}</p>
          <p>Warnings: {selectedStep.warningCount}</p>
          <p>Errors: {selectedStep.errorCount}</p>
        </FloatingDetailPanel>
      ) : null}
    </main>
  );
}
