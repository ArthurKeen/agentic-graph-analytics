"use client";

import type { WorkspaceAsset } from "@/lib/product-api/types";

interface DeleteConnectionProfileConfirmationOverlayProps {
  /** Which record is being removed. Both kinds delete the same way and refuse
   * the same way, so they share this dialog rather than duplicating it. */
  kind?: "connection profile" | "graph profile";
  connectionProfile: WorkspaceAsset;
  isDeleting: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

/**
 * Confirms a real, server-side deletion.
 *
 * Unlike the run "delete", which only hides a row in local state, this removes
 * the record — so the copy promises removal rather than dismissal, and the
 * server's refusal (a graph profile still using this connection) is surfaced
 * here rather than swallowed.
 */
export function DeleteConnectionProfileConfirmationOverlay({
  kind = "connection profile",
  connectionProfile,
  isDeleting,
  errorMessage,
  onCancel,
  onConfirm
}: DeleteConnectionProfileConfirmationOverlayProps) {
  return (
    <div className="confirmation-backdrop" role="presentation">
      <section
        className="confirmation-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-connection-profile-title"
      >
        <h2 id="delete-connection-profile-title">
          {kind === "graph profile" ? "Delete Graph Profile" : "Delete Connection Profile"}
        </h2>
        <p>
          Permanently delete <strong>{connectionProfile.label}</strong> from this
          workspace? This removes the stored connection metadata and cannot be
          undone.
        </p>
        <p className="muted">
          {kind === "graph profile"
            ? "Nothing is removed from the database itself — only this workspace's discovered schema for that graph. If it is the active profile, or runs, executions, interviews or graph sets still reference it, the delete is refused and you will be told what blocks it."
            : "Nothing is removed from the database itself — only this workspace's record of how to reach it. If a graph profile still uses this connection, the delete is refused and you will be told which one."}
        </p>
        <dl className="detail-list">
          <div>
            <dt>Profile ID</dt>
            <dd>{connectionProfile.id}</dd>
          </div>
          <div>
            <dt>Description</dt>
            <dd>{connectionProfile.description ?? "No description available."}</dd>
          </div>
        </dl>
        {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
        <div className="confirmation-actions">
          <button
            type="button"
            className="secondary-button"
            disabled={isDeleting}
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            type="button"
            className="danger-button"
            disabled={isDeleting}
            onClick={onConfirm}
          >
            {isDeleting ? "Deleting..." : "Delete Profile"}
          </button>
        </div>
      </section>
    </div>
  );
}
