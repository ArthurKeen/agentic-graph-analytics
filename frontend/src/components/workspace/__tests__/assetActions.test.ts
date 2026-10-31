import { describe, expect, it, vi } from "vitest";
import type { WorkspaceAsset } from "@/lib/product-api/types";
import {
  buildAssetMenuItems,
  visibleActions
} from "../contextMenus/forAsset";
import type { AssetMenuHandlers } from "../contextMenus/forAsset";

/** NFR-23: a capability a user cannot find is not delivered.
 *
 * The canvas action bar and the right-click menu both render
 * buildAssetMenuItems. These tests pin the property that makes that
 * worth doing: an action added for one surface appears on both, and the
 * only things kept off the visible surface are the ones that grant no
 * capability.
 */

const handlers: AssetMenuHandlers = {
  onOpenInCanvas: vi.fn(),
  onViewInfo: vi.fn(),
  onCopyId: vi.fn(),
  onVerifyConnection: vi.fn(),
  onDiscoverGraph: vi.fn(),
  onDeleteConnectionProfile: vi.fn(),
  onStartCopilot: vi.fn(),
  onDeleteGraphProfile: vi.fn(),
  onReopenCopilot: vi.fn(),
  onStartRun: vi.fn(),
  onRetryRun: vi.fn(),
  onDeleteRun: vi.fn(),
  onViewReport: vi.fn(),
  onPublishReport: vi.fn()
};

const KINDS: WorkspaceAsset["kind"][] = [
  "run",
  "connection-profile",
  "graph-profile",
  "document",
  "report",
  "requirements"
];

function asset(kind: WorkspaceAsset["kind"]): WorkspaceAsset {
  return { id: `${kind}-1`, kind, label: kind, description: "" };
}

describe("asset actions", () => {
  it.each(KINDS)("%s offers at least one action a user can see", (kind) => {
    const items = buildAssetMenuItems(asset(kind), handlers);

    expect(items.length).toBeGreaterThan(0);
    expect(visibleActions(items).length).toBeGreaterThan(0);
  });

  it("keeps clipboard helpers off the visible surface", () => {
    const items = buildAssetMenuItems(asset("run"), handlers);

    expect(items.map((item) => item.id)).toContain("copy-run-id");
    expect(visibleActions(items).map((item) => item.id)).not.toContain(
      "copy-run-id"
    );
  });

  it("keeps every action that grants a capability", () => {
    // The list the three open drift alerts are about. Each must survive the
    // visible-action filter, or the filter has become the new hiding place.
    const granted = [
      ["connection-profile", "delete-connection-profile"],
      ["connection-profile", "discover-graph"],
      ["connection-profile", "verify-connection"],
      ["graph-profile", "delete-graph-profile"],
      ["graph-profile", "start-requirements-copilot"],
      ["run", "start-run"],
      ["run", "delete-run"],
      ["report", "publish-report"]
    ] as const;

    for (const [kind, id] of granted) {
      const visible = visibleActions(
        buildAssetMenuItems(asset(kind), handlers)
      ).map((item) => item.id);
      expect(visible, `${kind} must surface ${id}`).toContain(id);
    }
  });

  it("marks destructive actions so the action bar can style them", () => {
    const items = buildAssetMenuItems(asset("connection-profile"), handlers);
    const remove = items.find((item) => item.id === "delete-connection-profile");

    expect(remove?.danger).toBe(true);
  });

  it("routes a clicked action to its handler", () => {
    const onPublishReport = vi.fn();
    const items = buildAssetMenuItems(asset("report"), {
      ...handlers,
      onPublishReport
    });

    items.find((item) => item.id === "publish-report")?.onSelect();

    expect(onPublishReport).toHaveBeenCalledOnce();
  });

  it("carries no emoji in its labels", () => {
    // Labels are the whole affordance now that icons are not rendered.
    const emoji = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]/u;

    for (const kind of KINDS) {
      for (const item of buildAssetMenuItems(asset(kind), handlers)) {
        expect(emoji.test(item.label), `${item.label}`).toBe(false);
      }
    }
  });
});
