"use client";

import type { WorkspaceAsset } from "@/lib/product-api/types";
import { buildAssetContextMenu } from "./contextMenus/asset";
import { buildRunContextMenu } from "./contextMenus/run";
import type { ContextMenuState } from "./contextMenus/types";

interface AssetExplorerProps {
  assets: WorkspaceAsset[];
  onSelectAsset: (asset: WorkspaceAsset) => void;
  onOpenRun: (runId: string) => void;
  onOpenMenu: (menu: ContextMenuState) => void;
}

export function AssetExplorer({
  assets,
  onSelectAsset,
  onOpenRun,
  onOpenMenu
}: AssetExplorerProps) {
  return (
    <aside className="asset-explorer" aria-label="Workspace assets">
      <h1>Graph Analytics Workspace</h1>
      <p>Left-click selects. Right-click opens object actions.</p>

      <section className="asset-section">
        <h2>Assets</h2>
        <div className="asset-list">
          {assets.map((asset) => (
            <button
              className="asset-row"
              key={asset.id}
              type="button"
              onClick={() => onSelectAsset(asset)}
              onContextMenu={(event) => {
                event.preventDefault();
                const baseArgs = {
                  onViewInfo: () => onSelectAsset(asset),
                  onCopyId: () => void navigator.clipboard?.writeText(asset.id)
                };
                if (asset.kind !== "run") {
                  onOpenMenu({
                    x: event.clientX,
                    y: event.clientY,
                    items: buildAssetContextMenu(baseArgs)
                  });
                  return;
                }
                onOpenMenu({
                  x: event.clientX,
                  y: event.clientY,
                  items: buildRunContextMenu({
                    onViewPipeline: () => onOpenRun(asset.id),
                    onCopyRunId: baseArgs.onCopyId,
                    onRetryRun: () => onOpenRun(asset.id),
                    onDeleteRun: () => onSelectAsset(asset)
                  })
                });
              }}
            >
              <strong>{asset.label}</strong>
              <br />
              <span className="muted">{asset.description ?? asset.kind}</span>
            </button>
          ))}
        </div>
      </section>
    </aside>
  );
}
