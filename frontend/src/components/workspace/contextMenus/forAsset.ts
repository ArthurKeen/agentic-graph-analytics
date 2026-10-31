import type { WorkspaceAsset } from "@/lib/product-api/types";
import { buildAssetContextMenu } from "./asset";
import { buildConnectionProfileContextMenu } from "./connectionProfile";
import { buildDocumentContextMenu } from "./document";
import { buildGraphProfileContextMenu } from "./graphProfile";
import { buildReportContextMenu } from "./report";
import { buildRequirementsContextMenu } from "./requirements";
import { buildRunContextMenu } from "./run";
import type { ContextMenuItem } from "./types";

/** Every action an asset offers, in one place.
 *
 * This used to be inlined in the explorer's right-click handler, which made
 * the context menu the only thing that could render it. NFR-23 requires a
 * visible path as well, and two copies of "what can you do to a report"
 * would drift apart within a release. The action bar and the context menu
 * now call this, so adding an action surfaces it in both.
 */
export interface AssetMenuHandlers {
  onOpenInCanvas: (asset: WorkspaceAsset) => void;
  onViewInfo: (asset: WorkspaceAsset) => void;
  onCopyId: (asset: WorkspaceAsset) => void;
  onVerifyConnection: (asset: WorkspaceAsset) => void;
  onDiscoverGraph: (asset: WorkspaceAsset) => void;
  onDeleteConnectionProfile: (asset: WorkspaceAsset) => void;
  onStartCopilot: (asset: WorkspaceAsset) => void;
  onDeleteGraphProfile: (asset: WorkspaceAsset) => void;
  onReopenCopilot: (asset: WorkspaceAsset) => void;
  onStartRun: (asset: WorkspaceAsset) => void;
  onRetryRun: (asset: WorkspaceAsset) => void;
  onDeleteRun: (asset: WorkspaceAsset) => void;
  onViewReport: (asset: WorkspaceAsset) => void;
  onPublishReport: (asset: WorkspaceAsset) => void;
}

export function buildAssetMenuItems(
  asset: WorkspaceAsset,
  handlers: AssetMenuHandlers
): ContextMenuItem[] {
  const viewInfo = () => handlers.onViewInfo(asset);
  const copyId = () => handlers.onCopyId(asset);

  switch (asset.kind) {
    case "run":
      return buildRunContextMenu({
        onViewPipeline: () => handlers.onOpenInCanvas(asset),
        onCopyRunId: copyId,
        onStartRun: () => handlers.onStartRun(asset),
        onRetryRun: () => handlers.onRetryRun(asset),
        onDeleteRun: () => handlers.onDeleteRun(asset)
      });
    case "connection-profile":
      return buildConnectionProfileContextMenu({
        onOpenInCanvas: () => handlers.onOpenInCanvas(asset),
        onVerifyConnection: () => handlers.onVerifyConnection(asset),
        onDiscoverGraph: () => handlers.onDiscoverGraph(asset),
        onViewInfo: viewInfo,
        onCopyId: copyId,
        onDelete: () => handlers.onDeleteConnectionProfile(asset)
      });
    case "graph-profile":
      return buildGraphProfileContextMenu({
        onOpenInCanvas: () => handlers.onOpenInCanvas(asset),
        onStartRequirementsCopilot: () => handlers.onStartCopilot(asset),
        onViewInfo: viewInfo,
        onCopyId: copyId,
        onDelete: () => handlers.onDeleteGraphProfile(asset)
      });
    case "document":
      return buildDocumentContextMenu({
        onOpenInCanvas: () => handlers.onOpenInCanvas(asset),
        onViewInfo: viewInfo,
        onCopyId: copyId
      });
    case "report":
      return buildReportContextMenu({
        onViewReport: () => handlers.onViewReport(asset),
        onCopyReportId: copyId,
        onPublishReport: () => handlers.onPublishReport(asset)
      });
    case "requirements":
      return buildRequirementsContextMenu({
        onOpenInCanvas: () => handlers.onOpenInCanvas(asset),
        onReopenCopilot: () => handlers.onReopenCopilot(asset),
        onViewInfo: viewInfo,
        onCopyId: copyId
      });
    default:
      return buildAssetContextMenu({ onViewInfo: viewInfo, onCopyId: copyId });
  }
}

/** Actions that earn a visible button.
 *
 * Copy-to-clipboard and view-nudge items stay accelerator-only: NFR-23 asks
 * for the capabilities a requirement grants to be reachable, and "Copy ID"
 * grants none. Keeping them out is what stops the action bar turning into
 * the same undifferentiated list the canvas menu already is.
 */
const ACCELERATOR_ONLY = new Set([
  "copy-id",
  "copy-run-id",
  "copy-report-id",
  "copy-error",
  "fit-all",
  "center-view"
]);

export function visibleActions(items: ContextMenuItem[]): ContextMenuItem[] {
  return items.filter((item) => !ACCELERATOR_ONLY.has(item.id));
}
