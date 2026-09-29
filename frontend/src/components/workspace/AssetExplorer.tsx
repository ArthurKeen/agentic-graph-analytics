"use client";

import { useMemo, useState } from "react";

import type { WorkspaceAsset, WorkspaceHealth } from "@/lib/product-api/types";
import { buildAssetContextMenu } from "./contextMenus/asset";
import { buildConnectionProfileContextMenu } from "./contextMenus/connectionProfile";
import { buildDocumentContextMenu } from "./contextMenus/document";
import { buildGraphProfileContextMenu } from "./contextMenus/graphProfile";
import { buildReportContextMenu } from "./contextMenus/report";
import { buildRequirementsContextMenu } from "./contextMenus/requirements";
import { buildRunContextMenu } from "./contextMenus/run";
import type { ContextMenuState } from "./contextMenus/types";

/** Sidebar groups, in reading order.
 *
 * Grouped by the role an object plays rather than by its type. The flat list
 * this replaces mixed setup objects, inputs, outputs and admin panels as
 * equals, so ten reports pushed the connection you needed off-screen and two
 * empty admin canvases sat among real content looking equally significant.
 *
 * "Analysing" is first and never hidden: "what am I pointed at" was the
 * question asked most often, and it was previously answerable only from a
 * dropdown embedded in the status banner.
 */
const GROUPS: Array<{
  key: AssetGroupKey;
  title: string;
  hint?: string;
  empty: string;
  collapsible?: boolean;
  alwaysShow?: boolean;
}> = [
  {
    key: "analysing",
    title: "Analysing",
    empty: "No active graph yet — discover one from a database below.",
    alwaysShow: true
  },
  { key: "results", title: "Results", empty: "No runs or reports yet." },
  { key: "inputs", title: "Inputs", empty: "No requirements or documents yet." },
  {
    key: "setup",
    title: "Setup",
    empty: "Nothing configured yet.",
    collapsible: true
  }
];

type AssetGroupKey = "analysing" | "results" | "inputs" | "setup";

/** Which group an asset belongs to. The active graph profile is promoted out
 * of Setup into Analysing; every other profile stays configuration. */
function groupOf(asset: WorkspaceAsset, activeGraphProfileId: string | null): AssetGroupKey {
  switch (asset.kind) {
    case "graph-profile":
      return asset.id === activeGraphProfileId ? "analysing" : "setup";
    case "run":
    case "report":
      return "results";
    case "requirements":
    case "document":
      return "inputs";
    default:
      // connection-profile, analysis-catalog, use-cases, retention
      return "setup";
  }
}

interface AssetExplorerProps {
  assets: WorkspaceAsset[];
  health: WorkspaceHealth | null;
  auditEvents: Array<Record<string, unknown>>;
  onSelectAsset: (asset: WorkspaceAsset) => void;
  onOpenConnectionProfile: (connectionProfileId: string) => void;
  onVerifyConnectionProfile: (connectionProfileId: string) => void;
  onRequestDeleteConnectionProfile: (asset: WorkspaceAsset) => void;
  onRequestDeleteGraphProfile: (asset: WorkspaceAsset) => void;
  onRequestDiscoverGraph: (asset: WorkspaceAsset) => void;
  onOpenDocument: (documentId: string) => void;
  onOpenGraphProfile: (graphProfileId: string) => void;
  onRequestStartRequirementsCopilot: (asset: WorkspaceAsset) => void;
  /** Reopen the Requirements Copilot pre-populated from the workspace's active
   * RequirementVersion. The Assets panel surfaces ONE consolidated
   * "Requirements" row, so this handler always implies "reopen from active";
   * the shell resolves the active version id from its own state. */
  onRequestReopenRequirementsCopilot: (asset: WorkspaceAsset) => void;
  onRequestAssetInfo: (asset: WorkspaceAsset) => void;
  onOpenRun: (runId: string) => void;
  onStartRun: (asset: WorkspaceAsset) => void;
  onOpenReport: (reportId: string) => void;
  onRequestPublishReport: (asset: WorkspaceAsset) => void;
  onRequestDeleteRun: (asset: WorkspaceAsset) => void;
  onOpenMenu: (menu: ContextMenuState) => void;
  /** Primary "where do I start" actions surfaced at the top of the panel. */
  onRequestConnectDatabase: () => void;
  /** Three analysis modes (fast → comprehensive). */
  onRequestQuickAnalysis: () => void;
  onRequestGuidedAnalysis: () => void;
  onRequestDetailedAnalysis: () => void;
  /** Whether the workspace has at least one graph profile (gates the three
   * analysis modes, which need a graph to run against). */
  hasGraphProfile: boolean;
  /** Which graph profile the workspace is pointed at, so it can be promoted
   * out of Setup into its own group. */
  activeGraphProfileId: string | null;
}

