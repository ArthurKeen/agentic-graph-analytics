"use client";

import type { WorkspaceAsset, WorkspaceHealth } from "@/lib/product-api/types";
import { buildAssetContextMenu } from "./contextMenus/asset";
import { buildConnectionProfileContextMenu } from "./contextMenus/connectionProfile";
import { buildDocumentContextMenu } from "./contextMenus/document";
import { buildGraphProfileContextMenu } from "./contextMenus/graphProfile";
import { buildReportContextMenu } from "./contextMenus/report";
import { buildRunContextMenu } from "./contextMenus/run";
import type { ContextMenuState } from "./contextMenus/types";

interface AssetExplorerProps {
  assets: WorkspaceAsset[];
  health: WorkspaceHealth | null;
  auditEvents: Array<Record<string, unknown>>;
  onSelectAsset: (asset: WorkspaceAsset) => void;
  onOpenConnectionProfile: (connectionProfileId: string) => void;
  onVerifyConnectionProfile: (connectionProfileId: string) => void;
  onRequestDiscoverGraph: (asset: WorkspaceAsset) => void;
  onOpenDocument: (documentId: string) => void;
  onOpenGraphProfile: (graphProfileId: string) => void;
  onRequestStartRequirementsCopilot: (asset: WorkspaceAsset) => void;
  onOpenRun: (runId: string) => void;
  onStartRun: (asset: WorkspaceAsset) => void;
  onOpenReport: (reportId: string) => void;
  onRequestPublishReport: (asset: WorkspaceAsset) => void;
  onRequestDeleteRun: (asset: WorkspaceAsset) => void;
  onOpenMenu: (menu: ContextMenuState) => void;
}

export function AssetExplorer({
  assets,
  health,
  auditEvents,
  onSelectAsset,
  onOpenConnectionProfile,
  onVerifyConnectionProfile,
  onRequestDiscoverGraph,
  onOpenDocument,
  onOpenGraphProfile,
  onRequestStartRequirementsCopilot,
  onOpenRun,
  onStartRun,
  onOpenReport,
  onRequestPublishReport,
  onRequestDeleteRun,
  onOpenMenu
}: AssetExplorerProps) {
  return (
    <aside className="asset-explorer" aria-label="Workspace assets">
      <div className="workspace-brand">
        <img
          className="workspace-brand-logo"
          src="/arango-logo.png"
          alt="Arango"
          width={343}
          height={76}
        />
        <div>
          <h1>Graph Analytics Workspace</h1>
        </div>
      </div>
      <p>Left-click selects. Right-click opens object actions.</p>
      <WorkspaceHealthSummary health={health} />
      <RecentAuditEvents events={auditEvents} />

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
                  if (asset.kind === "connection-profile") {
                    onOpenMenu({
                      x: event.clientX,
                      y: event.clientY,
                      items: buildConnectionProfileContextMenu({
                        onOpenInCanvas: () => onOpenConnectionProfile(asset.id),
                        onVerifyConnection: () => onVerifyConnectionProfile(asset.id),
                        onDiscoverGraph: () => onRequestDiscoverGraph(asset),
                        onViewInfo: () => onSelectAsset(asset),
                        onCopyId: baseArgs.onCopyId
                      })
                    });
                    return;
                  }
                  if (asset.kind === "document") {
                    onOpenMenu({
                      x: event.clientX,
                      y: event.clientY,
                      items: buildDocumentContextMenu({
                        onOpenInCanvas: () => onOpenDocument(asset.id),
                        onViewInfo: () => onSelectAsset(asset),
                        onCopyId: baseArgs.onCopyId
                      })
                    });
                    return;
                  }
                  if (asset.kind === "graph-profile") {
                    onOpenMenu({
                      x: event.clientX,
                      y: event.clientY,
                      items: buildGraphProfileContextMenu({
                        onOpenInCanvas: () => onOpenGraphProfile(asset.id),
                        onStartRequirementsCopilot: () =>
                          onRequestStartRequirementsCopilot(asset),
                        onViewInfo: () => onSelectAsset(asset),
                        onCopyId: baseArgs.onCopyId
                      })
                    });
                    return;
                  }
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
                    onStartRun: () => onStartRun(asset),
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

function RecentAuditEvents({ events }: { events: Array<Record<string, unknown>> }) {
  return (
    <section className="health-card" aria-label="Recent audit activity">
      <div className="health-card-header">
        <strong>Recent Activity</strong>
        <span>{events.length} events</span>
      </div>
      {events.length === 0 ? (
        <p className="muted">No audit events loaded for this workspace.</p>
      ) : (
        <ul>
          {events.slice(0, 4).map((event, index) => (
            <li key={String(event.audit_event_id ?? event.event_id ?? index)}>
              <span>{String(event.action ?? event.type ?? "event")}</span>{" "}
              {String(event.entity_id ?? event.target_id ?? event.actor ?? "workspace")}
            </li>
          ))}
        </ul>
      )}
    </section>
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
