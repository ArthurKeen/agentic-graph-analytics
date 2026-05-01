"use client";

import type { WorkspaceAsset, WorkspaceHealth } from "@/lib/product-api/types";
import { buildAssetContextMenu } from "./contextMenus/asset";
import { buildReportContextMenu } from "./contextMenus/report";
import { buildRunContextMenu } from "./contextMenus/run";
import type { ContextMenuState } from "./contextMenus/types";

interface AssetExplorerProps {
  assets: WorkspaceAsset[];
  health: WorkspaceHealth | null;
  onSelectAsset: (asset: WorkspaceAsset) => void;
  onOpenRun: (runId: string) => void;
  onOpenReport: (reportId: string) => void;
  onRequestPublishReport: (asset: WorkspaceAsset) => void;
  onRequestDeleteRun: (asset: WorkspaceAsset) => void;
  onOpenMenu: (menu: ContextMenuState) => void;
}

export function AssetExplorer({
  assets,
  health,
  onSelectAsset,
  onOpenRun,
  onOpenReport,
  onRequestPublishReport,
  onRequestDeleteRun,
  onOpenMenu
}: AssetExplorerProps) {
  return (
    <aside className="asset-explorer" aria-label="Workspace assets">
      <h1>Graph Analytics Workspace</h1>
      <p>Left-click selects. Right-click opens object actions.</p>
      <WorkspaceHealthSummary health={health} />

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
                  if (asset.kind === "report") {
                    onOpenMenu({
                      x: event.clientX,
                      y: event.clientY,
                      items: buildReportContextMenu({
                        onViewReport: () => onOpenReport(asset.id),
                        onCopyReportId: baseArgs.onCopyId,
                        onPublishReport: () => onRequestPublishReport(asset)
                      })
                    });
                    return;
                  }
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
                    onDeleteRun: () => onRequestDeleteRun(asset)
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

function WorkspaceHealthSummary({ health }: { health: WorkspaceHealth | null }) {
  if (!health) {
    return (
      <section className="health-card" aria-label="Workspace health">
        <strong>Workspace Health</strong>
        <p className="muted">Load a workspace to see readiness checks.</p>
      </section>
    );
  }

  const issueCount = health.issues.length;
  const statusLabel = health.status === "healthy" ? "Healthy" : "Needs attention";

  return (
    <section className="health-card" data-status={health.status} aria-label="Workspace health">
      <div className="health-card-header">
        <strong>Workspace Health</strong>
        <span>{statusLabel}</span>
      </div>
      <p className="muted">
        {issueCount === 0 ? "No setup issues detected." : `${issueCount} issue${issueCount === 1 ? "" : "s"} detected.`}
      </p>
      {health.issues.length > 0 ? (
        <ul>
          {health.issues.slice(0, 3).map((issue) => (
            <li key={issue.code}>
              <span data-severity={issue.severity}>{issue.severity}</span> {issue.message}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
