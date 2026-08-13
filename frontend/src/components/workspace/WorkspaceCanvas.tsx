"use client";

import { AnalysisCatalogCanvas } from "./AnalysisCatalogCanvas";
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
  AnalysisCatalogView,
  AnalysisExecution,
  AnalysisExecutionComparison,
  AnalysisExecutionFilters,
  AnalysisLineage,
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
  WorkflowRunStatusView,
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
  /** FR-31a: cooperative cancel for the currently displayed agentic
   * run. The shell wires this to ``cancelWorkflowRun(runId)``. The
   * canvas only renders the cancel button when the run is agentic
   * AND status is ``running``. */
  onCancelWorkflowRun?: () => void;
  /** FR-31a: live supervisor snapshot for the displayed agentic run.
   * ``null`` outside agentic mode (or before the first poll lands).
   * Drives the AgenticRunStatusPanel that shows executor_kind,
   * supervisor outcome, and a "cancellation requested" hint. */
  agenticRunStatus?: WorkflowRunStatusView | null;
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
  /** FR-13: omitted when no workspace is loaded (demo mode included), so
   * the canvas hides the action rather than rendering a dead entry. */
  onRequestUploadDocument?: () => void;
  /** FR-45..FR-48: Analysis Catalog data access. All four are supplied
   * together by the shell; the catalog view renders only when present. */
  onBrowseAnalysisCatalog?: () => Promise<AnalysisCatalogView>;
  onSearchAnalysisExecutions?: (
    filters: AnalysisExecutionFilters
  ) => Promise<AnalysisExecution[]>;
  onCompareAnalysisExecutions?: (
    ids: string[]
  ) => Promise<AnalysisExecutionComparison>;
  onGetAnalysisLineage?: (id: string) => Promise<AnalysisLineage>;
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
  onCancelWorkflowRun,
  agenticRunStatus,
  onClearAssetSelection,
  onClearSelection,
  onRequestCreateWorkspace,
  onRequestEditWorkspace,
  onRequestArchiveWorkspace,
  onRequestCreateConnectionProfile,
  onRequestCreateWorkflowRun,
  onExportWorkspace,
  onRequestImportWorkspace,
  onRequestUploadDocument,
  onBrowseAnalysisCatalog,
  onSearchAnalysisExecutions,
  onCompareAnalysisExecutions,
  onGetAnalysisLineage,
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
              : selectedAsset?.kind === "analysis-catalog"
                ? "Analysis Catalog"
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
      onUploadDocument: onRequestUploadDocument,
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
      ) : selectedAsset.kind === "analysis-catalog" &&
        onBrowseAnalysisCatalog &&
        onSearchAnalysisExecutions &&
        onCompareAnalysisExecutions &&
        onGetAnalysisLineage ? (
        <AnalysisCatalogCanvas
          onBrowse={onBrowseAnalysisCatalog}
          onSearch={onSearchAnalysisExecutions}
          onCompare={onCompareAnalysisExecutions}
          onLineage={onGetAnalysisLineage}
        />
      ) : dagView && selectedAsset.kind === "run" ? (
        <section
          className="pipeline-dag-section"
          aria-label="Workflow run"
          data-workflow-mode={dagView.workflowMode}
        >
          {/* FR-31a: live supervisor-side status. Renders for every
              agentic run (running, completed, cancelled, failed) so
              the user can see which executor handled the run and what
              outcome the supervisor recorded — independent from the
              persisted status, which lags by one poll until the
              orchestrator finishes its current step. */}
          {(dagView.workflowMode === "agentic" ||
            dagView.workflowMode === "parallel_agentic") &&
          agenticRunStatus ? (
            <AgenticRunStatusPanel snapshot={agenticRunStatus} />
          ) : null}
          {/* FR-31a: surface a run-level cancel button for agentic
              runs that are still RUNNING. Cancel is cooperative — the
              run will transition to "cancelled" once the orchestrator
              observes the token between steps, which the canvas will
              pick up on its next refresh. */}
          {(dagView.workflowMode === "agentic" ||
            dagView.workflowMode === "parallel_agentic") &&
          dagView.status === "running" &&
          onCancelWorkflowRun ? (
            <div className="pipeline-dag-actions">
              <button
                type="button"
                className="secondary-button"
                disabled={agenticRunStatus?.supervisor.cancelRequested === true}
                onClick={(event) => {
                  event.stopPropagation();
                  onCancelWorkflowRun();
                }}
              >
                {agenticRunStatus?.supervisor.cancelRequested
                  ? "Cancel Requested…"
                  : "Cancel Run"}
              </button>
            </div>
          ) : null}
          <div className="pipeline-dag" aria-label="Workflow DAG">
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
                            node.errorCount > 0
                              ? `${node.errorCount} errors`
                              : "No errors"
                          ),
                        onViewRunResults: () => onSelectStep(node),
                        onRetryRun: () => onRetryWorkflowStep(node),
                        // Hide per-step retry on agentic runs — there
                        // is no checkpoint to resume from in Phase 1.
                        isAgenticRun:
                          dagView.workflowMode === "agentic" ||
                          dagView.workflowMode === "parallel_agentic",
                        stepStatus: node.status
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
          </div>
        </section>
      ) : reportBundle && selectedAsset.kind === "report" ? (
        <DynamicReportCanvas
          report={reportBundle}
          onExport={(format) => onExportReport(reportBundle.manifest.reportId, format)}
        />
      ) : (
        <EmptyCanvasState />
      )}

      {selectedAsset.kind === "run" ? (
        <CanvasLensLegend lensName={lensName} />
      ) : null}

      {isAssetInfoOpen && !selectedStep ? (
        <AssetInfoPanel asset={selectedAsset} onClose={onClearAssetSelection} />
      ) : null}

      {selectedStep ? (
        <FloatingDetailPanel title={selectedStep.label} onClose={onClearSelection}>
          <p>Status: {selectedStep.status}</p>
          {selectedStep.agentName ? <p>Agent: {selectedStep.agentName}</p> : null}
          {selectedStep.startedAt || selectedStep.completedAt ? (
            <p className="muted">
              {selectedStep.startedAt ? `Started ${selectedStep.startedAt}` : "Not started"}
              {selectedStep.completedAt ? ` · completed ${selectedStep.completedAt}` : ""}
              {selectedStep.durationMs != null ? ` · ${selectedStep.durationMs}ms` : ""}
            </p>
          ) : null}
          <p>Retry count: {selectedStep.retryCount ?? 0}</p>
          {selectedStep.checkpointId ? (
            <p>Checkpoint: {selectedStep.checkpointId}</p>
          ) : null}
          {selectedStep.inputs && Object.keys(selectedStep.inputs).length > 0 ? (
            <p className="muted">Inputs: {JSON.stringify(selectedStep.inputs)}</p>
          ) : null}
          {selectedStep.outputs && Object.keys(selectedStep.outputs).length > 0 ? (
            <p className="muted">Outputs: {JSON.stringify(selectedStep.outputs)}</p>
          ) : null}
          {selectedStep.cost && Object.keys(selectedStep.cost).length > 0 ? (
            <p className="muted">Cost: {JSON.stringify(selectedStep.cost)}</p>
          ) : null}
          <p>Artifacts: {selectedStep.artifactCount}</p>
          {selectedStep.artifactRefs && selectedStep.artifactRefs.length > 0 ? (
            <ul className="copilot-question-list">
              {selectedStep.artifactRefs.map((ref, index) => (
                <li key={`${ref.type}-${ref.id}-${index}`}>
                  {ref.label ?? `${ref.type}: ${ref.id}`}
                </li>
              ))}
            </ul>
          ) : null}
          <p>Warnings: {selectedStep.warningCount}</p>
          {selectedStep.warningMessages && selectedStep.warningMessages.length > 0 ? (
            <ul className="copilot-question-list">
              {selectedStep.warningMessages.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          ) : null}
          <p>Errors: {selectedStep.errorCount}</p>
          {selectedStep.errorMessages && selectedStep.errorMessages.length > 0 ? (
            <ul className="copilot-question-list">
              {selectedStep.errorMessages.map((error, index) => (
                <li key={index}>{error}</li>
              ))}
            </ul>
          ) : null}
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

/**
 * FR-31a status panel for the run canvas.
 *
 * The panel shows the supervisor-side outcome (which can lag the
 * persisted ``status`` by one orchestrator step) and a fixed
 * ``executor_kind`` label so future durable executors (FR-31b+) are
 * visually distinguishable from in-process Phase 1 runs without
 * re-reading the URL or settings. ``cancel_requested`` surfaces the
 * intent-to-cancel state — important because the persisted row will
 * still report ``running`` until the orchestrator next yields.
 */
function AgenticRunStatusPanel({
  snapshot
}: {
  snapshot: WorkflowRunStatusView;
}) {
  const executorLabel =
    snapshot.executorKind === "inprocess"
      ? "In-process (Phase 1)"
      : snapshot.executorKind ?? "unknown";
  const outcomeLabel = snapshot.lastOutcome
    ? snapshot.lastOutcome.charAt(0).toUpperCase() + snapshot.lastOutcome.slice(1)
    : snapshot.supervisor.supervised
      ? "Pending first event"
      : "Not supervised";
  return (
    <aside
      className="agentic-status-panel"
      aria-label="Agentic run status"
      data-outcome={snapshot.lastOutcome ?? "pending"}
    >
      <dl>
        <div>
          <dt>Executor</dt>
          <dd>{executorLabel}</dd>
        </div>
        <div>
          <dt>Supervisor outcome</dt>
          <dd>{outcomeLabel}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{snapshot.status}</dd>
        </div>
        {snapshot.supervisor.cancelRequested ? (
          <div className="agentic-status-panel__cancel-flag">
            <dt>Cancellation</dt>
            <dd>Requested — waiting for next checkpoint</dd>
          </div>
        ) : null}
      </dl>
      {snapshot.errors.length > 0 ? (
        <details className="agentic-status-panel__errors">
          <summary>{snapshot.errors.length} error(s) recorded</summary>
          <ul>
            {snapshot.errors.map((message, index) => (
              <li key={`${index}-${message.slice(0, 24)}`}>{message}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </aside>
  );
}