export function AssetExplorer({
  assets,
  health,
  auditEvents,
  onSelectAsset,
  onOpenConnectionProfile,
  onVerifyConnectionProfile,
  onRequestDeleteConnectionProfile,
  onRequestDeleteGraphProfile,
  onRequestDiscoverGraph,
  onOpenDocument,
  onOpenGraphProfile,
  onRequestStartRequirementsCopilot,
  onRequestReopenRequirementsCopilot,
  onRequestAssetInfo,
  onOpenRun,
  onStartRun,
  onOpenReport,
  onRequestPublishReport,
  onRequestDeleteRun,
  onOpenMenu,
  onRequestConnectDatabase,
  onRequestQuickAnalysis,
  onRequestGuidedAnalysis,
  onRequestDetailedAnalysis,
  hasGraphProfile,
  activeGraphProfileId
}: AssetExplorerProps) {
  // Setup collapses once the workspace is set up, because it is configuration
  // consulted occasionally and it holds the two empty admin canvases that used
  // to sit among results looking equally significant.
  //
  // But it starts OPEN while there is no active graph, because that is where
  // "Discover graph" lives — the step that unblocks everything else. Collapsing
  // it for a new workspace would hide the only way forward, which is the same
  // dead end as the disabled analysis buttons.
  // Only explicit user choices live in state. The default is derived at render
  // time because the workspace loads AFTER first render: initialising from
  // activeGraphProfileId captured it while still null, so Setup opened and
  // stayed open forever.
  const [groupOverrides, setGroupOverrides] = useState<
    Partial<Record<AssetGroupKey, boolean>>
  >({});
  const isGroupOpen = (key: AssetGroupKey) =>
    groupOverrides[key] ?? (key === "setup" ? activeGraphProfileId === null : true);

  const grouped = useMemo(() => {
    const buckets: Record<AssetGroupKey, WorkspaceAsset[]> = {
      analysing: [],
      results: [],
      inputs: [],
      setup: []
    };
    for (const asset of assets) {
      buckets[groupOf(asset, activeGraphProfileId)].push(asset);
    }
    return buckets;
  }, [assets, activeGraphProfileId]);

  const handlers: RowHandlers = {
    onDiscoverGraph: onRequestDiscoverGraph,
    onVerifyConnection: onVerifyConnectionProfile,
    onStartCopilot: onRequestStartRequirementsCopilot,
    onReopenCopilot: onRequestReopenRequirementsCopilot,
    onStartRun: onStartRun,
    onPublishReport: onRequestPublishReport
  };

  /** Full action set, still on right-click. Unchanged behaviour — only the
   * dispatch moved out of the row so the row could carry its own buttons. */
  const openContextMenu = (asset: WorkspaceAsset, event: React.MouseEvent) => {
    event.preventDefault();
    const openInfo = () => {
      onSelectAsset(asset);
      onRequestAssetInfo(asset);
    };
    const copyId = () => void navigator.clipboard?.writeText(asset.id);
    const at = { x: event.clientX, y: event.clientY };

    if (asset.kind === "run") {
      onOpenMenu({
        ...at,
        items: buildRunContextMenu({
          onViewPipeline: () => onOpenRun(asset.id),
          onCopyRunId: copyId,
          onStartRun: () => onStartRun(asset),
          onRetryRun: () => onOpenRun(asset.id),
          onDeleteRun: () => onRequestDeleteRun(asset)
        })
      });
      return;
    }
    if (asset.kind === "connection-profile") {
      onOpenMenu({
        ...at,
        items: buildConnectionProfileContextMenu({
          onOpenInCanvas: () => onOpenConnectionProfile(asset.id),
          onVerifyConnection: () => onVerifyConnectionProfile(asset.id),
          onDiscoverGraph: () => onRequestDiscoverGraph(asset),
          onViewInfo: openInfo,
          onCopyId: copyId,
          onDelete: () => onRequestDeleteConnectionProfile(asset)
        })
      });
      return;
    }
    if (asset.kind === "graph-profile") {
      onOpenMenu({
        ...at,
        items: buildGraphProfileContextMenu({
          onOpenInCanvas: () => onOpenGraphProfile(asset.id),
          onStartRequirementsCopilot: () => onRequestStartRequirementsCopilot(asset),
          onViewInfo: openInfo,
          onCopyId: copyId,
          onDelete: () => onRequestDeleteGraphProfile(asset)
        })
      });
      return;
    }
    if (asset.kind === "document") {
      onOpenMenu({
        ...at,
        items: buildDocumentContextMenu({
          onOpenInCanvas: () => onOpenDocument(asset.id),
          onViewInfo: openInfo,
          onCopyId: copyId
        })
      });
      return;
    }
    if (asset.kind === "report") {
      onOpenMenu({
        ...at,
        items: buildReportContextMenu({
          onViewReport: () => onOpenReport(asset.id),
          onCopyReportId: copyId,
          onPublishReport: () => onRequestPublishReport(asset)
        })
      });
      return;
    }
    if (asset.kind === "requirements") {
      onOpenMenu({
        ...at,
        items: buildRequirementsContextMenu({
          onOpenInCanvas: () => onSelectAsset(asset),
          onReopenCopilot: () => onRequestReopenRequirementsCopilot(asset),
          onViewInfo: openInfo,
          onCopyId: copyId
        })
      });
      return;
    }
    onOpenMenu({ ...at, items: buildAssetContextMenu({ onViewInfo: openInfo, onCopyId: copyId }) });
  };

  return (
    <aside className="asset-explorer" aria-label="Workspace assets">
      <div className="workspace-brand">
        {/* Two variants: the stock logo has a white wordmark, which is
            invisible on the light canvas. The -light file recolours only the
            white ink to body-text grey, leaving the avocado and sparkle
            untouched. CSS shows exactly one per theme. */}
        <img
          className="workspace-brand-logo workspace-brand-logo--on-light"
          src="/arango-logo-light.png"
          alt="Arango"
          width={343}
          height={76}
        />
        <img
          className="workspace-brand-logo workspace-brand-logo--on-dark"
          src="/arango-logo.png"
          alt=""
          aria-hidden="true"
          width={343}
          height={76}
        />
        <div>
          <h1>Graph Analytics Workspace</h1>
        </div>
      </div>

      <section className="setup-actions" aria-label="Setup">
        <span className="actions-label">Setup</span>
        <button
          type="button"
          className="primary-button"
          onClick={onRequestConnectDatabase}
        >
          Connect to Database
        </button>
      </section>

      <section className="analyze-actions" aria-label="Analyze">
        <span className="actions-label">Analyze</span>
        <button
          type="button"
          className="analyze-mode-button"
          disabled={!hasGraphProfile}
          title={
            hasGraphProfile
              ? "Ask one question in plain English, get one report — no approvals"
              : "Connect to a database and discover a graph first"
          }
          onClick={onRequestQuickAnalysis}
        >
          <strong>Quick Analysis</strong>
          <span className="muted">One prompt → one report. Fast, no setup.</span>
        </button>
        <button
          type="button"
          className="analyze-mode-button"
          disabled={!hasGraphProfile}
          title={
            hasGraphProfile
              ? "Answer a few questions; we build the requirements, then analyze"
              : "Connect to a database and discover a graph first"
          }
          onClick={onRequestGuidedAnalysis}
        >
          <strong>Guided Analysis</strong>
          <span className="muted">Copilot interview → focused analysis.</span>
        </button>
        <button
          type="button"
          className="analyze-mode-button"
          disabled={!hasGraphProfile}
          title={
            hasGraphProfile
              ? "Full study from complete business requirements (multiple use cases)"
              : "Connect to a database and discover a graph first"
          }
          onClick={onRequestDetailedAnalysis}
        >
          <strong>Detailed Analysis</strong>
          <span className="muted">Full requirements → many use cases & reports.</span>
        </button>
      </section>

      {GROUPS.map((group) => {
        const rows = grouped[group.key];
        if (rows.length === 0 && !group.alwaysShow) {
          return null;
        }
        const collapsed = group.collapsible && !isGroupOpen(group.key);
        return (
          <section className="asset-section" key={group.key}>
            {group.collapsible ? (
              <button
                type="button"
                className="asset-group-toggle"
                aria-expanded={!collapsed}
                onClick={() =>
                  setGroupOverrides((current) => ({
                    ...current,
                    [group.key]: !isGroupOpen(group.key)
                  }))
                }
              >
                <span aria-hidden="true">{collapsed ? "\u25b8" : "\u25be"}</span>
                <h2>{group.title}</h2>
                <span className="muted">{rows.length}</span>
              </button>
            ) : (
              <div className="asset-group-head">
                <h2>{group.title}</h2>
                {group.hint ? <span className="muted">{group.hint}</span> : null}
              </div>
            )}
            {collapsed ? null : rows.length === 0 ? (
              <p className="muted asset-group-empty">{group.empty}</p>
            ) : (
              <div className="asset-list">
                {rows.map((asset) => (
                  <AssetRow
                    key={asset.id}
                    asset={asset}
                    actions={primaryActions(asset, handlers)}
                    onSelect={() => onSelectAsset(asset)}
                    onContextMenu={(event) => openContextMenu(asset, event)}
                  />
                ))}
              </div>
            )}
          </section>
        );
      })}

      {/* Status, not navigation. Below the groups so "what am I analysing"
          is the first thing in the panel rather than a screen down. */}
      <WorkspaceHealthSummary health={health} />
      <RecentAuditEvents events={auditEvents} />
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

/** A row's one or two most useful actions, shown on the row itself.
 *
 * Every one of these already existed — reachable only by right-clicking the
 * correct object, which is why 32 actions were effectively undiscoverable.
 * Right-click still offers the full set; this is the visible path for the
 * verbs people actually reach for. Deliberately capped at two: a row with
 * five buttons is its own kind of unreadable.
 */
function primaryActions(
  asset: WorkspaceAsset,
  handlers: RowHandlers
): RowAction[] {
  switch (asset.kind) {
    case "connection-profile":
      return [
        // The step that unblocks everything else: without a graph profile the
        // database cannot be analysed or selected.
        { label: "Discover graph", onClick: () => handlers.onDiscoverGraph(asset) },
        { label: "Verify", onClick: () => handlers.onVerifyConnection(asset.id) }
      ];
    case "graph-profile":
      return [
        { label: "Start copilot", onClick: () => handlers.onStartCopilot(asset) }
      ];
    case "requirements":
      return [
        { label: "Reopen copilot", onClick: () => handlers.onReopenCopilot(asset) }
      ];
    case "run":
      return [{ label: "Start", onClick: () => handlers.onStartRun(asset) }];
    case "report":
      return [{ label: "Publish", onClick: () => handlers.onPublishReport(asset) }];
    default:
      return [];
  }
}

interface RowAction {
  label: string;
  onClick: () => void;
}

interface RowHandlers {
  onDiscoverGraph: (asset: WorkspaceAsset) => void;
  onVerifyConnection: (connectionProfileId: string) => void;
  onStartCopilot: (asset: WorkspaceAsset) => void;
  onReopenCopilot: (asset: WorkspaceAsset) => void;
  onStartRun: (asset: WorkspaceAsset) => void;
  onPublishReport: (asset: WorkspaceAsset) => void;
}

/** One asset row: a select target plus its visible actions.
 *
 * The row used to be a single <button>, which is why the actions could not
 * live on it — nesting a button inside a button is invalid. The wrapper is now
 * a div carrying the context menu, with the label as the button so click and
 * keyboard selection behave as before.
 */
function AssetRow({
  asset,
  actions,
  onSelect,
  onContextMenu
}: {
  asset: WorkspaceAsset;
  actions: RowAction[];
  onSelect: () => void;
  onContextMenu: (event: React.MouseEvent) => void;
}) {
  return (
    <div className="asset-row" onContextMenu={onContextMenu}>
      <button type="button" className="asset-row-main" onClick={onSelect}>
        <strong>{asset.label}</strong>
        <span className="muted">{asset.description ?? asset.kind}</span>
      </button>
      {actions.length > 0 ? (
        <div className="asset-row-actions">
          {actions.map((action) => (
            <button
              key={action.label}
              type="button"
              className="asset-row-action"
              onClick={(event) => {
                // The wrapper is not a button, but the canvas listens for
                // clicks to dismiss menus; keep the action from selecting too.
                event.stopPropagation();
                action.onClick();
              }}
            >
              {action.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
