"use client";

import { useMemo } from "react";
import type { RequirementVersion } from "@/lib/product-api/types";
import { MarkdownView } from "./MarkdownView";

interface RequirementVersionCanvasProps {
  /** All RequirementVersion records visible in this workspace, in any order.
   * The canvas computes the active (most-recent APPROVED) version itself and
   * sorts the dropdown by version desc. Empty list is a programmer error —
   * the consolidated `requirements` asset should not be rendered if no
   * versions exist. */
  versions: RequirementVersion[];
  /** ID of the version to display. When `null`, the canvas defaults to the
   * active (most-recent APPROVED) version. URL deep-links pass an explicit
   * id; the dropdown calls back via `onSelectVersion` to change it. */
  selectedVersionId: string | null;
  isStartingRequirementsCopilot: boolean;
  onSelectVersion: (versionId: string | null) => void;
  /** Reopen the Copilot using `basedOnVersionId` (always the ACTIVE version
   * regardless of what's currently being viewed — historical-mode UI calls
   * "Return to active" before exposing reopen). */
  onReopenCopilot: (basedOnVersionId: string) => void;
}

export function RequirementVersionCanvas({
  versions,
  selectedVersionId,
  isStartingRequirementsCopilot,
  onSelectVersion,
  onReopenCopilot
}: RequirementVersionCanvasProps) {
  const sortedVersions = useMemo(
    () => [...versions].sort((a, b) => b.version - a.version),
    [versions]
  );
  const activeVersion = useMemo(
    () =>
      sortedVersions.find((version) => version.status === "approved") ??
      sortedVersions[0] ??
      null,
    [sortedVersions]
  );
  const displayedVersion = useMemo(() => {
    if (selectedVersionId) {
      const exact = sortedVersions.find(
        (version) => version.requirementVersionId === selectedVersionId
      );
      if (exact) {
        return exact;
      }
    }
    return activeVersion;
  }, [activeVersion, selectedVersionId, sortedVersions]);

  if (!displayedVersion || !activeVersion) {
    return (
      <section
        className="requirement-version-canvas"
        aria-label="Requirements"
      >
        <p className="muted">No requirement versions exist for this workspace yet.</p>
      </section>
    );
  }

  const isViewingActive =
    displayedVersion.requirementVersionId === activeVersion.requirementVersionId;
  const status = displayedVersion.status;
  const statusLabel = status.replace("_", " ");
  const approvedAt = displayedVersion.approvedAt
    ? new Date(displayedVersion.approvedAt).toLocaleString()
    : null;
  const basedOnVersion = displayedVersion.metadata?.based_on_version;
  const supersededAt = displayedVersion.metadata?.superseded_at;
  const supersededBy = displayedVersion.metadata?.superseded_by;

  return (
    <section
      className="requirement-version-canvas"
      aria-label="Requirements"
    >
      <header>
        <div>
          <p className="muted">Requirements</p>
          <h3>Requirements</h3>
          <div className="requirement-version-selector">
            <label htmlFor="requirement-version-select" className="muted">
              Version
            </label>
            <select
              id="requirement-version-select"
              value={displayedVersion.requirementVersionId}
              onChange={(event) => {
                const next = event.target.value;
                // Selecting the active version "anchors" the canvas back to
                // null so subsequent approvals (which advance the active id)
                // automatically follow without forcing the user to re-pick.
                onSelectVersion(
                  next === activeVersion.requirementVersionId ? null : next
                );
              }}
            >
              {sortedVersions.map((version) => {
                const isActive =
                  version.requirementVersionId ===
                  activeVersion.requirementVersionId;
                return (
                  <option
                    key={version.requirementVersionId}
                    value={version.requirementVersionId}
                  >
                    v{version.version} ({version.status})
                    {isActive ? " · active" : ""}
                  </option>
                );
              })}
            </select>
          </div>
          {basedOnVersion ? (
            <p className="muted">
              Based on v{String(basedOnVersion)}
            </p>
          ) : null}
        </div>
        <div className="requirement-version-header-actions">
          <span data-status={status}>{statusLabel}</span>
          {isViewingActive ? (
            <button
              className="primary-button"
              type="button"
              disabled={isStartingRequirementsCopilot}
              onClick={() =>
                onReopenCopilot(activeVersion.requirementVersionId)
              }
            >
              {isStartingRequirementsCopilot
                ? "Starting..."
                : `Reopen Copilot to Produce v${activeVersion.version + 1}`}
            </button>
          ) : (
            <button
              className="secondary-button"
              type="button"
              onClick={() => onSelectVersion(null)}
            >
              Return to active (v{activeVersion.version})
            </button>
          )}
        </div>
      </header>

      {!isViewingActive ? (
        <p className="warning-text">
          You are viewing <strong>v{displayedVersion.version}</strong>{" "}
          (read-only history). The active version is{" "}
          <strong>v{activeVersion.version}</strong>.
        </p>
      ) : null}

      {approvedAt || supersededAt ? (
        <section className="requirement-version-card requirement-version-meta">
          <dl className="detail-list">
            {approvedAt ? (
              <div>
                <dt>Approved</dt>
                <dd>{approvedAt}</dd>
              </div>
            ) : null}
            {supersededAt ? (
              <div>
                <dt>Superseded</dt>
                <dd>
                  {new Date(String(supersededAt)).toLocaleString()}
                  {supersededBy ? ` by ${String(supersededBy)}` : ""}
                </dd>
              </div>
            ) : null}
          </dl>
        </section>
      ) : null}

      <section className="requirement-version-card">
        <h4>Summary</h4>
        {displayedVersion.summary ? (
          <MarkdownView text={displayedVersion.summary} />
        ) : (
          <p className="muted">No summary recorded.</p>
        )}
      </section>

      <RequirementItemList
        title={`Objectives (${displayedVersion.objectives.length})`}
        items={displayedVersion.objectives}
        emptyMessage="No objectives captured yet."
      />
      <RequirementItemList
        title={`Requirements (${displayedVersion.requirements.length})`}
        items={displayedVersion.requirements}
        emptyMessage="No requirements captured yet."
      />
      <RequirementItemList
        title={`Constraints (${displayedVersion.constraints.length})`}
        items={displayedVersion.constraints}
        emptyMessage="No constraints captured yet."
      />
    </section>
  );
}

function RequirementItemList({
  title,
  items,
  emptyMessage
}: {
  title: string;
  items: Array<Record<string, unknown>>;
  emptyMessage: string;
}) {
  if (items.length === 0) {
    return (
      <section className="requirement-version-card">
        <h4>{title}</h4>
        <p className="muted">{emptyMessage}</p>
      </section>
    );
  }
  return (
    <section className="requirement-version-card">
      <h4>{title}</h4>
      <ol className="requirement-item-list">
        {items.map((item, index) => {
          const itemTitle = String(item.title ?? "").trim();
          const description = String(item.description ?? "").trim();
          const id = String(item.id ?? `item-${index}`);
          const priority = item.priority ? String(item.priority) : null;
          return (
            <li key={`${id}-${index}`}>
              {itemTitle ? <strong>{itemTitle}</strong> : null}
              {priority ? (
                <span className="requirement-item-priority" data-priority={priority}>
                  {priority}
                </span>
              ) : null}
              {description ? <MarkdownView text={description} /> : null}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
