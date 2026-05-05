"use client";

import type { WorkspaceSummary } from "@/lib/product-api/types";

interface ArchiveWorkspaceConfirmationOverlayProps {
  workspace: WorkspaceSummary;
  isArchiving: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ArchiveWorkspaceConfirmationOverlay({
  workspace,
  isArchiving,
  errorMessage,
  onCancel,
  onConfirm
}: ArchiveWorkspaceConfirmationOverlayProps) {
  return (
    <div className="confirmation-backdrop" role="presentation">
      <section className="confirmation-overlay" aria-label="Archive workspace">
        <h3>Archive Workspace?</h3>
        <p>
          This soft-deletes <strong>{workspace.customerName}</strong> /{" "}
          <strong>{workspace.projectName}</strong>. The workspace and all its
          history (runs, reports, requirements, audit events) remain queryable
          for lineage and audit; mutating actions will be disabled.
        </p>
        <p className="muted">
          You can later un-archive a workspace via the catalog. This action is
          recorded in the audit timeline.
        </p>
        {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
        <div className="confirmation-actions">
          <button className="secondary-button" type="button" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="primary-button"
            type="button"
            disabled={isArchiving}
            onClick={onConfirm}
          >
            {isArchiving ? "Archiving…" : "Archive Workspace"}
          </button>
        </div>
      </section>
    </div>
  );
}
