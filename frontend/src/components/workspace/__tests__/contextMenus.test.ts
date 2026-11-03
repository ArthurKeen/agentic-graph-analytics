import { describe, expect, it } from "vitest";

import { buildAssetContextMenu } from "../contextMenus/asset";
import { buildCanvasContextMenu } from "../contextMenus/canvas";
import { buildConnectionProfileContextMenu } from "../contextMenus/connectionProfile";
import { buildDocumentContextMenu } from "../contextMenus/document";
import { buildGraphProfileContextMenu } from "../contextMenus/graphProfile";
import { buildPipelineStepContextMenu } from "../contextMenus/pipelineStep";
import { buildReportContextMenu } from "../contextMenus/report";
import { buildRequirementsContextMenu } from "../contextMenus/requirements";
import { buildRunContextMenu } from "../contextMenus/run";

function noop() {
  return undefined;
}

describe("workspace context menu builders", () => {
  it("builds canvas actions without page navigation", () => {
    const items = buildCanvasContextMenu({
      onCreateWorkspace: noop,
      onCreateConnectionProfile: noop,
      onCreateWorkflowRun: noop,
      onExportWorkspace: noop,
      onImportWorkspace: noop,
      onFitAll: noop,
      onCenterView: noop,
      onViewAsOperational: noop,
      onShowHelp: noop
    });

    expect(items.map((item) => item.id)).toEqual([
      "create-workspace",
      "create-connection-profile",
      "create-workflow-run",
      "import-workspace",
      "export-workspace",
      "view-operational",
      "fit-all",
      "center-view",
      "show-help"
    ]);
  });

  it("keeps each group contiguous", () => {
    // The sidebar renders the create and workspace groups as two separate
    // menus, and the context menu draws a rule between groups. Both rely on
    // items of a group sitting together; interleaving them would split a
    // menu in two without any test noticing.
    const items = buildCanvasContextMenu({
      onCreateWorkspace: noop,
      onEditWorkspace: noop,
      onArchiveWorkspace: noop,
      onCreateConnectionProfile: noop,
      onCreateWorkflowRun: noop,
      onExportWorkspace: noop,
      onImportWorkspace: noop,
      onUploadDocument: noop,
      onFitAll: noop,
      onCenterView: noop,
      onViewAsOperational: noop,
      onShowHelp: noop
    });

    const seen: string[] = [];
    for (const item of items) {
      const group = item.group ?? "ungrouped";
      if (seen[seen.length - 1] !== group) {
        expect(seen, `group ${group} appears in two blocks`).not.toContain(group);
        seen.push(group);
      }
    }
    expect(seen).toEqual(["create", "workspace", "view", "help"]);
  });

  it("includes Edit and Archive actions when the shell provides handlers", () => {
    // FR-1: Edit and Archive are conditional. The shell omits the handlers
    // when the workspace is missing or already archived; the builder must
    // not surface dead menu rows in those cases (covered by the test
    // above), and must surface them when handlers ARE provided.
    const items = buildCanvasContextMenu({
      onCreateWorkspace: noop,
      onEditWorkspace: noop,
      onArchiveWorkspace: noop,
      onCreateConnectionProfile: noop,
      onCreateWorkflowRun: noop,
      onExportWorkspace: noop,
      onImportWorkspace: noop,
      onFitAll: noop,
      onCenterView: noop,
      onViewAsOperational: noop,
      onShowHelp: noop
    });

    const ids = items.map((item) => item.id);
    expect(ids).toContain("edit-workspace");
    expect(ids).toContain("archive-workspace");
    // Both belong to the workspace group, which the sidebar renders as the
    // "Workspace" menu. They used to sit beside create-workspace; creating a
    // workspace and archiving the one you are in are different enough jobs
    // to belong in different menus.
    for (const id of ["edit-workspace", "archive-workspace", "export-workspace"]) {
      expect(items.find((item) => item.id === id)?.group).toBe("workspace");
    }
    // Archiving is destructive and must be styled as such on both surfaces.
    expect(items.find((item) => item.id === "archive-workspace")?.danger).toBe(true);
  });

  it("builds generic explorer asset actions", () => {
    const items = buildAssetContextMenu({
      onViewInfo: noop,
      onCopyId: noop
    });

    expect(items.map((item) => item.id)).toEqual(["view-info", "copy-id"]);
  });

  it("builds connection profile actions with verification", () => {
    const items = buildConnectionProfileContextMenu({
      onOpenInCanvas: noop,
      onVerifyConnection: noop,
      onDiscoverGraph: noop,
      onViewInfo: noop,
      onCopyId: noop,
      onDelete: noop
    });

    expect(items.map((item) => item.id)).toEqual([
      "open-in-canvas",
      "verify-connection",
      "discover-graph",
      "view-info",
      "copy-id",
      "delete-connection-profile"
    ]);
  });

  it("builds graph profile actions for canvas inspection", () => {
    const items = buildGraphProfileContextMenu({
      onOpenInCanvas: noop,
      onStartRequirementsCopilot: noop,
      onViewInfo: noop,
      onCopyId: noop,
      onDelete: noop
    });

    expect(items.map((item) => item.id)).toEqual([
      "open-in-canvas",
      "start-requirements-copilot",
      "view-info",
      "copy-id",
      "delete-graph-profile"
    ]);
  });

  it("offers Reopen Copilot from the consolidated Requirements asset", () => {
    // The Assets panel surfaces ONE Requirements row regardless of how many
    // RequirementVersion records exist; Reopen always targets the active
    // version. Per-version inspection (incl. read-only history) lives in the
    // canvas-side dropdown, not the right-click menu.
    const items = buildRequirementsContextMenu({
      onOpenInCanvas: noop,
      onReopenCopilot: noop,
      onViewInfo: noop,
      onCopyId: noop
    });
    expect(items.map((item) => item.id)).toEqual([
      "open-in-canvas",
      "reopen-requirements-copilot",
      "view-info",
      "copy-id"
    ]);
  });

  it("builds document actions for canvas inspection", () => {
    const items = buildDocumentContextMenu({
      onOpenInCanvas: noop,
      onViewInfo: noop,
      onCopyId: noop
    });

    expect(items.map((item) => item.id)).toEqual([
      "open-in-canvas",
      "view-info",
      "copy-id"
    ]);
  });

  it("builds run actions with retry and destructive delete", () => {
    const items = buildRunContextMenu({
      onViewPipeline: noop,
      onCopyRunId: noop,
      onStartRun: noop,
      onRetryRun: noop,
      onDeleteRun: noop
    });

    expect(items.find((item) => item.id === "start-run")).toBeDefined();
    expect(items.find((item) => item.id === "retry-run")).toBeDefined();
    expect(items.find((item) => item.id === "delete-run")?.danger).toBe(true);
  });

  it("builds report actions with publish", () => {
    const items = buildReportContextMenu({
      onViewReport: noop,
      onCopyReportId: noop,
      onPublishReport: noop
    });

    expect(items.map((item) => item.id)).toEqual([
      "view-report",
      "copy-report-id",
      "publish-report"
    ]);
  });

  it("builds pipeline step actions", () => {
    const items = buildPipelineStepContextMenu({
      onViewStepDetails: noop,
      onCopyError: noop,
      onViewRunResults: noop,
      onRetryRun: noop
    });

    expect(items.map((item) => item.id)).toContain("view-step-details");
    // Traditional / unspecified runs keep the retry option as before.
    expect(items.map((item) => item.id)).toContain("retry-run");
  });

  it("hides Retry Run on agentic runs because Phase 1 has no checkpointing", () => {
    // FR-31a Phase 1 (PRD v0.4): the agentic runner walks the
    // canonical six-step pipeline start to finish without checkpoint
    // persistence, so per-step retry is not yet meaningful. The
    // canvas surfaces a run-level Cancel + reissue-run flow instead.
    const items = buildPipelineStepContextMenu({
      onViewStepDetails: noop,
      onCopyError: noop,
      onViewRunResults: noop,
      onRetryRun: noop,
      isAgenticRun: true
    });

    const ids = items.map((item) => item.id);
    expect(ids).not.toContain("retry-run");
    // The other navigational actions are intentionally preserved on
    // agentic runs — only the action that needs a checkpoint is hidden.
    expect(ids).toEqual([
      "view-step-details",
      "copy-error",
      "view-run-results"
    ]);
  });

  it("labels the action Resume Run for a paused step (FR-30)", () => {
    // A paused step is resumed, not retried — same backend transition
    // (PAUSED -> RUNNING, no retry_count bump), but the wording matters.
    const items = buildPipelineStepContextMenu({
      onViewStepDetails: noop,
      onCopyError: noop,
      onViewRunResults: noop,
      onRetryRun: noop,
      stepStatus: "paused"
    });

    const action = items.find((item) => item.id === "resume-run");
    expect(action).toBeDefined();
    expect(action?.label).toBe("Resume Run");
    expect(items.map((item) => item.id)).not.toContain("retry-run");
  });

  it("keeps Retry Run wording for a failed step (FR-30)", () => {
    const items = buildPipelineStepContextMenu({
      onViewStepDetails: noop,
      onCopyError: noop,
      onViewRunResults: noop,
      onRetryRun: noop,
      stepStatus: "failed"
    });

    const action = items.find((item) => item.id === "retry-run");
    expect(action).toBeDefined();
    expect(action?.label).toBe("Retry Run");
    expect(items.map((item) => item.id)).not.toContain("resume-run");
  });
});
