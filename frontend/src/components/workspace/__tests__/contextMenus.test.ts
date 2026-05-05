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
      "export-workspace",
      "import-workspace",
      "view-operational",
      "fit-all",
      "center-view",
      "show-help"
    ]);
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
    // Edit/archive should appear next to the create-workspace entry so the
    // workspace lifecycle actions stay visually grouped at the top.
    expect(ids.indexOf("edit-workspace")).toBe(ids.indexOf("create-workspace") + 1);
    expect(ids.indexOf("archive-workspace")).toBe(ids.indexOf("edit-workspace") + 1);
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
      onCopyId: noop
    });

    expect(items.map((item) => item.id)).toEqual([
      "open-in-canvas",
      "verify-connection",
      "discover-graph",
      "view-info",
      "copy-id"
    ]);
  });

  it("builds graph profile actions for canvas inspection", () => {
    const items = buildGraphProfileContextMenu({
      onOpenInCanvas: noop,
      onStartRequirementsCopilot: noop,
      onViewInfo: noop,
      onCopyId: noop
    });

    expect(items.map((item) => item.id)).toEqual([
      "open-in-canvas",
      "start-requirements-copilot",
      "view-info",
      "copy-id"
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
  });
});
