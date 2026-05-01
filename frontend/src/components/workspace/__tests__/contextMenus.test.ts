import { describe, expect, it } from "vitest";

import { buildAssetContextMenu } from "../contextMenus/asset";
import { buildCanvasContextMenu } from "../contextMenus/canvas";
import { buildPipelineStepContextMenu } from "../contextMenus/pipelineStep";
import { buildReportContextMenu } from "../contextMenus/report";
import { buildRunContextMenu } from "../contextMenus/run";

function noop() {
  return undefined;
}

describe("workspace context menu builders", () => {
  it("builds canvas actions without page navigation", () => {
    const items = buildCanvasContextMenu({
      onFitAll: noop,
      onCenterView: noop,
      onViewAsOperational: noop,
      onShowHelp: noop
    });

    expect(items.map((item) => item.id)).toEqual([
      "view-operational",
      "fit-all",
      "center-view",
      "show-help"
    ]);
  });

  it("builds generic explorer asset actions", () => {
    const items = buildAssetContextMenu({
      onViewInfo: noop,
      onCopyId: noop
    });

    expect(items.map((item) => item.id)).toEqual(["view-info", "copy-id"]);
  });

  it("builds run actions with retry and destructive delete", () => {
    const items = buildRunContextMenu({
      onViewPipeline: noop,
      onCopyRunId: noop,
      onRetryRun: noop,
      onDeleteRun: noop
    });

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
